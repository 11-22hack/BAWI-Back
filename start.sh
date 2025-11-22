#!/bin/bash
set -e

# 로그 출력을 즉시 확인하기 위해 stderr로 출력
log() {
    echo "[start.sh] $1" >&2
}

log "🚀 컨테이너 시작 스크립트 실행됨"

# 1. GCP_SA_KEY 환경변수 처리
if [ -n "$GCP_SA_KEY" ]; then
    log "🔑 GCP_SA_KEY 환경변수 감지됨. 인증 파일 생성 중..."
    echo "$GCP_SA_KEY" > /app/gcp-key.json
    export GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
else
    log "⚠️ GCP_SA_KEY 환경변수가 없습니다. GOOGLE_APPLICATION_CREDENTIALS가 설정되어 있는지 확인하세요."
fi

# 2. 필수: gcloud 로그인 수행
# 인증 정보가 없으면 서버를 띄우지 않고 종료하여 배포 실패로 처리되게 함
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    log "✅ 인증 파일 확인됨: $GOOGLE_APPLICATION_CREDENTIALS"

    log "☁️ gcloud 로그인 시도 중..."
    # 로그인 실패 시 스크립트가 중단되도록 set -e가 동작함. 상세 로그를 위해 에러는 그대로 출력됨.
    gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" --quiet

    log "☁️ gcloud 로그인 성공"

    if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
        log "☁️ gcloud 프로젝트 설정: $GOOGLE_CLOUD_PROJECT"
        gcloud config set project "$GOOGLE_CLOUD_PROJECT" --quiet
    else
        log "⚠️ GOOGLE_CLOUD_PROJECT 환경변수가 없어 프로젝트 설정은 건너뜁니다."
    fi
else
    log "❌ [치명적 오류] Google Cloud 인증 파일이 없습니다."
    log "   Dokploy 환경변수에 'GCP_SA_KEY'를 설정하거나 볼륨 마운트로 키 파일을 제공해야 합니다."
    # 명시적으로 에러 코드로 종료하여 컨테이너 실행을 막음
    exit 1
fi

# 3. 서버 실행
PORT=${PORT:-80}
log "🔥 서버 실행 시작 (Port: $PORT)"
exec uvicorn src.server:app --host 0.0.0.0 --port "$PORT"
