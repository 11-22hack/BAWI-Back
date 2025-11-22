import os
import numpy as np
import math

# ==========================================
# 1. 기본 유틸리티 함수들
# ==========================================

def _haversine_distance(lat1, lon1, lat2, lon2):
    """
    두 GPS 좌표 간의 거리를 미터(m) 단위로 계산합니다 (Haversine Formula).
    """
    R = 6371000  # 지구 반지름 (미터)

    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c

def _smallest_angle_diff(angle1, angle2):
    """
    두 각도 사이의 가장 작은 차이를 계산합니다.
    """
    diff = np.abs(angle1 - angle2)
    return np.minimum(diff, 360 - diff)

def _load_image_data(image_folder):
    """
    폴더 내의 png 파일 이름을 파싱하여 데이터베이스를 구축합니다.
    """
    image_db = []

    if not os.path.exists(image_folder):
        print(f"❌ 오류: '{image_folder}' 폴더가 존재하지 않습니다. 경로를 확인해주세요.")
        return []

    files = [f for f in os.listdir(image_folder) if f.lower().endswith('.png')]

    print(f"📂 '{image_folder}' 폴더에서 {len(files)}개의 이미지 파일을 찾았습니다.")

    for f in files:
        try:
            name_part = f.rsplit('.', 1)[0]
            parts = name_part.replace(',', ' ').split()

            if len(parts) < 3:
                continue

            lon = float(parts[0])
            lat = float(parts[1])
            heading = float(parts[2])

            image_db.append({
                'filename': f,
                'lon': lon,
                'lat': lat,
                'heading': heading
            })
        except ValueError:
            continue

    return image_db

def _find_best_matches(path_data, image_db, max_dist_m=10.0, max_angle_deg=30.0):
    """
    경로 데이터와 이미지 DB를 비교하여 최적의 매칭 이미지를 찾습니다.
    * 조건: 한 번 선택된 이미지는 다시 선택되지 않습니다 (중복 방지).
    """
    matches = []
    used_indices = set()  # 이미 사용된 이미지 인덱스를 저장할 집합

    if not image_db:
        print("⚠️ 매칭할 이미지 데이터가 없습니다.")
        return [None] * len(path_data)

    # numpy 배열로 변환
    db_lons = np.array([img['lon'] for img in image_db])
    db_lats = np.array([img['lat'] for img in image_db])
    db_headings = np.array([img['heading'] for img in image_db])
    filenames = [img['filename'] for img in image_db]

    print(f"🚀 매칭 시작 (총 {len(path_data)}개 경로 지점, 중복 허용 X)...")

    for i, (p_lon, p_lat, p_heading) in enumerate(path_data[:-1]):
        # 1. 거리 계산
        dists = _haversine_distance(p_lat, p_lon, db_lats, db_lons)

        # 2. 각도 차이 계산
        angle_diffs = _smallest_angle_diff(p_heading, db_headings)

        # 3. 필터링 (거리 & 각도 조건)
        valid_mask = (dists <= max_dist_m) & (angle_diffs <= max_angle_deg)

        # === 이미 사용된 이미지는 후보에서 강제로 제외 ===
        if used_indices:
            valid_mask[list(used_indices)] = False

        # 매칭 실패 시 처리
        if not np.any(valid_mask):
            # 디버깅 정보 출력
            nearest_idx = np.argmin(dists)
            nearest_file = filenames[nearest_idx]
            nearest_dist = dists[nearest_idx]
            nearest_angle_diff = angle_diffs[nearest_idx]

            status_msg = ""
            if nearest_idx in used_indices:
                status_msg = " (❌ 이미 앞선 경로에서 사용됨)"

            print(f"[DEBUG] Point {i}: 매칭 실패")
            print(f"  └─ 가장 가까운 이미지: {nearest_file}{status_msg}")
            print(f"  └─ 거리: {nearest_dist:.2f}m, 각도차: {nearest_angle_diff:.2f}°")
            continue

        # 4. 최적 선택 (거리순)
        valid_indices = np.where(valid_mask)[0]
        valid_dists = dists[valid_indices]

        best_idx_in_valid = np.argmin(valid_dists)
        original_idx = valid_indices[best_idx_in_valid]

        matched_file = filenames[original_idx]
        matches.append(matched_file)

        # 선택된 이미지 인덱스 저장 (중복 방지)
        used_indices.add(original_idx)

    return matches


# ==========================================
# 2. 메인 실행 함수 (요청하신 부분)
# ==========================================

def find_matching(
    path_segments: list[list[float, float, float]],
    image_folder_path: str,
    max_dist: float = 10.0,
    max_angle: float = 90.0
) -> list[str]:
    """
    이동 경로(path_points)와 이미지 폴더 경로를 입력받아 매칭 결과를 반환합니다.

    Args:
        path_points (list): [[lon, lat, heading], ...] 형태의 리스트
        image_folder_path (str): 이미지가 저장된 폴더 경로
        max_dist (float): 매칭 허용 최대 거리 (미터)
        max_angle (float): 매칭 허용 최대 각도 차이 (도)

    Returns:
        list: 매칭된 파일명 리스트 (매칭 실패 시 None)
    """
    print(f"\n=== 매칭 프로세스 시작 (폴더: {image_folder_path}) ===")

    # 1. 이미지 DB 로드
    loaded_image_db = _load_image_data(image_folder_path)
    print(loaded_image_db)

    # 2. 매칭 실행 (중복 방지 로직 포함)
    final_results = _find_best_matches(
        path_segments,
        loaded_image_db,
        max_dist_m=max_dist,
        max_angle_deg=max_angle
    )

    # 3. 결과 요약 출력
    print("\n--- 최종 결과 요약 ---")
    matched_count = 0
    for i, filename in enumerate(final_results):
        if filename:
            print(f"경로 점 {i}: {filename}")
            matched_count += 1
        else:
            print(f"경로 점 {i}: (매칭 없음)")

    print(f"\n총 {len(path_segments)}개 지점 중 {matched_count}개 매칭 성공")

    return final_results


# ==========================================
# 3. 사용 예시
# ==========================================

if __name__ == "__main__":
    print("Test for utils.find_matching")
    # 1. 경로 데이터 정의
    my_path = [
        [126.93786958841235,37.5516945685967,-43.72494194971623],
        [126.93793347320441,37.551633465734305,14.932123753321727],
        [126.93797513576003,37.55164457629946,57.14506559908161],
        [126.93806123525816,37.55177789567232,38.12261723880201],
        [126.9381412261945,37.551840667583356,38.12261723795986],
        [126.93826921169266,37.55194110264101,38.12261723799025],
        [126.93838439864099,37.552031494192896,38.12261723287876],
        [126.93844583168011,37.55207970302057,38.12261724985376],
        [126.93846118993989,37.55209175522749,54.3962018426633],
        [126.93854173497692,37.55220424358974,54.39620184437641],
        [126.93862228001396,37.552316731952004,33.930340909538145],
        [126.93877504096572,37.55241950051529,4.18584027226713],
        [126.93888891923994,37.55242783491857,8.260271296518567],
        [126.93906112506056,37.55245283509505,-26.563330873832193]
    ]

    # 2. 함수 호출
    results = find_matching(
        path_segments=my_path,
        image_folder_path="./images"
    )