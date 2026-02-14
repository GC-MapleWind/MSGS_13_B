# 배포 가이드

이 폴더에는 서버 배포를 위한 설정 파일과 가이드가 포함되어 있습니다.

## 📁 파일 구성

| 파일 | 설명 |
|------|------|
| `setup_server.sh` | 서버 초기 설정 스크립트 (Docker, 의존성, systemd 서비스 설정) |
| `DIRECTORY_STRUCTURE.md` | 서버 배포 디렉토리 구조 가이드 |
| `TODO_GHCR_AUTH.md` | GitHub Container Registry 인증 설정 가이드 |
| `README.md` | 이 파일 - 배포 가이드 개요 |

## 🚀 빠른 시작

### 1. 최초 서버 설정

서버에 처음 배포할 때 한 번만 실행:

```bash
# 저장소 클론 (임시)
git clone https://github.com/GC-MapleWind/MSGS_13_B.git ~/temp_backend
cd ~/temp_backend

# 초기 설정 스크립트 실행
bash deploy/setup_server.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- ✅ 필수 패키지 설치 (Git, Python, uv)
- ✅ 배포 디렉토리 구조 생성 (`~/dpbr_deploy/dpbr_backend`)
- ✅ 의존성 설치
- ✅ systemd 서비스 설정
- ✅ 서비스 자동 시작

### 2. 환경 변수 설정

`.env` 파일을 생성하고 필요한 값을 설정:

```bash
cd ~/dpbr_deploy/dpbr_backend
nano .env
```

필수 환경 변수:
```env
# JWT 설정
JWT_SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 서버 설정
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
```

### 3. Docker 배포

```bash
cd ~/dpbr_deploy/dpbr_backend

# Docker Compose로 실행
docker compose up -d

# 또는 수동으로 실행
docker build -t dpbr-backend:local .
docker run -d --name dpbr-backend -p 8000:8000 --env-file .env dpbr-backend:local
```

## 🔄 자동 배포 (CI/CD)

`main` 브랜치에 push하면 GitHub Actions가 자동으로:

1. ✅ Docker 이미지 빌드
2. ✅ GitHub Container Registry에 push
3. ✅ 서버에 SSH 접속
4. ✅ 최신 코드 pull
5. ✅ Docker Compose로 서비스 재시작
6. ✅ Health check 수행

### 필요한 GitHub Secrets

레포지토리 Settings > Secrets에 다음을 추가:

| Secret | 설명 |
|--------|------|
| `SSH_PRIVATE_KEY` | 서버 SSH private key |
| `SERVER_HOST` | 서버 IP 또는 도메인 |
| `SERVER_USER` | 서버 사용자명 (예: `ark1st`) |

## 📂 디렉토리 구조

자세한 내용은 [DIRECTORY_STRUCTURE.md](./DIRECTORY_STRUCTURE.md) 참고

```
~/dpbr_deploy/
├── dpbr_front/      # 프론트엔드
└── dpbr_backend/    # 백엔드 (이 레포)
    ├── main.py
    ├── Dockerfile
    ├── docker-compose.yml
    └── .env
```

## 🔧 유용한 명령어

### 서비스 관리

```bash
# 상태 확인
sudo systemctl status dpbr-backend

# 재시작
sudo systemctl restart dpbr-backend

# 로그 확인
sudo journalctl -u dpbr-backend -f
```

### Docker 관리

```bash
# 컨테이너 확인
docker ps

# 로그 확인
docker logs dpbr-backend -f

# 재시작
docker restart dpbr-backend

# 재배포
docker compose pull
docker compose up -d
```

## 🚨 문제 해결

### 배포 실패

1. **SSH 접속 문제**: `SSH_PRIVATE_KEY` secret 확인
2. **이미지 pull 실패**: GHCR 인증 확인 (TODO_GHCR_AUTH.md 참고)
3. **컨테이너 시작 실패**: `.env` 파일 확인
4. **Health check 실패**: 로그 확인 (`docker logs dpbr-backend`)

### 수동 롤백

```bash
cd ~/dpbr_deploy/dpbr_backend
git log --oneline -5  # 이전 커밋 확인
git checkout <이전-커밋-해시>
docker compose up -d --force-recreate
```

## 📚 추가 문서

- [디렉토리 구조 가이드](./DIRECTORY_STRUCTURE.md) - 배포 디렉토리 상세 설명
- [GHCR 인증 설정](./TODO_GHCR_AUTH.md) - Container Registry 접근 설정
- [CI/CD 워크플로우](../.github/workflows/deploy.yml) - GitHub Actions 설정

## 📞 도움이 필요하신가요?

- GitHub Issues에 문제 보고
- 프로젝트 문서 확인: [DEVELOPMENT.md](../DEVELOPMENT.md)
