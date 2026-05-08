---

description: "Task list for split-chatbot-postgres feature"
---

# Tasks: Split Chatbot Service & PostgreSQL Migration

**Input**: Design documents from `/specs/001-split-chatbot-postgres/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md)

**Tests**: 회귀 테스트는 `unittest` 와 `scripts/simulate_maesaeng_flow.py` 로 검증. 신규
컨트랙트 테스트는 본 작업 범위 외 (인프라 마이그가 주 목적).

**Organization**: 헌법의 SDD lifecycle 에 따라 User Story 단위로 그룹화. P1 (메생결산
무중단 + 데이터 보존) 이 MVP 기준선이며, P2/P3 는 분리 배포 / SLA 격리 가치를 추가한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = 메생결산 무중단 (P1) / US2 = 챗봇 독립 배포 (P2) / US3 = SLA 격리 (P3)
- 파일 경로는 메인 repo 기준 (`./` = 현 repo 루트). 신규 repo 경로는 `chatbot-repo/...` 표기

## Execution status overlay — 2026-05-09

The checkboxes below preserve the original implementation plan. Use this overlay plus
[completion-audit.md](./completion-audit.md) as the current execution state:

- **Verified complete**: T002-T028, T031-T034.
- **Prepared but externally blocked**: T029-T030. The workflow patch is preserved in
  [chatbot-workflows-pending.patch](./chatbot-workflows-pending.patch) and applies
  cleanly to chatbot `origin/main`, but pushing workflow files requires a GitHub
  credential/app with `workflow` scope.
- **Production/ops-gated**: T001, T035-T039, T042-T043. These require production or
  staging authority, backup/cutover execution, webhook/SLA/monitoring evidence, or
  post-run retention cleanup.
- **Documentation complete**: T040-T041. Main README and chatbot README/env/webhook/simulation docs are
  present; production runbooks and handoff issues remain the operational source of
  truth.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 모든 phase 가 공유하는 안전망 — 백업, 신규 repo 생성, 도구 검증.

- [ ] T001 운영 SQLite 백업 확보: 운영 호스트에서 `data/maplewind.db` / `data/chatbot.db`
  를 `*.bak.YYYY-MM-DD` 로 복사 후 로컬로 다운로드. 30일 이상 보존 정책 명시.
- [ ] T002 신규 repo 생성: GitHub 조직 `GC-MapleWind` 에 `maplewind-chatbot` (private)
  빈 repo 생성. `archive/chinbabang-submission` 보존 의지 README 한 줄 추가.
- [ ] T003 [P] pgloader 동작 검증: 로컬에서 `docker run --rm dimitri/pgloader:latest --version`
  실행. 백업한 SQLite 사본으로 1차 dry-run 수행하여 변환 가능 여부 확인.
- [ ] T004 [P] PostgreSQL 17 이미지 결정: `postgres:17-alpine` 으로 고정. 추가 확장
  (`pgvector` 등) 불필요 확인.

**Checkpoint**: 백업 / 신규 repo / pgloader 모두 준비 완료. Phase 2 부터 본격적 코드
작업 시작 가능.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 메인 repo 의 PostgreSQL 인프라 — 모든 후속 작업의 토대. US1, US2, US3
모두 이 단계가 끝나야 시작 가능.

**⚠️ CRITICAL**: 이 phase 가 끝나야 어떤 user story 도 진행할 수 없다.

- [ ] T005 [P] [pyproject.toml](../../pyproject.toml) 의존성 갱신:
  - `uv add asyncpg "psycopg[binary]" alembic`
  - `uv remove aiosqlite`
- [ ] T006 [P] [docker-compose.yml](../../docker-compose.yml) 에 `postgres` 서비스 추가:
  `postgres:17-alpine`, named volume `./data/pg`, `postgres-init.sql` 마운트, healthcheck
  (`pg_isready`).
- [ ] T007 [scripts/postgres-init.sql](../../scripts/postgres-init.sql) 생성:
  `CREATE DATABASE maplewind;` + `CREATE DATABASE chatbot;` (postgres 컨테이너 첫 기동 시
  자동 실행).
- [ ] T008 [.env.example](../../.env.example) 갱신: `POSTGRES_USER`, `POSTGRES_PASSWORD`,
  `DATABASE_URL=postgresql+asyncpg://...`, `CHATBOT_DATABASE_URL=postgresql+asyncpg://...`
  추가. SQLite 관련 항목 제거.
- [ ] T009 [src/database.py](../../src/database.py) 정리:
  - `DATABASE_URL` 기본값 제거 (fail-fast)
  - SQLite-only `event.listens_for("connect")` PRAGMA 가드는 dialect 검사로 보존하거나
    함수 자체 제거.
- [ ] T010 [src/database_chatbot.py](../../src/database_chatbot.py) 정리:
  - `CHATBOT_DATABASE_URL` env var 강제. SQLite 경로 하드코딩 제거.
  - PRAGMA `event.listens_for` 가 dialect=sqlite 일 때만 동작하도록 가드 추가 (Phase 3
    에서 신규 repo 로 옮길 때까지 임시 보호).
- [ ] T011 [src/models/chatbot.py](../../src/models/chatbot.py) JSON 호환성:
  `JSON().with_variant(JSONB, "postgresql")` 적용 + `server_default=text("'{}'::jsonb")`
  로 dialect-aware 기본값 설정.
- [ ] T012 [src/main.py](../../src/main.py) 의 `migrate_user_student_id_to_username`
  검토: SQLite PRAGMA 사용 부분이 dialect 가드 (`if engine.dialect.name == "sqlite"`)
  로 이미 보호되는지 재확인. 운영에서 한 번 더 실행 후 함수 자체 제거 가능.
- [ ] T013 Alembic 도입 — 메인 repo:
  - `uv run alembic init src/alembic`
  - `src/alembic/env.py` 에서 `target_metadata = Base.metadata` 설정 (챗봇 metadata 는
    Phase 4 에서 신규 repo 로 빠지므로 메인 repo 에서는 메인만)
  - 첫 revision: `uv run alembic revision --autogenerate -m "initial schema"` 후
    SQLite 백업과 동일한 DDL 인지 수동 검토.
- [ ] T014 [scripts/migrate_sqlite_to_postgres.sh](../../scripts/migrate_sqlite_to_postgres.sh)
  생성: pgloader Docker 호출 + 환경변수로 SQLite 경로 / Postgres URL 지정 + row count
  비교 로직 (`sqlite3` 와 `psql` 출력 비교).
- [ ] T015 로컬 검증: `docker compose up postgres backend` → `alembic upgrade head` →
  `migrate_sqlite_to_postgres.sh` 1회 실행 → row count 매치 확인.

**Checkpoint**: 메인 backend 가 PostgreSQL 위에서 기동 가능하고, 운영 백업 데이터를
무손실 이전할 수 있는 도구가 검증됨. 이후 user story 시작 가능.

---

## Phase 3: User Story 1 - 마이그레이션 후 메생결산 제출 무중단 (Priority: P1) 🎯 MVP

**Goal**: 마이그레이션 전후 데이터가 한 건도 손실되지 않으며, 챗봇 메생결산 제출이
PostgreSQL 환경에서 정상 동작한다.

**Independent Test**: 운영 SQLite 백업으로 pgloader 이전 → row count 매치 → 메생결산
시뮬레이션 1회 통과 → 구글 시트 기록 확인.

### Implementation for User Story 1

- [ ] T016 [US1] 챗봇 SQLAlchemy 모델 PostgreSQL 호환 검증:
  [src/models/chatbot.py](../../src/models/chatbot.py) 의 `EventInfo`, `InfoList`,
  `TemporaryImage` 가 PG 에서 alembic-autogenerate 로 정확한 DDL 을 만드는지 확인.
  `func.now()` / `DateTime` 사용 부분이 PG 에서 동작하는지 점검.
- [ ] T017 [US1] [src/repositories/chatbot_repo.py](../../src/repositories/chatbot_repo.py)
  의 `case()` 표현식이 PG 에서도 동일하게 동작하는지 회귀 테스트 (`uv run python -m
  unittest tests.test_event_date_gating -v`).
- [ ] T018 [US1] [scripts/simulate_maesaeng_flow.py](../../scripts/simulate_maesaeng_flow.py)
  를 PostgreSQL 환경에서 실행하도록 수정:
  - `os.environ["DATABASE_URL"]`, `os.environ["CHATBOT_DATABASE_URL"]` 으로 PG 강제
  - 최종 제출 1건이 Google Sheets mock 으로 정확히 한 번 전달되는지 검증
  - DB 에 남는 임시 세션/사진 row count 는 시뮬 종료 후 초기값으로 돌아오는지 검증
- [ ] T019 [US1] pgloader 마이그 스크립트 운영 dry-run:
  `scripts/migrate_sqlite_to_postgres.sh` 를 운영 백업 사본으로 실행 후 핵심 테이블
  (`users`, `characters`, `settlements`, `event_info`, `info_list`, `temporary_image`)
  의 샘플 행을 SQLite ↔ PG 비교.
- [ ] T020 [US1] 컷오버 절차 문서화: `specs/001-split-chatbot-postgres/cutover-runbook.md`
  (선택) 또는 plan.md 의 Phase 3 섹션을 운영 runbook 형태로 정리. 롤백 명령 포함.

**Checkpoint**: 메인 + 챗봇이 같은 repo / 같은 컨테이너인 채로 PostgreSQL 위에서
기동되고 메생결산이 동작한다. 분리 작업이 늦어져도 P1 가치는 이 시점에 달성된다.

---

## Phase 4: User Story 2 - 챗봇 독립 배포로 메인 backend 격리 (Priority: P2)

**Goal**: 챗봇 코드가 신규 repo `GC-MapleWind/maplewind-chatbot` 으로 분리되어 독립
이미지 빌드 / 배포가 가능하다.

**Independent Test**: 신규 repo 의 GitHub Actions 가 GHCR 이미지를 빌드 → 운영 통합
docker-compose 가 두 이미지를 pull 하여 함께 기동 → 메인 backend 재시작 없이 챗봇만
이미지 교체 가능.

### Implementation for User Story 2

- [ ] T021 [US2] `git filter-repo` 로 챗봇 파일 추출:
  ```bash
  git clone https://github.com/GC-MapleWind/msgs_13_b chatbot-extract
  cd chatbot-extract
  git filter-repo \
    --path src/services/chatbot_service.py \
    --path src/services/google_sheet_service.py \
    --path src/repositories/chatbot_repo.py \
    --path src/models/chatbot.py \
    --path src/schemas/chatbot_dto.py \
    --path src/controller/v1/chatbot.py \
    --path src/database_chatbot.py \
    --path tests/test_event_date_gating.py \
    --path scripts/simulate_maesaeng_flow.py
  ```
  추출 결과를 `chatbot-extract/` 에 보관.
- [ ] T022 [P] [US2] 신규 repo 디렉토리 재배치 (chatbot-extract 내부):
  - `src/database_chatbot.py` → `src/database.py` 로 rename
  - import 경로 일괄 갱신 (`src.database_chatbot` → `src.database`)
  - 디렉토리 구조를 plan.md 의 신규 repo 트리에 맞춤
- [ ] T023 [P] [US2] 신규 repo `chatbot-repo/pyproject.toml` 작성:
  fastapi, uvicorn[standard], sqlalchemy>=2.0.46, asyncpg, alembic, httpx,
  google-api-python-client, gspread, sqladmin, itsdangerous, python-dotenv, greenlet.
- [ ] T024 [P] [US2] 신규 repo `chatbot-repo/src/main.py` 작성: FastAPI 앱, lifespan
  에서 `alembic upgrade head` 실행, chatbot router 등록, sqladmin setup. 메인 repo
  의 `main.py` 를 참조하여 동일 패턴 유지.
- [ ] T025 [P] [US2] 신규 repo `chatbot-repo/src/admin.py` 작성: `EventInfoAdmin`,
  `InfoListAdmin`, `TemporaryImageAdmin` 등록 (메인 repo 의 `admin.py` 에서 추출).
- [ ] T026 [US2] 신규 repo Alembic 도입:
  - `chatbot-repo/src/alembic/` 초기화
  - `target_metadata = ChatbotBase.metadata`
  - 첫 revision 으로 `event_info`, `info_list`, `temporary_image` 테이블 DDL 생성.
- [ ] T027 [P] [US2] 신규 repo `chatbot-repo/Dockerfile` + `docker-compose.dev.yml`
  작성: 메인 repo Dockerfile 패턴 재사용 + postgres 서비스 포함 (개발용).
- [ ] T028 [P] [US2] 신규 repo `chatbot-repo/.env.example`: `CHATBOT_DATABASE_URL`,
  `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_SHEET_ID`, `KAKAO_*` 등 챗봇이 필요한 모든 환경변수.
- [ ] T029 [P] [US2] 신규 repo `chatbot-repo/.github/workflows/ci.yml`: ruff lint +
  unittest (또는 pytest) + Postgres service container 로 통합 테스트.
- [ ] T030 [P] [US2] 신규 repo `chatbot-repo/.github/workflows/deploy.yml`: `main`
  push 시 GHCR 이미지 빌드 (`ghcr.io/gc-maplewind/maplewind-chatbot:<sha>`,
  `:latest`) + 운영 SSH 배포.
- [ ] T031 [US2] 신규 repo 첫 push: `git push -u origin main` + `archive/chinbabang-submission`
  브랜치 동시 push (FR-014).
- [ ] T032 [US2] 메인 repo 청소 — 챗봇 파일 삭제 PR:
  - 삭제: T021 의 `--path` 인자 9개 파일 모두
  - [src/main.py](../../src/main.py): chatbot router import, `init_chatbot_db()` 호출,
    `app.include_router(chatbot_router, ...)` 제거
  - [src/admin.py](../../src/admin.py): chatbot ModelView 3개 + import + add_view 호출
    제거. `chatbot_async_session` import 제거
  - [pyproject.toml](../../pyproject.toml): `gspread`, `google-api-python-client` 제거
    + `uv lock`
  - [docker-compose.yml](../../docker-compose.yml): `google-credentials.json` 마운트 제거
  - [scripts/](../../scripts/) 의 `simulate_maesaeng_flow.py` 는 신규 repo로 이동했으므로 삭제
- [ ] T033 [US2] 메인 repo `tests/` 정리: `test_event_date_gating.py` 삭제 (신규 repo
  로 이동 완료).

**Checkpoint**: US1 + US2 양쪽 가치 달성. 두 repo 가 독립적으로 진화 가능. 메인 repo
의 의존성 그래프에서 `gspread` / `google-api-python-client` / `aiosqlite` 가 사라짐
(SC-006).

---

## Phase 5: User Story 3 - 챗봇 SLA 격리 (Priority: P3)

**Goal**: 메인 backend 의 부하가 챗봇 응답 시간에 영향을 주지 않는다.

**Independent Test**: 메인 backend 에 인위적 부하 + 챗봇 발화 10회 → 응답 시간 4초 이내.

### Implementation for User Story 3

- [ ] T034 [US3] 운영 통합 docker-compose 설계: 두 GHCR 이미지를 pull 하는 단일
  `docker-compose.prod.yml` 작성. 두 컨테이너가 동일 PostgreSQL 인스턴스를 공유하되
  각자 별도 DB URL 을 환경변수로 받음.
  - 위치: `gc-maplewind/deployment` 별도 repo 또는 메인 repo `deploy/` 폴더 (의사결정
    필요).
- [ ] T035 [US3] reverse proxy / DNS 설정: 카카오 webhook URL 변경 + 7일 호환성 라우팅
  (FR-009).
  - `https://api.maplewind.com/chatbot/chat` → 임시 라우팅으로 챗봇 컨테이너로 forward
  - `https://chatbot.maplewind.com/chatbot/chat` → 챗봇 컨테이너 직접 라우팅
- [ ] T036 [US3] SLA 검증 시나리오 실행: 메인 backend 에 부하 (예: 전체 캐릭터 새로고침
  어드민 작업) 가하면서 카카오 챗봇 발화 10회 응답 시간 측정. p95 < 3s, p99 < 4s 확인
  (SC-003).
- [ ] T037 [US3] 챗봇 단독 크래시 시나리오 검증: 챗봇 컨테이너를 강제 종료
  (`docker stop`) 한 상태에서 메인 backend `/health`, `/v1/characters` 정상 응답 확인.

**Checkpoint**: 모든 user story 완료. SLA 격리 가치 입증.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 운영 컷오버 + 문서/설정 정리.

- [ ] T038 운영 컷오버 (예상 30분 다운타임):
  1. 운영 SQLite 두 파일 백업 (`maplewind.db.bak.<date>`, `chatbot.db.bak.<date>`)
  2. `docker compose down backend` (구버전 SQLite)
  3. PostgreSQL 컨테이너 기동 + `postgres-init.sql` 자동 실행으로 두 DB 생성
  4. `pgloader` 로 두 SQLite → 두 PG DB 이전 (T019 기반)
  5. 메인 backend 신규 이미지 + 챗봇 신규 이미지 기동
  6. 카카오 오픈빌더에서 webhook URL 갱신
  7. 메생결산 1회 발화 → 구글 시트 기록 확인
- [ ] T039 [P] 운영 검증 24시간 모니터링: SC-003 (챗봇 응답 p95/p99), SC-004 (메인
  5xx 비율) 측정. 임계 초과 시 롤백 검토.
- [ ] T040 [P] 메인 repo `README.md` 갱신: 챗봇 섹션 → 신규 repo 링크로 변경. 운영
  통합 docker-compose 사용법 추가.
- [ ] T041 [P] 신규 repo `chatbot-repo/README.md` 작성: 운영 가이드, 환경변수, 카카오
  webhook 설정법, 시뮬레이션 스크립트 사용법.
- [ ] T042 메인 repo 의 `migrate_user_student_id_to_username` 함수 제거 (T012 후속):
  운영에서 1회 더 실행되어 정상 동작 확인되면 함수 자체 삭제.
- [ ] T043 SQLite 백업 보관 정책 적용: 컷오버 30일 후 백업 폐기 또는 cold storage 이전.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음. 즉시 시작.
- **Foundational (Phase 2)**: Setup 완료 후. **모든 user story 를 BLOCK 한다.**
- **User Story 1 (Phase 3)**: Foundational 완료 후. MVP 기준선.
- **User Story 2 (Phase 4)**: Foundational 완료 후 시작 가능. US1 과 병렬 진행 가능
  (코드 영역이 거의 겹치지 않음).
- **User Story 3 (Phase 5)**: US2 완료 후 (분리 배포가 선결). US1 과는 무관.
- **Polish (Phase 6)**: 모든 user story 완료 후. 운영 컷오버는 Phase 6 의 첫 단계.

### User Story Dependencies

- **US1 (P1)**: Foundational 만 의존. 단독으로도 마이그레이션 가치 100% 달성.
- **US2 (P2)**: Foundational 만 의존. US1 과 병렬 가능 (의존성 충돌 없음, 단 컷오버는
  한 번에).
- **US3 (P3)**: US2 의 분리 배포가 선결. SLA 격리는 분리된 컨테이너가 있어야 측정 가능.

### Within Each User Story

- 데이터 모델 호환성 검증 (T016) → repository / service 회귀 테스트 (T017) → 시뮬
  스크립트 검증 (T018) → 운영 dry-run (T019) → 컷오버 runbook (T020).
- 신규 repo 작업 (T022~T030) 은 파일별 [P] 가능. T031 (push) 은 모든 [P] 작업 완료 후.
- 메인 repo 청소 (T032, T033) 는 신규 repo push (T031) 후. 청소 PR 머지 시점이 단방향.

### Parallel Opportunities

- T003, T004 (Setup [P])
- T005, T006 (Foundational [P]: pyproject 와 docker-compose 는 다른 파일)
- T022~T030 의 [P] 표시된 작업들 (신규 repo 디렉토리 재배치 / pyproject / Dockerfile /
  CI / deploy / README — 서로 다른 파일)
- T039, T040, T041 (Polish [P])
- US1 (Phase 3) 과 US2 (Phase 4) 는 병렬 진행 가능 (다른 repo 다른 파일)

---

## Parallel Example: Phase 4 의 신규 repo 골격 작성

```bash
# T022 ~ T030 중 [P] 표시된 작업들을 동시 진행 가능
Task: "신규 repo 디렉토리 재배치 + import 경로 갱신 (T022)"
Task: "신규 repo pyproject.toml 작성 (T023)"
Task: "신규 repo src/main.py 작성 (T024)"
Task: "신규 repo src/admin.py 작성 (T025)"
Task: "신규 repo Dockerfile + docker-compose.dev.yml (T027)"
Task: "신규 repo .env.example (T028)"
Task: "신규 repo .github/workflows/ci.yml (T029)"
Task: "신규 repo .github/workflows/deploy.yml (T030)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup 완료
2. Phase 2: Foundational 완료 (Postgres + Alembic + 마이그 스크립트)
3. Phase 3: User Story 1 완료 — MVP. **여기서 멈춰도 인프라 마이그는 성공.**
4. Phase 6 의 컷오버 (T038) 만 수행하면 운영 가치 100% 달성.
5. Phase 4 / Phase 5 는 추후 sprint 로 미뤄도 됨.

### Incremental Delivery

1. Setup + Foundational → 마이그 도구 준비 완료
2. + User Story 1 → 데이터 무손실 마이그 가능 (MVP, 컷오버 옵션)
3. + User Story 2 → 분리 배포 가치 추가
4. + User Story 3 → SLA 격리 가치 추가
5. Polish → 컷오버 + 문서화

각 단계에서 멈춰도 이전 단계의 가치는 유지된다.

### Parallel Team Strategy

분리 가능한 두 트랙:

- **Track A**: 메인 repo Postgres 마이그 (Phase 2 + Phase 3 = US1)
- **Track B**: 챗봇 신규 repo 골격 + 추출 (Phase 4 = US2)

두 트랙은 코드 영역이 거의 겹치지 않으므로 병렬 진행 가능. 단 운영 컷오버 (Phase 6
T038) 는 두 트랙이 모두 끝난 시점에 한 번에 진행한다.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- 본 작업은 인프라 마이그가 핵심이라 일반적인 user-facing 기능 개발과 task 형태가 다름.
  user story 는 "운영 가치" 단위로 grouping 됨.
- 컷오버 (T038) 는 단일 task 처럼 보이지만 실제로는 7단계 절차. 실행 직전 plan.md 를
  runbook 으로 변환해서 별도 문서화 권장.
- 모든 phase 에 헌법(`/.specify/memory/constitution.md`) 의 게이트 (3-Layer, async-first,
  type-safe, minimum-surprise) 가 적용된다. 위반 발견 시 즉시 정지하고 plan.md 의
  Complexity Tracking 표에 사유 등록 후 진행.
- pgloader 단계 (T019, T038) 는 비가역적이므로 반드시 백업 사본으로 dry-run 통과 후 운영
  실행.
