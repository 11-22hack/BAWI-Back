#!/usr/bin/env python3
import argparse
import glob
import os
import shutil

from google import genai
from dotenv import load_dotenv

from typing import List
from moviepy import VideoFileClip, concatenate_videoclips
import os
import time
from google.cloud import storage

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_api_key = os.getenv("API_KEY")
_project = os.getenv("GOOGLE_CLOUD_PROJECT")
_location = os.getenv("GOOGLE_CLOUD_LOCATION")

if not _api_key:
    raise RuntimeError("API_KEY 환경변수가 없습니다.")
if not _project or not _location:
    raise RuntimeError("GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION 이 필요합니다.")

client = genai.Client()

VIDEO_MODEL_ID = os.getenv("VIDEO_MODEL_ID", "veo-3.1-generate-001")


def _load_image(path: str) -> types.Image:
    if not os.path.exists(path):
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {path}")
    return types.Image.from_file(location=path)


def _download_gcs_uri(gcs_uri: str, local_path: str) -> None:
    """
    gs://bucket/path/to/file.mp4 형태의 URI를 로컬 파일로 다운로드.
    """
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"gs:// 로 시작하지 않는 URI 입니다: {gcs_uri}")

    without_scheme = gcs_uri[len("gs://") :]
    bucket_name, _, blob_path = without_scheme.partition("/")

    client = storage.Client()  # ADC 기반 (gcloud auth application-default login 등)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)


def _generate_transition_vertex(
    img_a: str,
    img_b: str,
    out_path: str,
    prompt: str | None = None,
    duration_seconds: int = 4,
):
    """
    두 장의 이미지를 이용해 Veo 3.1로 프레임 보간 영상 생성.

    img_a       : 시작 프레임 경로
    img_b       : 마지막 프레임 경로
    out_path    : 저장할 mp4 경로
    prompt      : 없으면 기본 도로 주행 프롬프트 사용
    duration_seconds : 생성 영상 길이(초). Veo 기본은 8초지만 줄여도 됨.
    """
    if prompt is None:
        prompt = (
            "A smooth driving roadview video transitioning from the first frame "
            "to the second frame, as if a camera is moving forward along the road."
        )

    print(f"  ▶ Veo 3.1 요청: {os.path.basename(img_a)} → {os.path.basename(img_b)}")

    # 1) 로컬 이미지를 Veo용 Image 객체로 변환
    first_image = _load_image(img_a)
    last_image = _load_image(img_b)

    # 2) Veo 3.1에 프레임 보간 요청 (첫 프레임 + 마지막 프레임)
    operation = client.models.generate_videos(
    model=VIDEO_MODEL_ID,
    prompt=prompt,
    image=first_image,
    config=types.GenerateVideosConfig(
        last_frame=last_image,
        duration_seconds=duration_seconds,
        aspect_ratio="16:9",
        resolution="720p",
        number_of_videos=1,
    ),
)


    # 3) Long-running operation 폴링
        # 3) Long-running operation 폴링
    while not operation.done:
        print("    ⏳ Veo 생성 중… (10초 대기)")
        # 여기서는 그냥 기다리기만 하고,
        # operation 객체는 그대로 둔다 (get으로 다시 가져오지 않음)
        time.sleep(10)

        # 필요하면 상태를 다시 받아오고 싶을 때는 name 기반으로 가져오는 게 안전함
        operation = client.operations.get(operation)

    # 4) 작업 결과 / 에러 확인
    if getattr(operation, "response", None) is None:
        op_err = getattr(operation, "error", None)
        raise RuntimeError(f"Veo operation이 응답 없이 종료되었습니다. error={op_err!r}")

    if not getattr(operation.response, "generated_videos", None):
        raise RuntimeError(f"Veo 응답에 generated_videos가 없습니다. raw_response={operation.response!r}")

    video_info = operation.response.generated_videos[0]
    video_obj = video_info.video

    # 4-1) 우선 uri / gcs_uri 있는지 시도
    uri = getattr(video_obj, "uri", None) or getattr(video_obj, "gcs_uri", None)

    if uri:
        print(f"    🎯 Veo video uri: {uri}")

        if uri.startswith("gs://"):
            print(f"    ⬇️ GCS → 로컬 다운로드: {out_path}")
            _download_gcs_uri(uri, out_path)
        elif uri.startswith("http://") or uri.startswith("https://"):
            import requests

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            print(f"    ⬇️ HTTP → 로컬 다운로드: {out_path}")
            resp = requests.get(uri)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(resp.content)
        else:
            raise RuntimeError(f"지원하지 않는 URI 형식입니다: {uri}")

        print(f"    ✅ Veo transition saved to {out_path}")
        return

    # 4-2) uri가 없다면 → 인라인 비디오(video_bytes)로 온 경우 처리
    print("    ℹ️ URI 없음, 인라인 비디오 데이터(video_bytes)로 처리합니다.")

    data = None

    # google-genai의 Video 객체가 video_bytes 필드를 가지고 있으므로 거기서 꺼낸다
    if hasattr(video_obj, "video_bytes"):
        vb = video_obj.video_bytes
        # 바로 bytes/bytearray인 경우
        if isinstance(vb, (bytes, bytearray)):
            data = vb
        # message 안에 data 필드가 있는 경우 (예: ByteString 같은 구조체)
        elif hasattr(vb, "data"):
            data = vb.data
        # 혹시 buffer라는 이름으로 감싸져 있을 수도 있으니 한 번 더 시도
        elif hasattr(vb, "buffer"):
            data = vb.buffer

    if not data:
        # 여기서 다시 타입 확인해보고 싶으면 type(video_obj.video_bytes), dir(...) 찍어보면 됨
        raise RuntimeError(f"지원하지 않는 비디오 응답 형식입니다: {video_obj!r}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    print(f"    ✅ Veo transition saved to {out_path}")


def _merge_videos(
    clip_paths: List[str],
    output_file: str,
    trim_last_frames: int = 7,
) -> None:
    """
    여러 mp4 클립을 이어 붙여 하나의 영상으로 합친다.
    각 클립의 마지막 `trim_last_frames` 프레임은 잘라낸다.

    :param clip_paths: 이어 붙일 영상 경로 리스트 (앞에서부터 순서대로)
    :param output_file: 최종 출력 파일 경로 (예: "roadview.mp4")
    :param trim_last_frames: 각 클립에서 뒤에서 제거할 프레임 수
    """
    clips = []
    used_fps = None

    for path in clip_paths:
        clip = VideoFileClip(path)

        # fps 가져오기 (첫 번째 클립 기준)
        fps = getattr(clip, "fps", None) or getattr(clip.reader, "fps", None)
        if used_fps is None:
            used_fps = fps

        if trim_last_frames > 0 and fps:
            trim_sec = trim_last_frames / fps
        else:
            trim_sec = 0.0

        # 너무 짧은 클립이면 스킵
        new_duration = max(0.0, clip.duration - trim_sec)
        if new_duration <= 0:
            print(f"⚠️ {path} : 길이가 너무 짧아서 스킵합니다.")
            clip.close()
            continue

        # 0 ~ new_duration 구간만 사용
        trimmed = clip.subclipped(0, new_duration)
        clips.append(trimmed)

    if not clips:
        raise RuntimeError("합칠 클립이 없습니다. (모두 스킵되었거나 존재하지 않음)")

    print(f"🧵 {len(clips)}개의 클립을 병합합니다. (클립당 뒤에서 {trim_last_frames}프레임 제거)")

    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(
        output_file,
        fps=used_fps or 30,  # fps 정보가 없으면 30으로
        codec="libx264",
        audio=False,
    )

    # 리소스 정리
    for c in clips:
        c.close()
    final_clip.close()


def interpolate_images(
        image_paths: str,
        out_file: str,
        out_dir: str,
        no_resume: bool = False
    ) -> None:
    clip_dir = os.path.join(out_dir, "clips")
    os.makedirs(clip_dir, exist_ok=True)

    clip_paths = []

    for i in range(len(image_paths) - 1):
        img_a = image_paths[i]
        img_b = image_paths[i + 1]

        clip_name = f"transition_{i+1:03d}.mp4"
        clip_path = os.path.join(clip_dir, clip_name)

        if not no_resume and os.path.exists(clip_path):
            print(f"⏭  이미 존재, 스킵: {clip_path}")
            clip_paths.append(clip_path)
            continue

        print(f"🎬 ({i+1}/{len(image_paths)-1}) {os.path.basename(img_a)} → {os.path.basename(img_b)}")
        _generate_transition_vertex(img_a, img_b, clip_path)
        clip_paths.append(clip_path)

    if not clip_paths:
        print("❌ 생성된 클립이 없습니다.")
        return

    print("🧵 클립 병합 중…")
    _merge_videos(clip_paths, os.path.join(out_dir, out_file))
    print("🎉 최종 영상 생성 완료:", os.path.join(out_dir, out_file))
    print(f"🧹 중간 클립 정리: {clip_dir}")
    shutil.rmtree(clip_dir)


def main():
    load_dotenv()  # .env 로드

    parser = argparse.ArgumentParser(
        description="Streetview 이미지들을 Veo(구글)로 보간해서 영상으로 만드는 스크립트"
    )
    parser.add_argument(
        "--frames_dir",
        required=True,
        help="프레임 이미지(jpg, png)가 들어있는 디렉토리 경로",
    )
    parser.add_argument(
        "--output",
        default="final.mp4",
        help="최종 출력 파일 이름 (기본: final.mp4)",
    )
    parser.add_argument(
        "--out_dir",
        default="demo_out",
        help="중간 transition 클립을 저장할 디렉토리 (기본: demo_out)",
    )
    parser.add_argument(
        "--no_resume",
        action="store_true",
        help="이미 존재하는 클립이 있어도 무조건 다시 생성",
    )

    args = parser.parse_args()
    interpolate_images(
        images=args.frames_dir,
        out_file=args.output,
        out_dir=args.out_dir,
        no_resume=args.no_resume,
    )
