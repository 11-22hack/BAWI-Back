#!/bin/bash
set -e

# 1. GCP_SA_KEY 환경변수에 JSON 내용이 들어있는 경우 (Base64 인코딩 없이 Raw JSON 가정)
# Dokploy 등의 환경변수에서 줄바꿈이 어려울 수 있으므로, 필요한 경우 base64 디코딩 로직을 추가할 수도 있습니다.
if [ -n "$GCP_SA_KEY" ]; then
    echo "🔑 GCP_SA_KEY 환경변수 감지됨. 인증 파일 생성 중..."
    echo "$GCP_SA_KEY" > /app/gcp-key.json
    export GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
fi

# 2. GOOGLE_APPLICATION_CREDENTIALS 설정 확인 및 gcloud 로그인
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "✅ 인증 파일 확인: $GOOGLE_APPLICATION_CREDENTIALS"

    echo "☁️ gcloud 로그인 시도 중..."
    gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" --quiet

    if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
        echo "☁️ gcloud 프로젝트 설정: $GOOGLE_CLOUD_PROJECT"
        gcloud config set project "$GOOGLE_CLOUD_PROJECT" --quiet
    fi
else
    echo "⚠️ 경고: Google Cloud 인증 정보(GOOGLE_APPLICATION_CREDENTIALS 또는 GCP_SA_KEY)가 없습니다."
fi

# 3. 서버 실행
PORT=${PORT:-80}
echo "🚀 서버 시작 (Port: $PORT)"
exec uvicorn src.server:app --host 0.0.0.0 --port "$PORT"

