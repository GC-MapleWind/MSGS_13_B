# 🔧 GHCR 인증 설정 TODO

## 현재 상황 (2026-02-10)

### ❌ 문제점
- GitHub Container Registry의 이미지가 **private**
- 서버에서 `docker compose pull` 시 `error from registry: denied` 발생
- **임시방편**: 서버에서 직접 빌드하여 배포 중 (표준 방식 아님)

### 🎯 목표
표준 CI/CD 방식으로 변경:
```
GitHub Actions (빌드) → GHCR (push) → 서버 (pull & 실행)
```

## 🔐 해결 방법

### STEP 1: GitHub Personal Access Token 생성

1. https://github.com/settings/tokens/new 접속
2. 설정:
   - **Note**: `DPBR Server GHCR Access`
   - **Expiration**: 90 days (또는 No expiration)
   - **Scopes**: ✅ `read:packages` 선택
3. **Generate token** 클릭
4. 생성된 토큰 복사 (한 번만 표시됨!)

### STEP 2: 서버에서 GHCR 로그인

```bash
# SSH로 서버 접속
ssh -i ~/.ssh/deploy_key ark1st@168.107.45.180

# Docker login (YOUR_TOKEN을 실제 토큰으로 변경)
echo 'YOUR_TOKEN' | docker login ghcr.io -u GC-MapleWind --password-stdin
```

### STEP 3: docker-compose.yml 원래대로 복원

현재 `docker-compose.yml`:
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    image: dpbr-backend:latest
```

변경 후 (표준 방식):
```yaml
services:
  backend:
    image: ghcr.io/gc-maplewind/msgs_13_b-backend:latest
```

### STEP 4: 서버에서 테스트

```bash
cd ~/MSGS_13_B
docker compose pull
docker compose up -d
```

## 📝 참고사항

- 서버 재부팅 시 Docker 로그인 유지됨 (credentials 저장됨)
- Token은 안전하게 보관 필요
- Token 만료 시 재생성 후 다시 로그인

## 🚀 완료 후 체크리스트

- [ ] GitHub Token 생성
- [ ] 서버에서 `docker login` 완료
- [ ] `docker-compose.yml` 원래 방식으로 복원
- [ ] GitHub Actions 워크플로우 정상 작동 확인
- [ ] 이 파일 삭제

---

**생성일**: 2026-02-10  
**상태**: ⏳ 보류 (나중에 처리)
