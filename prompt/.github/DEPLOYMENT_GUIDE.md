# 배포 프로세스 및 실패 처리 가이드

## 🔄 CI/CD 워크플로우

### 1️⃣ PR 단계 (Pull Request)

**실행되는 작업:**
```
✅ Docker 이미지 빌드 테스트 (push 안 함)
✅ 빌드 가능 여부 검증
```

**실패 시:**
- ❌ Merge 차단됨
- 🔧 빌드 오류를 수정한 후 다시 push
- GitHub Actions 탭에서 오류 로그 확인

**예시:**
```bash
# 로컬에서 빌드 테스트
docker build -t test .

# 문제 수정 후
git add .
git commit -m "fix: Resolve Docker build issue"
git push
```

---

### 2️⃣ Main 브랜치 Merge 후

**실행되는 작업:**
```
1. ✅ Docker 이미지 빌드
2. ✅ GitHub Container Registry에 Push
3. ✅ 서버에 자동 배포
4. ✅ 헬스 체크
```

**각 단계별 실패 처리:**

#### A. Docker 빌드 실패

**현상:**
- GitHub Actions에서 빌드 단계 실패
- 배포가 자동으로 중단됨

**대응:**
1. GitHub Actions 로그 확인
2. 로컬에서 빌드 테스트
   ```bash
   docker build -t test .
   ```
3. 문제 수정 후 새 커밋 push
4. **중요**: 이전 버전이 서버에서 계속 실행 중 (서비스 중단 없음)

#### B. 배포 실패

**현상:**
- Docker 이미지는 빌드되었으나 서버 배포 실패
- 자동 롤백 시도

**대응:**
1. GitHub Actions 로그에서 오류 확인
2. 서버 상태 확인
   ```bash
   ssh ark1st@168.107.45.180
   cd ~/dpbr_backend
   docker compose ps
   docker compose logs
   ```
3. 필요시 수동 롤백
   ```bash
   # 이전 이미지로 복구
   docker compose down
   docker compose pull <previous-tag>
   docker compose up -d
   ```

#### C. 헬스 체크 실패

**현상:**
- 배포는 완료되었으나 API 응답 없음

**대응:**
1. 서버 로그 확인
   ```bash
   docker compose logs -f backend
   ```
2. 컨테이너 상태 확인
   ```bash
   docker compose ps
   ```
3. 필요시 재시작
   ```bash
   docker compose restart backend
   ```

---

## 🚨 긴급 상황 대응

### 전체 서비스 다운

```bash
# 서버 접속
ssh ark1st@168.107.45.180
cd ~/dpbr_backend

# 상태 확인
docker compose ps
docker compose logs --tail=50

# 재시작
docker compose restart

# 완전 재시작 (필요시)
docker compose down
docker compose up -d
```

### 특정 버전으로 롤백

```bash
# 사용 가능한 이미지 태그 확인
docker images | grep dpbr-backend

# 특정 버전으로 롤백
docker tag ghcr.io/gc-maplewind/msgs_13_b-backend:main-abc1234 ghcr.io/gc-maplewind/msgs_13_b-backend:latest
docker compose up -d
```

### 데이터베이스 복구

```bash
# 백업 확인
ls -la backups/

# 복원
docker run --rm -v dpbr_backend-data:/data -v $(pwd)/backups:/backup alpine \
  tar xzf /backup/backup-YYYYMMDD-HHMMSS.tar.gz -C /data
```

---

## 📊 모니터링

### 실시간 로그 확인

```bash
# 백엔드 로그
docker compose logs -f backend

# 전체 서비스 로그
docker compose logs -f
```

### 리소스 사용량

```bash
# 컨테이너 리소스 확인
docker stats

# 디스크 사용량
docker system df
```

### 헬스 체크

```bash
# API 엔드포인트
curl http://168.107.45.180/api/v1/characters

# 헬스 체크 엔드포인트
curl http://168.107.45.180/health
```

---

## 🔐 보안 및 권한

### GitHub Secrets 필수 항목

| Secret | 설명 | 확인 방법 |
|--------|------|----------|
| `SSH_PRIVATE_KEY` | SSH 접속 키 | `cat ~/.ssh/ssh-key-2026-01-09.key` |
| `SERVER_HOST` | 서버 IP | `168.107.45.180` |
| `SERVER_USER` | 서버 사용자 | `ark1st` |
| `DEPLOY_PATH` | 배포 경로 | `/home/ark1st/dpbr_backend` |

### Secrets 업데이트

1. GitHub → Settings → Secrets and variables → Actions
2. Secret 선택 → Update secret
3. 새 값 입력 후 저장

---

## 📞 문제 해결 체크리스트

- [ ] GitHub Actions 로그 확인
- [ ] 서버 SSH 접속 가능 여부
- [ ] Docker 컨테이너 실행 상태
- [ ] 로그에서 오류 메시지 확인
- [ ] 디스크 용량 충분한지 확인
- [ ] 네트워크 연결 상태
- [ ] GitHub Secrets 올바르게 설정되었는지

---

## 🎯 베스트 프랙티스

1. **작은 단위로 배포**: 큰 변경사항은 여러 PR로 분할
2. **PR 단계에서 충분히 테스트**: Merge 전 빌드 성공 확인
3. **배포 시간 고려**: 트래픽이 적은 시간대 배포
4. **백업**: 중요 변경 전 데이터베이스 백업
5. **모니터링**: 배포 후 5-10분간 로그 및 헬스 체크 모니터링
6. **문서화**: 특이사항 발생 시 이 문서 업데이트

---

## 📚 참고 자료

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
