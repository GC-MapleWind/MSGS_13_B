# 📊 현재 배포 상태

**최종 업데이트**: 2026-02-10

## ✅ 완료된 작업

### 1. CI/CD 파이프라인 구축
- ✅ GitHub Actions 워크플로우 생성 (`.github/workflows/deploy.yml`)
- ✅ Docker 기반 배포 전략 수립
- ✅ PR 검증 / Main 배포 분리
- ✅ Health check & Rollback 로직 구현

### 2. 서버 설정
- ✅ SSH 키 기반 인증 설정
- ✅ Git & Docker 설치 완료
- ✅ 배포 디렉토리 생성 (`~/MSGS_13_B`)

### 3. Docker 구성
- ✅ `Dockerfile` 작성 (Python 3.12 + FastAPI)
- ✅ `docker-compose.yml` 작성
- ✅ `.dockerignore` 작성
- ✅ Health check endpoint 추가 (`/health`)

### 4. GitHub Secrets 설정
- ✅ `SSH_PRIVATE_KEY`: 서버 접속 키
- ✅ `SERVER_HOST`: `168.107.45.180`
- ✅ `SERVER_USER`: `ark1st`
- ✅ `BACKEND_DEPLOY_PATH`: `~/MSGS_13_B`

## ⚠️ 임시방편 (현재 상태)

### 배포 방식
**현재**: 서버에서 직접 Docker 빌드
```bash
cd ~/MSGS_13_B
docker build -t dpbr-backend:latest .
docker compose up -d
```

**이유**: GHCR private 이미지 pull 시 인증 오류
```
error from registry: denied
```

### docker-compose.yml (현재)
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    image: dpbr-backend:latest  # 로컬 빌드 이미지 사용
```

## 🔴 남은 작업

### 우선순위 1: GHCR 인증 설정 ⏳
**문서**: `deploy/TODO_GHCR_AUTH.md` 참조

1. GitHub Personal Access Token 생성 (`read:packages`)
2. 서버에서 GHCR 로그인
   ```bash
   echo 'TOKEN' | docker login ghcr.io -u GC-MapleWind --password-stdin
   ```
3. `docker-compose.yml`을 표준 방식으로 복원
   ```yaml
   services:
     backend:
       image: ghcr.io/gc-maplewind/msgs_13_b-backend:latest
   ```

### 우선순위 2: 프론트엔드 CI/CD
- `dpbr_2026/dpbr_front` 프로젝트 배포 설정

## 🏥 서버 상태

```
서버: ark1st@168.107.45.180
배포 경로: ~/MSGS_13_B
컨테이너: dpbr-backend (실행 중)
포트: 8000
```

**Health Check**:
```bash
curl http://168.107.45.180:8000/health
# 예상 응답: {"status":"healthy"}
```

**API Endpoint**:
```bash
curl http://168.107.45.180:8000/api/v1/characters
```

## 📚 관련 문서

- `.github/DEPLOYMENT_GUIDE.md`: 배포 가이드 및 트러블슈팅
- `deploy/README.md`: 배포 설정 문서
- `deploy/TODO_GHCR_AUTH.md`: GHCR 인증 설정 TODO

## 🔗 유용한 링크

- **GitHub Actions**: https://github.com/GC-MapleWind/MSGS_13_B/actions
- **GHCR 패키지**: https://github.com/orgs/GC-MapleWind/packages
- **현재 PR**: https://github.com/GC-MapleWind/MSGS_13_B/pull/3

---

**다음 작업 시작 시**: `deploy/TODO_GHCR_AUTH.md` 먼저 확인
