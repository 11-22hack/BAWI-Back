# 👑 King Project - Roadview Navigation & Video Generation

이 프로젝트는 **TMap API**를 활용한 보행자 경로 탐색과 **Google Veo (Generative AI)** 기술을 결합하여, 출발지와 목적지 사이의 경로를 따라 이동하는 로드뷰 영상을 생성하는 백엔드 서비스입니다.

## 🚀 주요 기능

1.  **경로 탐색 (Navigation)**
    *   TMap API를 사용하여 출발지와 목적지(WGS84 좌표) 사이의 보행자 경로를 탐색합니다.
    *   경로상의 좌표를 일정 간격으로 보간(Interpolation)하고, 이동 방향(Heading)을 계산하여 상세 경로 데이터를 생성합니다.

2.  **이미지 매칭 (Image Matching)**
    *   계산된 경로 좌표와 로컬 데이터베이스(이미지 파일명에 좌표 포함)를 비교합니다.
    *   Haversine 거리 공식과 각도 차이를 이용하여 경로상에 가장 적합한 실제 로드뷰 이미지를 매칭합니다.

3.  **AI 영상 생성 (Video Generation)**
    *   매칭된 로드뷰 이미지들 사이의 구간을 **Google Veo 3.1** (Generative AI) 모델로 보간합니다.
    *   끊겨있는 이미지 사이를 부드럽게 이어주는 주행 영상을 생성하고, 이를 하나의 비디오 파일(MP4)로 병합합니다.
    *   생성된 영상은 캐싱되어 동일한 요청 시 빠르게 응답합니다.

## 🛠 기술 스택

*   **Language**: Python 3.11
*   **Web Framework**: FastAPI
*   **AI/ML**: Google GenAI (Veo 3.1 model), Google Cloud Storage
*   **Media Processing**: MoviePy, FFMPEG
*   **Deployment**: Docker, Dokploy

## 📂 프로젝트 구조

```
.
├── data/                   # 이미지 및 캐시 데이터 저장소
│   ├── images/             # 로드뷰 원본 이미지 (파일명: lon,lat,heading.png)
│   └── cache/              # 생성된 비디오 캐시
├── src/
│   ├── server.py           # FastAPI 메인 서버
│   └── utils/
│       ├── navigate.py         # TMap 경로 탐색 로직
│       ├── find_matching.py    # 경로-이미지 매칭 알고리즘
│       └── interpolate_images.py # Google Veo 영상 생성 및 병합
├── Dockerfile              # Docker 빌드 설정
├── start.sh                # 컨테이너 시작 스크립트 (GCP 인증 포함)
└── requirements.txt        # Python 의존성 목록
```

## 🔧 설치 및 실행 방법

### 1. 환경 변수 설정 (.env)

프로젝트 루트에 `.env` 파일을 생성하거나 서버 환경 변수로 다음 값을 설정해야 합니다.

```ini
# Google Cloud 설정 (Video Generation)
GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
API_KEY="your-google-genai-api-key"
VIDEO_MODEL_ID="veo-3.1-generate-001"

# TMap API (Navigation)
TMAP_APP_KEY="your-tmap-api-key"

# Server Config
HOST=0.0.0.0
PORT=8000
DATA_DIR="./data"
```

### 2. 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python src/server.py
```

### 3. Docker 실행 (Dokploy 등)

이 프로젝트는 Docker 환경에서 실행되도록 구성되어 있으며, 특히 Google Cloud 인증을 위해 시작 스크립트(`start.sh`)를 사용합니다.

```bash
# 이미지 빌드
docker build -t king-server .

# 컨테이너 실행 (환경 변수 필요)
docker run -p 8000:80 --env-file .env king-server
```

> **Dokploy 배포 시 주의사항**:
> *   `GCP_SA_KEY` 환경변수에 서비스 계정 JSON 파일의 내용을 그대로 넣으면 `start.sh`가 자동으로 인증 파일을 생성하고 로그인합니다.
> *   초기 데이터(이미지) 보존을 위해 `data` 폴더를 볼륨 마운트할 때 주의가 필요합니다. (빈 볼륨 마운트 시 이미지가 사라질 수 있음)

## 📡 API 엔드포인트

### `GET /get-meta`
*   **설명**: 출발지와 목적지 좌표를 받아 경로 데이터를 반환합니다. 이미 캐시된 영상이 있다면 영상 키도 함께 반환합니다.
*   **Parameters**: `startLat`, `startLng`, `endLat`, `endLng`

### `GET /gen-video`
*   **설명**: 경로에 맞는 주행 영상을 생성하거나 스트리밍합니다.
*   **Parameters**: `startLat`, `startLng`, `endLat`, `endLng`
*   **Response**:
    *   생성 중: `201 In progress`
    *   완료: MP4 비디오 파일 스트리밍

## 📝 라이선스

이 프로젝트는 개인 포트폴리오 및 학습 목적으로 제작되었습니다.

