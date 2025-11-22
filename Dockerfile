# Python 3.11 슬림 이미지 사용
FROM python:3.11-slim

# 시스템 의존성 및 Google Cloud CLI 설치
# 1. 기본 패키지 설치
# 2. Google Cloud SDK 저장소 추가 및 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    curl \
    gnupg \
    lsb-release \
    && mkdir -p /usr/share/keyrings \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-cli \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 및 데이터 복사
COPY src ./src
COPY data ./data
COPY start.sh .

# 실행 권한 부여
RUN chmod +x start.sh

# 환경 변수 설정
ENV PYTHONPATH=/app/src
ENV HOST=0.0.0.0
ENV PORT=80
ENV DATA_DIR=/app/data

# 포트 노출
EXPOSE 80

# 시작 스크립트 실행
CMD ["./start.sh"]
