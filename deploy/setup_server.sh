#!/bin/bash
# 서버 초기 설정 스크립트
# 이 스크립트는 서버에서 한 번만 실행하면 됩니다.

set -euo pipefail

echo "🚀 단풍바람 백엔드 서버 초기 설정"

# 변수 설정
DEPLOY_USER=${DEPLOY_USER:-"ark1st"}
DEPLOY_ROOT=${DEPLOY_ROOT:-"/home/$DEPLOY_USER/dpbr_deploy"}
BACKEND_PATH="${DEPLOY_ROOT}/dpbr_backend"
SERVICE_NAME="dpbr-backend"
REPO_URL=${REPO_URL:-"https://github.com/GC-MapleWind/MSGS_13_B.git"}

# 1. 필수 패키지 설치
echo "📦 필수 패키지 설치 중..."
sudo apt-get update
sudo apt-get install -y git curl python3.12 python3.12-venv

# 2. uv 설치 (Python 패키지 매니저)
echo "📚 uv 설치 중..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
fi

# 3. 배포 루트 디렉토리 및 백엔드 디렉토리 생성
echo "📁 배포 디렉토리 구조 설정 중..."
echo "   - 배포 루트: ${DEPLOY_ROOT}"
echo "   - 백엔드: ${BACKEND_PATH}"

mkdir -p "$DEPLOY_ROOT"

if [ ! -d "$BACKEND_PATH" ]; then
    echo "📦 백엔드 저장소 클론 중..."
    git clone "$REPO_URL" "$BACKEND_PATH"
else
    echo "✅ 백엔드 디렉토리가 이미 존재합니다."
fi

cd "$BACKEND_PATH"

# 4. 의존성 설치
echo "📚 의존성 설치 중..."
uv sync

# 5. .env 파일 생성
if [ ! -f ".env" ]; then
    echo "🔧 .env 파일 생성 중..."
    cat > .env << 'EOF'
# Database
DATABASE_URL=sqlite+aiosqlite:///./maplewind.db

# Server
HOST=0.0.0.0
PORT=8000

# Environment
ENVIRONMENT=production
EOF
    echo ".env 파일이 생성되었습니다. 필요한 설정을 수정해주세요."
fi

# 6. systemd 서비스 파일 생성
echo "⚙️  systemd 서비스 설정 중..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=단풍바람 백엔드 API 서비스
After=network.target

[Service]
Type=simple
User=$DEPLOY_USER
WorkingDirectory=$BACKEND_PATH
Environment="PATH=/home/${DEPLOY_USER}/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/${DEPLOY_USER}/.cargo/bin/uv run uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. 서비스 활성화 및 시작
echo "🔄 서비스 활성화 및 시작 중..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

# 8. 서비스 상태 확인
echo "✅ 서비스 상태 확인 중..."
sudo systemctl status ${SERVICE_NAME} --no-pager

echo ""
echo "🎉 초기 설정이 완료되었습니다!"
echo ""
echo "유용한 명령어:"
echo "  - 서비스 상태 확인: sudo systemctl status ${SERVICE_NAME}"
echo "  - 서비스 재시작: sudo systemctl restart ${SERVICE_NAME}"
echo "  - 로그 확인: sudo journalctl -u ${SERVICE_NAME} -f"
echo "  - 서비스 중지: sudo systemctl stop ${SERVICE_NAME}"
echo ""
echo "API 접속: http://$(hostname -I | awk '{print $1}'):8000/docs"
