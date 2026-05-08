---
name: split chatbot postgres migration
overview: 챗봇을 별도 git repo `GC-MapleWind/maplewind-chatbot` 으로 완전 분리하면서 메인 backend와 챗봇 모두 SQLite → PostgreSQL(단일 인스턴스, DB 2개) 로 마이그레이션. 운영 데이터는 양쪽 모두 보존.
todos:
  - id: phase0-prep
    content: "Phase 0: 운영 SQLite 백업 확보 + 신규 repo 생성 + Postgres/pgloader 에셋 결정"
    status: in_progress
  - id: phase1-deps
    content: "Phase 1: 의존성 교체 (asyncpg + psycopg + alembic 추가, aiosqlite 제거)"
    status: completed
  - id: phase1-compose
    content: "Phase 1: docker-compose에 postgres 서비스 + postgres-init.sql 두 DB 생성"
    status: completed
  - id: phase1-codefix
    content: "Phase 1: SQLite 전용 코드 정리 (database_chatbot.py URL/PRAGMA, models/chatbot.py JSON server_default, main.py 마이그레이션 가드 재검토)"
    status: completed
  - id: phase1-alembic
    content: "Phase 1: Alembic 도입 + 초기 migration 생성 (메인 metadata만)"
    status: completed
  - id: phase1-migrator
    content: "Phase 1: pgloader 기반 SQLite→Postgres 데이터 이전 스크립트 작성 + 로컬 검증"
    status: completed
  - id: phase2-extract
    content: "Phase 2: git filter-repo 로 챗봇 파일들을 이력 보존하며 신규 repo로 추출"
    status: completed
  - id: phase2-newrepo
    content: "Phase 2: 신규 repo 구조 세팅 (main.py, config.py, alembic, Dockerfile, pyproject.toml, .env.example)"
    status: completed
  - id: phase2-cleanup
    content: "Phase 2: 메인 repo 청소 (chatbot 파일 삭제 + main.py/admin.py/pyproject 수정)"
    status: completed
  - id: phase2-cicd
    content: "Phase 2: 신규 repo CI/CD workflow (ci.yml + deploy.yml + GHCR 이미지 푸시)"
    status: in_progress
  - id: phase3-cutover
    content: "Phase 3: 운영 컷오버 (Postgres 기동 + pgloader 데이터 이전 + 두 서비스 배포 + webhook URL 변경)"
    status: pending
  - id: phase3-verify
    content: "Phase 3: 컷오버 후 검증 (메인 API + 챗봇 메생결산 끝단 끝단 1회)"
    status: pending
  - id: phase4-cleanup
    content: "Phase 4: 문서/도커 설정 정리 + README 업데이트"
    status: completed
isProject: false
---

## Execution status — 2026-05-09

- Remaining external gates and their evidence templates are indexed in `specs/001-split-chatbot-postgres/operator-handoff-index.md`; observable remote status can be checked with `specs/001-split-chatbot-postgres/check-external-gates.sh`.
- Latest external-gate check input was `origin/dev` `3f9912b304bd241a224a7a801b5549028046a26a`; later docs-only audit commits may advance `dev` without changing implementation state.
- Latest dev workflow evidence: run `25576285116` succeeded for commit `e87e71863a1dacc0662e995696ae9e348ce61426`, including `Build and Push Dev Image` and `Deploy to Dev Server`, after preserving `scripts/migrate_sqlite_to_postgres.sh` as executable. Earlier runs `25574864234` and `25574451603` also succeeded.

- Main repo PR #54 is merged into `dev` as merge commit `eafce94c`; the
  post-merge dev workflow run `25567914804` passed `Build and Push Dev Image`
  and `Deploy to Dev Server`.
- Recent `dev` evidence head before the T024/lifespan sync was `98419800cb139714dfe90aa9c28697484dc649ff`; latest dependency-cleanup evidence commit is `7d70ea9ae35fc6ddc884b0af88dcf051bff20ff0`.
  That commit closes the remaining local FR-007/SC-006 gap by removing
  `aiosqlite` from `pyproject.toml`/`uv.lock`, switching runtime-seeding tests
  to temporary `postgres:17-alpine`, and adding explicit FR/SC coverage to
  `specs/001-split-chatbot-postgres/completion-audit.md`. Dev CI/CD run
  `25570800233` completed successfully.
- Durable handoff evidence is published from `dev` at
  `omx_wiki/split-chatbot-postgresql-migration-handoff.md`, and both open
  blocker issues link back to that handoff page. Verify the current `dev` hash
  with `git ls-remote origin refs/heads/dev` because evidence-only commits may
  advance the branch without changing implementation state.
- Chatbot remote `GC-MapleWind/maplewind-chatbot` `main` is
  `25ba79950d452fa07aadf486d253c4c7eb6f3b71`, a documentation descendant of
  history-adopting merge commit `5e6c20d` with runtime parent `b3d80a9` and
  filtered-history parent `d725f8f`; `git diff 5e6c20d^1 5e6c20d` was empty,
  so the runtime tree was preserved. Local verification on runtime commit
  `b3d80a9` passed lint, unittest, SQLite fallback simulation, and
  PostgreSQL-backed 메생결산 simulation. The chatbot README now documents env, Kakao webhook, operations, simulation usage, integrated compose deployment ownership, and the 7-day compatibility route; `src/main.py` lifespan now runs Alembic `upgrade head` before serving requests, dev compose uses a named PostgreSQL volume, and local compose `/health` boot passes even with dummy Google credentials.
- Chatbot CI/CD workflow files originated from local branch
  `workflows-pending-scope` commit `6ab860c`; the updated patch is preserved as
  `specs/001-split-chatbot-postgres/chatbot-workflows-pending.patch`. The
  patch was rechecked and locally simulated against current chatbot `origin/main`
  `25ba79950d452fa07aadf486d253c4c7eb6f3b71` (patch apply, frozen sync, ruff, unittest, Alembic offline/online, Docker build, and `:<full sha>` tag-shape check) and
  applies cleanly; direct push is blocked because the
  current GitHub OAuth credential lacks `workflow` scope
  (`X-Oauth-Scopes: gist, read:org, repo`). evidence capture is templated in
  `specs/001-split-chatbot-postgres/chatbot-workflow-evidence-template.md`. Handoff issue:
  https://github.com/GC-MapleWind/maplewind-chatbot/issues/1
- Production/staging cutover, Kakao webhook change, SLA/load validation, and
  24h/7d monitoring gates remain pending operational work; evidence capture is templated in
  `specs/001-split-chatbot-postgres/production-cutover-evidence-template.md`. Handoff issue:
  https://github.com/GC-MapleWind/MSGS_13_B/issues/55
- README/docs/audit cleanup is complete; phase4-cleanup is marked completed. T042/T043 remain post-cutover cleanup/retention gates.
- T042 removal of `migrate_user_student_id_to_username` remains gated by the
  post-cutover/post-run verification prerequisite in `tasks.md`; do not remove
  it as an isolated local cleanup before that operational evidence exists.

## 큰 그림

```mermaid
flowchart LR
    subgraph current [현재 상태]
        sqlite1[(maplewind.db SQLite)]
        sqlite2[(chatbot.db SQLite)]
        backend[backend FastAPI<br/>chatbot router 포함]
        sqlite1 --- backend
        sqlite2 --- backend
    end

    subgraph target [목표 상태]
        pg[(PostgreSQL 단일 인스턴스)]
        pgmw[(maplewind DB)]
        pgcb[(chatbot DB)]
        pg --- pgmw
        pg --- pgcb

        mainRepo["GC-MapleWind/msgs_13_b<br/>backend (메인)"]
        cbRepo["GC-MapleWind/maplewind-chatbot<br/>(신규 repo)"]

        mainRepo --> pgmw
        cbRepo --> pgcb
    end

    current ==> target
```

## Phase 순서

**권장: Phase 1(메인 Postgres 마이그) → Phase 2(챗봇 추출 + 챗봇 Postgres) 병렬 가능**. 두 작업이 코드 영역이 거의 겹치지 않고, 챗봇 코드를 추출하면서 동시에 Postgres 호환 작업을 신규 repo에서 진행할 수 있어 시간 절약. 단 운영 컷오버는 한 번에 묶어서 진행.

## Phase 0 — 사전 준비 (1~2시간)

- 운영 서버에서 SQLite 백업 확보: `cp data/maplewind.db data/maplewind.db.bak.$(date +%F)` 와 동일하게 `chatbot.db` 도. 백업 파일을 로컬로 가져옴.
- 신규 repo 생성: `GC-MapleWind/maplewind-chatbot` (private, 빈 repo).
- Postgres 17 이미지 결정 + `pgvector` 등 추가 확장 불필요 확인.
- `pgloader` 로컬 설치 또는 Docker 이미지 (`dimitri/pgloader`) 확인 — SQLite → Postgres 데이터 이전 도구.

## Phase 1 — 메인 repo Postgres 마이그레이션 (현 repo 내, 챗봇은 그대로 둔 채)

### 1-1. 의존성 변경 ([pyproject.toml](../../pyproject.toml))

- 추가: `asyncpg>=0.30`, `psycopg[binary]>=3.2` (sync 도구용), `alembic>=1.14`
- 유지: `sqlalchemy>=2.0.46`, `greenlet>=3.3.1` (Postgres 계열에 쓰임)
- 제거: `aiosqlite` (Postgres 전환 후 불필요)

### 1-2. docker-compose 에 Postgres 서비스 추가 ([docker-compose.yml](../../docker-compose.yml))

```yaml
services:
  postgres:
    image: postgres:17-alpine
    container_name: dpbr-postgres
    restart: unless-stopped
    volumes:
      - ./data/pg:/var/lib/postgresql/data
      - ./scripts/postgres-init.sql:/docker-entrypoint-initdb.d/01-create-databases.sql:ro
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]

  backend:
    depends_on:
      postgres: {condition: service_healthy}
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/maplewind
```

`scripts/postgres-init.sql` (신규) 에서 `CREATE DATABASE maplewind;` `CREATE DATABASE chatbot;` 두 DB 자동 생성.

### 1-3. 코드 Postgres 호환성 fix

| 파일 | 문제 | 조치 |
|------|------|------|
| [src/database.py](../../src/database.py) L11 | 기본값이 SQLite | env var 강제, default 제거하고 fail-fast |
| [src/database.py](../../src/database.py) L14~31 | SQLite-only 가드 | 그대로 둠 (Postgres에서는 no-op) |
| `src/database_chatbot.py` L11~28 | SQLite 경로 하드코딩 + PRAGMA 무가드 | `CHATBOT_DATABASE_URL` env var, dialect 가드 추가 |
| `src/models/chatbot.py` L38 | `JSON` 타입 + `server_default='{}'` | Postgres에서는 `JSONB` + `server_default=text("'{}'::jsonb")`. dialect-agnostic 하려면 `from sqlalchemy.dialects.postgresql import JSONB` + `JSON().with_variant(JSONB, "postgresql")` |
| [src/main.py](../../src/main.py) L90~131 `migrate_user_student_id_to_username` | SQLite PRAGMA 사용, 이미 dialect 가드(L93) 있음 | 운영에서 한 번 더 실행 후 함수 자체 제거 가능, 일단 유지 |
| `src/repositories/chatbot_repo.py` L80 `case()` | SQLAlchemy core, 양쪽 호환 | 변경 불필요 |

### 1-4. Alembic 도입

- `alembic init src/alembic` (메인용)
- `env.py` 에서 두 metadata (Base, ChatbotBase) 모두 import 후 `target_metadata = [Base.metadata, ChatbotBase.metadata]` 사용 또는 두 alembic 환경 분리. 챗봇은 어차피 Phase 2에서 신규 repo로 빠지므로 **메인은 메인 metadata만, 챗봇 alembic은 신규 repo에서 별도 구성**.
- 초기 migration: `alembic revision --autogenerate -m "initial schema"` 으로 현재 SQLite 스키마와 동일한 Postgres DDL 생성.
- 운영 배포 시 `alembic upgrade head` 가 lifespan 또는 entrypoint 에서 실행.

### 1-5. 데이터 마이그레이션 스크립트 ([scripts/migrate_sqlite_to_postgres.py](../../scripts/migrate_sqlite_to_postgres.py) 신규)

- 옵션 A (권장): `pgloader` 사용

```bash
docker run --rm --network dpbr-main_default \
  -v $(pwd)/data:/data:ro \
  dimitri/pgloader:latest \
  pgloader sqlite:///data/maplewind.db.bak postgresql://user:pass@postgres:5432/maplewind
```

- 옵션 B: Python 스크립트로 SQLAlchemy 양쪽 연결 후 row-by-row insert (제어성 ↑, 시간 ↑)

운영 데이터 검증: row count 비교 + 핵심 테이블 (users, characters, settlements) 샘플 체크.

### 1-6. 의존성 변경 PR + 검증

- 로컬 `docker compose up postgres backend` 로 기동 확인
- `uv run python -m unittest tests/...` 회귀 테스트 통과
- 메생결산 시뮬레이션 (`scripts/simulate_maesaeng_flow.py`) 가 Postgres 위에서 통과하는지 확인 (스크립트의 `os.environ["DATA_DIR"]` 부분은 Postgres 환경 변수로 교체 필요)

## Phase 2 — 챗봇 추출 + 신규 repo (Phase 1과 병렬 가능)

### 2-1. 신규 repo 디렉토리 구조 (`maplewind-chatbot`)

```
maplewind-chatbot/
  src/
    main.py                  # FastAPI app, lifespan
    config.py                # 환경변수 로딩
    database.py              # 챗봇 Postgres (이전 src/database_chatbot.py)
    admin.py                 # TemporaryImage/EventInfo/InfoList ModelView
    models/
      chatbot.py             # 이전 src/models/chatbot.py
    schemas/
      chatbot_dto.py
    repositories/
      chatbot_repo.py
    services/
      chatbot_service.py
      google_sheet_service.py
    controller/v1/
      chatbot.py
    alembic/
      versions/0001_initial.py
      env.py
  tests/
    test_event_date_gating.py
  scripts/
    simulate_maesaeng_flow.py
  Dockerfile
  docker-compose.dev.yml     # 개발용 (postgres 포함)
  pyproject.toml
  .env.example
  README.md
  .github/workflows/
    ci.yml
    deploy.yml
```

### 2-2. 신규 repo 의존성 (`maplewind-chatbot/pyproject.toml`)

핵심만:

```
fastapi, uvicorn[standard], sqlalchemy>=2.0.46, asyncpg, alembic,
httpx, google-api-python-client, gspread, sqladmin, itsdangerous, dotenv,
greenlet
```

메인 repo에는 `gspread`, `google-api-python-client` 더 이상 필요 없으므로 제거.

### 2-3. 신규 repo 코드 변경

- 신규 `maplewind-chatbot/src/main.py`: chatbot router 만 등록, lifespan에서 `init_chatbot_db()` (또는 `alembic upgrade head`).
- import 경로 변경: `from src.database_chatbot import ...` → `from src.database import ...`. 모듈명 컨플릭트 없음.
- `src/services/chatbot_service.py` L9 의 `from src.database_chatbot import get_chatbot_db` 도 동일 변경.
- [src/admin.py](../../src/admin.py) 에서 챗봇 ModelView (TemporaryImage/EventInfo/InfoList) 부분만 신규 repo로 이동.

### 2-4. git 이력 보존 — `git filter-repo`

- 메인 repo 의 챗봇 관련 파일 목록을 `--path` 인자로 지정하여 새 repo로 추출:

```bash
git clone https://github.com/GC-MapleWind/msgs_13_b chatbot-extract
cd chatbot-extract
git filter-repo \
  --path src/services/chatbot_service.py \
  --path src/services/google_sheet_service.py \
  --path src/services/chinbabang_service.py \
  --path src/repositories/chatbot_repo.py \
  --path src/models/chatbot.py \
  --path src/schemas/chatbot_dto.py \
  --path src/controller/v1/chatbot.py \
  --path src/database_chatbot.py \
  --path tests/test_event_date_gating.py \
  --path scripts/simulate_maesaeng_flow.py
git remote add origin https://github.com/GC-MapleWind/maplewind-chatbot.git
git push -u origin main
```

- 추출 후 신규 repo에서 디렉토리 재배치, `pyproject.toml`/Dockerfile 등 신규 파일 추가.
- `archive/chinbabang-submission` 브랜치는 메인 repo와 신규 repo 양쪽에 모두 남김 (혹시 있을 복원 필요 대비).

### 2-5. 메인 repo 청소 PR

다음 파일/항목 삭제 또는 수정:

- 삭제: 위 git filter-repo 의 모든 `--path` 파일들
- [src/main.py](../../src/main.py): `from src.controller.v1.chatbot import router as chatbot_router` 줄, `from src.database_chatbot import init_chatbot_db` 줄, `await init_chatbot_db()`, `app.include_router(chatbot_router, ...)` 모두 제거
- [src/admin.py](../../src/admin.py): `EventInfoAdmin`, `InfoListAdmin`, `TemporaryImageAdmin` 세 ModelView 와 `add_view` 호출 + import 제거. `chatbot_async_session` import 도 제거
- [pyproject.toml](../../pyproject.toml): `gspread`, `google-api-python-client` 제거
- 운영 [docker-compose.yml](../../docker-compose.yml): `google-credentials.json` 마운트 제거 가능

### 2-6. 신규 repo CI/CD

- GitHub Actions workflow:
  - `ci.yml`: lint(ruff) + tests(pytest 도입) + Postgres service container
  - `deploy.yml`: `main` 브랜치 push 시 GHCR 이미지 빌드 (`ghcr.io/gc-maplewind/maplewind-chatbot:latest`) 후 운영 서버 SSH 배포
- 운영 docker-compose 가 어디에 있는지에 따라 배포 방식 결정. 권장: **운영 서버에 단일 통합 docker-compose 두기** — 두 repo의 GHCR 이미지를 pull 하여 함께 기동. 이 통합 compose 파일은 `gc-maplewind/deployment` 같은 별도 repo 또는 backend repo `deploy/` 폴더에 둠.

## Phase 3 — 통합 배포 (예상 다운타임 30분)

### 순서

1. 메인 backend Postgres PR 머지 → 운영에 새 이미지 배포 준비
2. 신규 repo 첫 배포: `maplewind-chatbot:latest` 이미지 GHCR 푸시
3. **컷오버 윈도우 시작**: 카카오 챗봇 사용량 적은 시간대 선택 (새벽)
4. 운영 서버에서:
   ```
   docker compose down backend
   pgloader sqlite:///data/maplewind.db.bak.YYYY-MM-DD postgresql://...maplewind
   pgloader sqlite:///data/chatbot.db.bak.YYYY-MM-DD postgresql://...chatbot
   docker compose up -d postgres backend chatbot
   ```
5. 카카오 오픈빌더 webhook URL 변경: `https://api.maplewind.com/chatbot/chat` → `https://chatbot.maplewind.com/chatbot/chat` (또는 reverse proxy 라우팅 변경)
6. 검증:
   - `/health` 양쪽 200 응답
   - 메인 API 핵심 엔드포인트 (캐릭터 목록, 결산 목록) 응답 확인
   - 카카오에서 "메생결산" 발화 1회 → 시트 기록 확인
7. **컷오버 윈도우 종료**

### 롤백 플랜

- pgloader 실패 시: backend 컨테이너를 이전 이미지(SQLite 버전)로 롤백, 카카오 webhook도 원위치
- 부분 실패 시: 챗봇 컨테이너만 재기동, 메인은 그대로 유지 (이게 분리의 핵심 이득)

## Phase 4 — 정리

- [docker-compose.dev.yml](../../docker-compose.dev.yml) 에서 챗봇 관련 마운트 제거
- [scripts/](../../scripts/) 폴더 정리 (챗봇 시뮬레이션은 신규 repo로 이동 완료)
- 메인 repo `README.md` 에서 챗봇 섹션 → 신규 repo 링크로 변경
- 신규 repo `README.md` 에 운영 가이드, 환경변수, 카카오 webhook 설정법 작성

## 위험 요소 / 의사결정 포인트

- **JSONB 사용 여부**: SQLAlchemy `JSON` 타입을 Postgres에서 그대로 두면 `JSON` 컬럼 (text 기반) 으로 생성됨. 검색 성능 안 중요하므로 그냥 `JSON` 두는 것도 OK. `JSONB` 로 가려면 dialect-specific 변환 필요.
- **Alembic 단일 metadata vs 분리**: 신규 repo가 챗봇만 관리하므로 분리가 자연스러움. 메인 repo도 메인 metadata만 관리.
- **운영 데이터 마이그 시점**: pgloader 가 SQLite 락을 걸 수 있으므로 backend 컨테이너 down 후 실행. 미리 dry-run 으로 schema 호환성 검증.
- **운영 secret 관리**: `google-credentials.json` 은 챗봇 컨테이너만 마운트. 메인 backend는 더 이상 필요 없음.
- **카카오 webhook URL 변경 vs reverse proxy**: 단일 도메인 + nginx path-based routing 이 webhook URL 변경 부담 줄임. 별도 서브도메인이 깔끔하지만 카카오 빌더에서 URL 수정 필요.

## 예상 작업량

- Phase 0: 1~2시간
- Phase 1: 0.5~1일 (의존성 + Alembic + 마이그 스크립트)
- Phase 2: 1일 (filter-repo 추출 + 신규 repo 구성 + CI/CD)
- Phase 3: 0.5일 (운영 컷오버 윈도우)
- Phase 4: 2~3시간

총 2.5~3일 소요 예상.
