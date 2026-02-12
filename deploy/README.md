# 배포 가이드

이 문서는 단풍바람 백엔드 서버를 Docker를 사용하여 배포하는 방법을 설명합니다.

> **참고**: 실제 배포 정보(IP, 사용자명, SSH 키 등)는 별도로 안전하게 관리하세요.

## 📋 목차

1. [서버 초기 설정](#1-서버-초기-설정)
2. [GitHub Secrets 설정](#2-github-secrets-설정)
3. [자동 배포 (CI/CD)](#3-자동-배포-cicd)
4. [수동 배포](#4-수동-배포)
5. [문제 해결](#5-문제-해결)

---

## 1. 서버 초기 설정

### 1.1 서버 접속

```bash
ssh <USERNAME>@<SERVER_IP>
```

### 1.2 Docker 설치

서버에 Docker가 설치되어 있지 않다면:

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 재로그인 필요
exit
```

### 1.3 프로젝트 디렉토리 설정

```bash
# 저장소 클론
git clone <YOUR_REPO_URL> ~/dpbr_backend
cd ~/dpbr_backend
```

---

## 2. GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

다음 secrets를 추가하세요:

| Secret 이름 | 값 | 설명 |
|------------|-----|------|
| `SSH_PRIVATE_KEY` | SSH 개인 키 전체 내용 | `~/.ssh/<your_key_file>` 파일 내용 |
| `SERVER_HOST` | `<SERVER_IP>` | 배포 서버 IP |
| `SERVER_USER` | `<USERNAME>` | 서버 사용자명 |
| `BACKEND_DEPLOY_PATH` | `/home/<USERNAME>/dpbr_backend` | 백엔드 프로젝트 경로 |

### 2.1 SSH 키 복사 방법

**로컬 머신에서:**
```bash
cat ~/.ssh/<your_key_file>
```

복사한 내용을 `SSH_PRIVATE_KEY` secret에 붙여넣으세요.

**중요:** 
- `-----BEGIN PRIVATE KEY-----`부터 `-----END PRIVATE KEY-----`까지 전체를 복사해야 합니다.
- 줄바꿈을 포함한 모든 내용을 그대로 복사하세요.

### 2.2 서버에 공개 키 등록 확인

서버의 `~/.ssh/authorized_keys`에 해당 SSH 키의 공개 키가 등록되어 있는지 확인하세요.

```bash
# 서버에서 실행
cat ~/.ssh/authorized_keys
```

---

## 3. 자동 배포 (CI/CD)

### 3.1 배포 트리거

다음 상황에서 자동으로 배포됩니다:

- `main` 브랜치에 push할 때
- GitHub Actions 탭에서 "Run workflow" 수동 실행

### 3.2 배포 프로세스

1. **PR 단계**: Docker 이미지 빌드 테스트 (push 안 함)
2. **Main Merge 후**:
   - Docker 이미지 빌드
   - GitHub Container Registry에 푸시
   - 서버에 SSH 접속
   - `docker compose pull` 실행
   - 서비스 재시작
3. **Health Check**: API 응답 확인

### 3.3 배포 확인

배포 후 다음 URL에서 확인하세요:

- Health Check: `http://<SERVER_IP>/health`
- API 문서: `http://<SERVER_IP>/docs`
- API 엔드포인트: `http://<SERVER_IP>/api/v1/characters`

---

## 4. 수동 배포

긴급한 경우 서버에서 수동으로 배포할 수 있습니다:

```bash
# 서버 접속
ssh <USERNAME>@<SERVER_IP>

# 프로젝트 디렉토리로 이동
cd ~/dpbr_backend

# 최신 코드 받기
git pull origin main

# GitHub Container Registry 로그인
echo "<YOUR_GITHUB_TOKEN>" | docker login ghcr.io -u <YOUR_GITHUB_USERNAME> --password-stdin

# 이미지 pull 및 재시작
docker compose pull
docker compose up -d

# 상태 확인
docker compose ps
docker compose logs -f
```

---

## 5. 문제 해결

### 5.1 서비스가 시작되지 않을 때

```bash
# 로그 확인
docker compose logs backend

# 컨테이너 상태 확인
docker compose ps

# 서비스 재시작
docker compose restart backend
```

### 5.2 포트가 이미 사용 중일 때

```bash
# 8000 포트를 사용하는 프로세스 확인
sudo lsof -i :8000

# 프로세스 종료
sudo kill -9 <PID>

# 서비스 재시작
docker compose restart
```

### 5.3 이미지 Pull 실패

```bash
# GitHub Container Registry 재로그인
echo "<YOUR_TOKEN>" | docker login ghcr.io -u <YOUR_USERNAME> --password-stdin

# 이미지 수동 pull
docker pull ghcr.io/<YOUR_ORG>/<YOUR_REPO>-backend:latest
```

### 5.4 데이터베이스 초기화

```bash
cd ~/dpbr_backend

# 볼륨 데이터 백업 (선택사항)
docker run --rm -v dpbr_backend-data:/data -v $(pwd):/backup alpine tar czf /backup/db_backup.tar.gz -C /data .

# DB 파일 삭제 (볼륨 내부)
docker compose down
docker volume rm dpbr_backend-data

# 서비스 재시작 (새 DB 생성)
docker compose up -d
```

### 5.5 메모리 부족

```bash
# 사용하지 않는 이미지 정리
docker image prune -a

# 사용하지 않는 컨테이너 정리
docker container prune

# 전체 시스템 정리 (주의!)
docker system prune -a --volumes
```

---

## 6. 유용한 명령어

```bash
# Docker Compose 명령어
docker compose ps                  # 컨테이너 상태
docker compose logs -f backend     # 실시간 로그
docker compose restart             # 재시작
docker compose down                # 중지
docker compose up -d               # 시작

# 리소스 모니터링
docker stats                       # 리소스 사용량
docker system df                   # 디스크 사용량

# 서버 정보
curl http://localhost/health                   # 헬스 체크
curl http://localhost/api/v1/characters        # API 테스트
```

---

## 📞 문의

문제가 발생하면 GitHub Issues에 등록해주세요.
