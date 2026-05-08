# Implementation Plan: Split Chatbot Service & PostgreSQL Migration

**Branch**: `001-split-chatbot-postgres` | **Date**: 2026-05-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-split-chatbot-postgres/spec.md`

## Summary

메인 backend 와 챗봇을 두 개의 git 저장소 / 컨테이너로 분리하고, 두 서비스 모두
SQLite (aiosqlite) → PostgreSQL 17 (asyncpg) 로 데이터베이스 엔진을 마이그레이션한다.
PostgreSQL 은 단일 인스턴스에 `maplewind` / `chatbot` 두 데이터베이스로 분리되며,
서비스 간 DB 접근은 격리된다. 운영 데이터는 pgloader 로 무손실 이전하며, git 이력은
`git filter-repo` 로 신규 repo 에 보존한다. 두 repo 모두 Alembic 으로 스키마를 관리하고,
GHCR 이미지를 단일 통합 docker-compose 가 pull 하여 컷오버 윈도우 안에서 함께 기동한다.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, sqladmin,
httpx, gspread (챗봇 only), google-api-python-client (챗봇 only)
**Storage**: PostgreSQL 17 단일 인스턴스, DB 2개 (`maplewind`, `chatbot`). 마이그레이션
도구: pgloader (Docker 이미지 `dimitri/pgloader`)
**Testing**: 표준 라이브러리 `unittest` (현행), 신규 챗봇 repo 는 `pytest` 도입 검토.
회귀 검증으로 `scripts/simulate_maesaeng_flow.py` (현재 챗봇 repo로 이동됨)
를 PostgreSQL 환경에서 실행
**Target Platform**: Linux 컨테이너 (docker-compose), 운영은 단일 호스트
**Project Type**: 백엔드 web service (메인) + 분리된 webhook service (챗봇).
구조는 Plan 의 "Project Structure" 섹션 참조
**Performance Goals**: 메인 backend 핵심 GET 엔드포인트 p95 < 500ms (현 수준 유지),
챗봇 카카오 콜백 응답 p95 < 3s, p99 < 4s (카카오 SLA 5s 내 유지)
**Constraints**: 컷오버 윈도우 ≤ 30분 다운타임, 운영 데이터 손실 0건, 카카오 webhook
SLA 5초 절대 위반 금지
**Scale/Scope**: 동시 사용자 < 200, 일 챗봇 발화 수백 건 수준. 데이터 규모는 SQLite
파일 합산 ≤ 200MB. 단일 PG 인스턴스로 충분

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 적용 방식 | 결과 |
|------|----------|------|
| I. Strict 3-Layer Architecture | 챗봇 신규 repo 도 동일하게 controller/v1, services, repositories, models 5-layer 유지. 분리 과정에서 레이어 경계를 깨지 않음. | PASS |
| II. Async-First | aiosqlite → asyncpg 로 교체. 양쪽 모두 async SQLAlchemy 2.0 그대로. 외부 SDK (gspread, googleapiclient) 의 동기 호출은 기존 `asyncio.to_thread` 래핑 유지. | PASS |
| III. Type-Safe Modern Python | 신규 repo 는 동일 컨벤션 (`str \| None`, `Mapped[]`, builtin generics) 으로 시작. 분리 과정에서 추가 타입 위반 없음. | PASS |
| IV. Spec-Driven Change | 본 PR 자체가 SDD 사이클 (spec → plan → tasks → implement) 을 따른다. | PASS |
| V. Minimum-Surprise Code | 마이그레이션 스크립트 / 컷오버 절차에 비자명한 부분 (롤백, secret 분리) 만 주석으로 설명. 자명한 narration 주석 추가 없음. | PASS |

**결과**: 모든 원칙 PASS. Complexity Tracking 표 항목 없음.

추가 헌법 게이트 (Quality Gates 섹션):

- 신규 도메인 추가 없음 — 기존 도메인 분리뿐 → 5-layer 신설 의무 N/A
- 신규 controller 핸들러 추가 없음 — 기존 핸들러 이동 → `response_model` 게이트 N/A
- `Depends(get_db)` 패턴 유지 — 챗봇 repo 의 `get_chatbot_db` 만 `get_db` 로 이름 정리
- 외부 I/O 추가 없음 — pgloader 는 일회성 마이그 도구
- `.env.example` 에 `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`,
  `CHATBOT_DATABASE_URL` 추가 필요 (신규 secret 게이트 PASS 조건)

## Project Structure

### Documentation (this feature)

```text
specs/001-split-chatbot-postgres/
├── plan.md              # This file
├── spec.md              # User stories, FR, success criteria
├── tasks.md             # Phase별 task 분해
└── (research.md / data-model.md / quickstart.md / contracts/ — 본 작업에서는 미사용)
```

### Source Code (current repo: `GC-MapleWind/msgs_13_b`)

분리 후 메인 repo 구조 (챗봇 모듈 제거됨, Alembic 추가됨):

```text
src/
├── controller/v1/                    # 메인 도메인 라우터만 (chatbot.py 제거)
│   ├── characters.py
│   ├── settlements.py
│   └── ...
├── services/                         # google_sheet_service.py, chatbot_service.py 제거
│   └── ... (메인 도메인 서비스만)
├── repositories/                     # chatbot_repo.py 제거
│   └── ...
├── models/                           # chatbot.py 제거
│   └── ...
├── schemas/                          # chatbot_dto.py 제거
│   └── ...
├── alembic/                          # 신규 — 메인 metadata만
│   ├── versions/0001_initial.py
│   └── env.py
├── database.py                       # asyncpg 기반으로 단일화 (aiosqlite 제거)
├── admin.py                          # 챗봇 ModelView 제거
└── main.py                           # chatbot router/init 제거

tests/
├── (test_event_date_gating.py 신규 repo로 이동)
└── ... (메인 도메인 테스트만)

scripts/
├── postgres-init.sql                 # 신규 — CREATE DATABASE maplewind / chatbot
├── migrate_sqlite_to_postgres.sh     # 신규 — pgloader wrapper
└── (simulate_maesaeng_flow.py 신규 repo로 이동)

docker-compose.yml                    # postgres 서비스 추가, google-credentials 마운트 제거
pyproject.toml                        # gspread/googleapiclient/aiosqlite 제거, asyncpg/alembic 추가
```

### Source Code (new repo: `GC-MapleWind/maplewind-chatbot`)

`git filter-repo` 로 추출된 후 디렉토리 재배치 + 신규 인프라 파일 추가:

```text
maplewind-chatbot/
├── src/
│   ├── main.py                       # FastAPI app + lifespan(alembic upgrade head)
│   ├── config.py                     # 환경 변수 로딩
│   ├── database.py                   # 챗봇 Postgres 단일 (구 database_chatbot.py)
│   ├── admin.py                      # EventInfo / InfoList / TemporaryImage ModelView
│   ├── controller/v1/
│   │   └── chatbot.py
│   ├── services/
│   │   ├── chatbot_service.py
│   │   └── google_sheet_service.py
│   ├── repositories/
│   │   └── chatbot_repo.py
│   ├── models/
│   │   └── chatbot.py
│   ├── schemas/
│   │   └── chatbot_dto.py
│   └── alembic/
│       ├── versions/0001_initial.py
│       └── env.py
├── tests/
│   └── test_event_date_gating.py
├── scripts/
│   └── simulate_maesaeng_flow.py
├── Dockerfile
├── docker-compose.dev.yml
├── pyproject.toml                    # fastapi/sqlalchemy/asyncpg/alembic/httpx/gspread/googleapiclient/sqladmin
├── .env.example                      # CHATBOT_DATABASE_URL, GOOGLE_CREDENTIALS_PATH, KAKAO_*
├── README.md
└── .github/workflows/
    ├── ci.yml                        # ruff + unittest/pytest + Postgres service container
    └── deploy.yml                    # GHCR 이미지 빌드 + 운영 SSH 배포
```

### Source Code (운영 통합)

```text
deployment/                           # 별도 repo 또는 메인 repo의 deploy/ 폴더 검토
└── docker-compose.prod.yml           # 단일 postgres + 두 서비스 GHCR 이미지를 pull
```

**Structure Decision**: 메인 backend 와 챗봇은 두 개의 독립 git repo 와 컨테이너 이미지로
관리한다. 두 repo 는 동일한 5-layer 컨벤션을 따르며, 운영 환경은 단일 PostgreSQL 인스턴스
+ 두 서비스 컨테이너 + 통합 docker-compose 구조다. Alembic 환경은 각 repo 가 자체 보유하며
서로 독립적으로 진화한다. `.specify/memory/constitution.md` 의 5 핵심 원칙을 두 repo 모두
계승한다.

## Phase Strategy

본 작업은 다음 4개 phase 로 진행된다 — 자세한 task 는 [tasks.md](./tasks.md) 참조.

| Phase | 목적 | 산출물 | 사용자 가치 매핑 |
|-------|------|--------|---------------|
| Phase 0 | 사전 준비 (백업, 신규 repo 생성, pgloader 검증) | SQLite 백업, 빈 신규 repo, pgloader 동작 확인 | 안전망 (FR-012, FR-013) |
| Phase 1 | 메인 repo Postgres 마이그 (챗봇 그대로) | docker-compose postgres 추가, alembic, 의존성 교체, 마이그 스크립트 | US1 일부 (메인 데이터 보존) |
| Phase 2 | 챗봇 추출 + 신규 repo (Phase 1과 병렬 가능) | filter-repo, 신규 repo 골격, CI/CD, 메인 repo 청소 | US2, US3 (분리 배포 + SLA 격리) |
| Phase 3 | 운영 컷오버 | pgloader 로 양쪽 DB 이전, 두 서비스 동시 기동, webhook URL 갱신 | US1 완성 (양쪽 데이터 무손실 + 챗봇 정상 동작) |
| Phase 4 | 정리 | README, deploy 문서, 미사용 secret/마운트 제거 | DX |

## Risks & Decisions

| 리스크 | 의사결정 / 완화책 |
|--------|-----------------|
| pgloader 가 SQLite `JSON` 컬럼을 변환하지 못함 | Alembic 1차 마이그 후 수동 SQL 로 `JSON` → `JSONB` 변환. 또는 SQLAlchemy 모델에서 `JSON().with_variant(JSONB, "postgresql")` 적용 |
| Alembic metadata 분리 vs 통합 | **분리** — 메인 repo 는 메인 metadata 만, 챗봇 repo 는 챗봇 metadata 만. 각자 진화 |
| 운영 컷오버 중 webhook 손실 | 새벽 시간대 컷오버 + 카카오 측 재시도 신뢰 + 사후 재제출 안내 (필요 시) |
| `git filter-repo` 후 commit hash 변경으로 cherry-pick 불가 | 분리 시점 이후 변경은 두 repo 가 독립 진화. hot-fix 동기화 필요 시 수동 patch |
| google-credentials secret 누수 | 챗봇 컨테이너에만 read-only 마운트, 메인 repo / 메인 컨테이너에서 완전 제거 (FR-016) |
| 단일 PG 인스턴스의 connection pool 포화 | 두 서비스가 각자 `pool_size=10` 으로 시작, `max_connections=100` 기본값으로 충분. 모니터링 후 필요 시 PG 측 튜닝 |
| 카카오 webhook URL 변경 누락 | reverse proxy 단계에서 7일간 양쪽 URL 모두 라우팅 (FR-009) |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

본 작업은 헌법의 모든 핵심 원칙을 준수하며 위반 사항이 없으므로 Complexity Tracking
표는 비워둔다.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (해당 없음) | — | — |
