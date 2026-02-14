# 서버 배포 디렉터리 구조

프론트엔드와 백엔드를 한 곳에서 관리하기 위한 통합 배포 구조입니다.

## 📂 권장 디렉토리 구조

```
~/dpbr_deploy/
├── dpbr_front/      # 프론트엔드 (프론트 레포 CI가 scp로 전송)
│   ├── app/
│   ├── nginx/
│   └── Dockerfile
└── dpbr_backend/    # 백엔드 (이 레포, CI/CD로 자동 배포)
    ├── main.py
    ├── Dockerfile
    ├── docker-compose.yml
    └── ...
```

## 🚀 초기 설정

### 방법 1: 자동 설정 (권장)

서버에서 setup 스크립트를 실행하면 자동으로 디렉토리 구조가 생성됩니다:

```bash
# 저장소 클론 (임시)
git clone https://github.com/GC-MapleWind/MSGS_13_B.git ~/temp_backend
cd ~/temp_backend

# setup 스크립트 실행
bash deploy/setup_server.sh
```

스크립트가 자동으로 다음을 수행합니다:
- `~/dpbr_deploy/` 루트 디렉토리 생성
- `~/dpbr_deploy/dpbr_backend/` 에 백엔드 클론
- 필요한 패키지 및 의존성 설치
- systemd 서비스 설정

### 방법 2: 수동 설정

이미 다른 위치에 백엔드가 있다면 이동하거나 복사할 수 있습니다:

#### 2-1. 기존 백엔드를 dpbr_deploy로 이동

```bash
cd ~
mkdir -p dpbr_deploy

# 기존 백엔드를 새 위치로 이동
mv MSGS_13_B dpbr_deploy/dpbr_backend
```

#### 2-2. 복사본 생성 (원본 유지)

```bash
mkdir -p ~/dpbr_deploy
cp -a ~/MSGS_13_B ~/dpbr_deploy/dpbr_backend
```

#### 2-3. 처음부터 올바른 위치에 클론

```bash
mkdir -p ~/dpbr_deploy
cd ~/dpbr_deploy
git clone https://github.com/GC-MapleWind/MSGS_13_B.git dpbr_backend
```

## 🔄 CI/CD 자동 배포

이 레포의 GitHub Actions CI/CD는 자동으로 다음 경로에 배포합니다:

- **배포 루트**: `~/dpbr_deploy`
- **백엔드 경로**: `~/dpbr_deploy/dpbr_backend`

### 배포 흐름

1. `main` 브랜치에 push
2. Docker 이미지 빌드 및 GHCR에 push
3. 서버 SSH 접속
4. `~/dpbr_deploy/dpbr_backend`로 이동
5. 최신 코드 pull
6. Docker Compose로 컨테이너 재시작
7. Health check 수행

### 필요한 GitHub Secrets

다음 secrets를 레포지토리에 설정해야 합니다:

| Secret | 설명 | 예시 |
|--------|------|------|
| `SSH_PRIVATE_KEY` | 서버 SSH 접속을 위한 private key | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `SERVER_HOST` | 서버 주소 | `123.456.78.90` 또는 `example.com` |
| `SERVER_USER` | 서버 사용자명 | `ark1st` |

> **참고**: `BACKEND_DEPLOY_PATH` secret은 더 이상 필요하지 않습니다. 
> CI/CD가 자동으로 `~/dpbr_deploy/dpbr_backend`를 사용합니다.

## 🐳 Docker 배포

### Docker Compose 사용 (권장)

```bash
cd ~/dpbr_deploy/dpbr_backend
docker compose up -d
```

### 수동 Docker 실행

```bash
cd ~/dpbr_deploy/dpbr_backend

# 이미지 빌드
docker build -t dpbr-backend:local .

# 컨테이너 실행
docker run -d \
  --name dpbr-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -v dpbr-data:/app/data \
  --env-file .env \
  dpbr-backend:local
```

## 📋 경로 정리

| 항목 | 경로 |
|------|------|
| 배포 루트 | `~/dpbr_deploy` |
| 백엔드 | `~/dpbr_deploy/dpbr_backend` |
| 프론트엔드 | `~/dpbr_deploy/dpbr_front` |
| 백엔드 데이터 볼륨 | Docker volume `dpbr-data` |

## 🔧 유용한 명령어

### 서비스 관리 (systemd)

```bash
# 서비스 상태 확인
sudo systemctl status dpbr-backend

# 서비스 재시작
sudo systemctl restart dpbr-backend

# 로그 확인
sudo journalctl -u dpbr-backend -f

# 서비스 중지
sudo systemctl stop dpbr-backend
```

### Docker 관리

```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker logs dpbr-backend -f

# 컨테이너 재시작
docker restart dpbr-backend

# 컨테이너 중지 및 삭제
docker stop dpbr-backend
docker rm dpbr-backend
```

## 🚨 문제 해결

### 디렉토리 구조가 잘못된 경우

기존 배포가 다른 경로에 있다면:

```bash
# 1. 기존 컨테이너 중지
docker stop dpbr-backend
docker rm dpbr-backend

# 2. 새 구조로 이동
mkdir -p ~/dpbr_deploy
mv ~/MSGS_13_B ~/dpbr_deploy/dpbr_backend

# 3. 새 경로에서 실행
cd ~/dpbr_deploy/dpbr_backend
docker compose up -d
```

### CI/CD 배포 실패

1. GitHub Secrets 확인 (`SSH_PRIVATE_KEY`, `SERVER_HOST`, `SERVER_USER`)
2. 서버에 `~/dpbr_deploy/dpbr_backend` 디렉토리 존재 확인
3. Docker가 설치되어 있고 실행 중인지 확인
4. 서버에서 GHCR 접근 권한 확인

## 📚 참고 문서

- [초기 서버 설정](./setup_server.sh) - 서버 환경 자동 설정
- [GitHub Actions 워크플로우](../.github/workflows/deploy.yml) - CI/CD 설정
- [Docker Compose 설정](../docker-compose.yml) - 컨테이너 구성
