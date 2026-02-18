#!/bin/bash
# 컨테이너 충돌 해결 스크립트
# 서버에서 실행: bash deploy/fix_container_conflict.sh

set -e

BACKEND_PATH="${BACKEND_PATH:-~/dpbr_deploy/dpbr_backend}"

echo "🔧 컨테이너 충돌 해결 중..."

cd "$BACKEND_PATH"

echo "1️⃣ 기존 컨테이너 강제 중지 및 제거..."
docker stop dpbr-backend 2>/dev/null || true
docker rm -f dpbr-backend 2>/dev/null || true

echo "2️⃣ Docker Compose로 모든 리소스 정리..."
docker compose down --remove-orphans

echo "3️⃣ 최신 이미지 pull..."
docker compose pull || echo "⚠️ Image pull 실패 - 로컬 이미지 사용"

echo "4️⃣ 새로운 컨테이너 시작..."
docker compose up -d --force-recreate

echo "5️⃣ 컨테이너 상태 확인..."
sleep 5
docker ps | grep dpbr-backend

echo ""
echo "✅ 완료! 컨테이너가 재시작되었습니다."
echo ""
echo "상태 확인: docker ps"
echo "로그 확인: docker logs dpbr-backend -f"
