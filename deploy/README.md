# 배포 가이드

이 문서는 단풍바람 백엔드 서버를 배포하는 방법을 설명합니다.

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
ssh ark1st@168.107.45.180
```

### 1.2 초기 설정 스크립트 실행

서버에서 다음 명령어를 실행합니다:

```bash
# 스크립트 다운로드 (또는 직접 복사)
curl -o setup_server.sh https://raw.githubusercontent.com/YOUR_USERNAME/dpbr_13_B/main/deploy/setup_server.sh

# 실행 권한 부여
chmod +x setup_server.sh

# 환경 변수 설정 후 실행
export REPO_URL="https://github.com/YOUR_USERNAME/dpbr_13_B.git"
export DEPLOY_PATH="/home/ark1st/dpbr_backend"

# 스크립트 실행
./setup_server.sh
```

이 스크립트는 자동으로 다음 작업을 수행합니다:
- 필수 패키지 설치 (Python, Git, uv)
- 저장소 클론
- 의존성 설치
- systemd 서비스 설정
- 서비스 시작

### 1.3 Nginx 설정 (선택사항)

프론트엔드와 함께 배포하려면 Nginx를 설정합니다:

```bash
# Nginx 설치
sudo apt-get install -y nginx

# 설정 파일 복사
sudo cp deploy/nginx.conf /etc/nginx/sites-available/dpbr

# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/dpbr /etc/nginx/sites-enabled/

# 기본 사이트 비활성화
sudo rm /etc/nginx/sites-enabled/default

# Nginx 재시작
sudo systemctl restart nginx
```

---

## 2. GitHub Secrets 설정

GitHub Actions가 서버에 자동으로 배포하려면 다음 secrets를 설정해야 합니다.

### 2.1 SSH 키 등록

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

다음 secrets를 추가하세요:

| Secret 이름 | 값 | 설명 |
|------------|-----|------|
| `SSH_PRIVATE_KEY` | SSH 개인 키 전체 내용 | `~/.ssh/ssh-key-2026-01-09.key` 파일 내용 |
| `SERVER_HOST` | `168.107.45.180` | 배포 서버 IP |
| `SERVER_USER` | `ark1st` | 서버 사용자명 |
| `BACKEND_DEPLOY_PATH` | `/home/ark1st/dpbr_backend` | 백엔드 프로젝트 경로 |

### 2.2 SSH 키 복사 방법

**Windows (WSL):**
```bash
cat ~/.ssh/ssh-key-2026-01-09.key
```

복사한 내용을 `SSH_PRIVATE_KEY` secret에 붙여넣으세요.

**중요:** 
- `-----BEGIN PRIVATE KEY-----`부터 `-----END PRIVATE KEY-----`까지 전체를 복사해야 합니다.
- 줄바꿈을 포함한 모든 내용을 그대로 복사하세요.

### 2.3 서버에 공개 키 등록 확인

서버의 `~/.ssh/authorized_keys`에 해당 SSH 키의 공개 키가 등록되어 있는지 확인하세요.

```bash
# 서버에서 실행
cat ~/.ssh/authorized_keys
```

---

## 3. 자동 배포 (CI/CD)

GitHub Actions가 설정되면 자동 배포가 활성화됩니다.

### 3.1 배포 트리거

다음 상황에서 자동으로 배포됩니다:

- `main` 브랜치에 push할 때
- GitHub Actions 탭에서 "Run workflow" 수동 실행

### 3.2 배포 프로세스

1. **Test 단계**: 린팅 및 테스트 실행 (선택적)
2. **Deploy 단계**: 
   - 서버에 SSH 접속
   - 최신 코드 pull
   - 의존성 업데이트
   - 서비스 재시작
3. **Health Check**: API 응답 확인

### 3.3 배포 확인

배포 후 다음 URL에서 확인하세요:

- API 문서: http://168.107.45.180:8000/docs
- API 엔드포인트: http://168.107.45.180:8000/api/v1/characters

---

## 4. 수동 배포

긴급한 경우 서버에서 수동으로 배포할 수 있습니다:

```bash
# 서버 접속
ssh ark1st@168.107.45.180

# 프로젝트 디렉토리로 이동
cd /home/ark1st/dpbr_backend

# 최신 코드 받기
git pull origin main

# 의존성 업데이트
uv sync

# 서비스 재시작
sudo systemctl restart dpbr-backend

# 상태 확인
sudo systemctl status dpbr-backend
```

---

## 5. 문제 해결

### 5.1 서비스가 시작되지 않을 때

```bash
# 로그 확인
sudo journalctl -u dpbr-backend -n 50 --no-pager

# 실시간 로그 확인
sudo journalctl -u dpbr-backend -f

# 서비스 상태 확인
sudo systemctl status dpbr-backend
```

### 5.2 포트가 이미 사용 중일 때

```bash
# 8000 포트를 사용하는 프로세스 확인
sudo lsof -i :8000

# 프로세스 종료
sudo kill -9 <PID>

# 서비스 재시작
sudo systemctl restart dpbr-backend
```

### 5.3 의존성 문제

```bash
# uv 캐시 삭제
rm -rf ~/.cache/uv

# 의존성 재설치
uv sync --reinstall
```

### 5.4 권한 문제

```bash
# 프로젝트 디렉토리 소유권 확인
ls -la /home/ark1st/dpbr_backend

# 소유권 변경 (필요시)
sudo chown -R ark1st:ark1st /home/ark1st/dpbr_backend
```

### 5.5 데이터베이스 초기화

```bash
cd /home/ark1st/dpbr_backend

# 기존 DB 백업
mv maplewind.db maplewind.db.backup

# 서비스 재시작 (새 DB 자동 생성)
sudo systemctl restart dpbr-backend
```

---

## 6. 유용한 명령어

```bash
# 서비스 관리
sudo systemctl start dpbr-backend      # 시작
sudo systemctl stop dpbr-backend       # 중지
sudo systemctl restart dpbr-backend    # 재시작
sudo systemctl status dpbr-backend     # 상태 확인

# 로그 확인
sudo journalctl -u dpbr-backend -f     # 실시간 로그
sudo journalctl -u dpbr-backend -n 100 # 최근 100줄

# 서버 정보
curl http://localhost:8000/api/v1/characters  # API 테스트
netstat -tuln | grep 8000                      # 포트 확인
```

---

## 📞 문의

문제가 발생하면 GitHub Issues에 등록해주세요.
