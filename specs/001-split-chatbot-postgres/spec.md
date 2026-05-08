# Feature Specification: Split Chatbot Service & PostgreSQL Migration

**Feature Branch**: `001-split-chatbot-postgres`
**Created**: 2026-05-09
**Status**: Draft
**Input**: User description: "챗봇을 별도 git repo `GC-MapleWind/maplewind-chatbot` 으로
완전 분리하면서 메인 backend 와 챗봇 모두 SQLite → PostgreSQL(단일 인스턴스, DB 2개)
로 마이그레이션. 운영 데이터는 양쪽 모두 보존."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 마이그레이션 후 메생결산 제출 무중단 (Priority: P1)

13기 운영진과 길드원은 인프라가 SQLite → PostgreSQL 로 전환되어도 카카오톡 챗봇에서
"메생결산" 제출 흐름이 동일하게 동작해야 한다. 마이그레이션 이전에 이미 제출되었던
이력 / 캐릭터 / 결산 데이터가 한 건도 누락되지 않아야 하며, 컷오버 직후 첫 제출이
구글 시트에 정상 기록되어야 한다.

**Why this priority**: 이 스토리는 마이그레이션의 존재 이유 그 자체다. 데이터 손실이
한 건이라도 발생하면 인프라 변경 자체가 실패한 것으로 간주된다. P2/P3 가 부재해도
이 스토리만 충족되면 사용자 입장에서 인프라 변경의 부정적 영향이 없다.

**Independent Test**: 운영 SQLite 백업을 받아 로컬에서 pgloader 로 PostgreSQL 에 이전한
후, 마이그레이션 전후의 row count 와 핵심 테이블 (`users`, `characters`, `settlements`,
`event_info`, `info_list`, `temporary_image`) 의 샘플 행을 비교한다. 그 다음
`scripts/simulate_maesaeng_flow.py` 를 PostgreSQL 환경에서 실행하여 메생결산 1회 제출이
구글 시트에 기록되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 운영 SQLite 의 `maplewind.db` 와 `chatbot.db` 가 백업되어 있고, **When**
   pgloader 로 두 DB 를 단일 PostgreSQL 인스턴스의 `maplewind` / `chatbot` DB 로 이전한 뒤
   ,**Then** 두 DB 모든 테이블의 row count 가 SQLite 백업 시점과 일치한다.
2. **Given** 마이그레이션 후 새 인프라가 기동된 상태에서, **When** 길드원이 카카오톡에서
   "메생결산" → 캐릭터 선택 → 사진 첨부 → 제출까지 진행하면, **Then** 구글 시트에 해당
   제출 행이 한 번에 추가되고 카카오톡에 응답 카드가 5초 이내에 전달된다.
3. **Given** PostgreSQL 인스턴스가 정상 기동되어 있고, **When** 메인 backend 가
   `alembic upgrade head` 후 기동되면, **Then** 새 마이그레이션이 추가로 발생하지 않고
   기존 데이터에 대한 기본 조회 API (`GET /v1/characters`, `GET /v1/settlements`) 가
   200 응답을 반환한다.

---

### User Story 2 - 챗봇 독립 배포로 메인 backend 격리 (Priority: P2)

운영진은 챗봇 코드 변경 시 메인 backend 를 재배포하지 않고도 챗봇만 단독 배포할 수
있어야 한다. 마찬가지로 메인 backend 배포가 챗봇 서비스에 영향을 주지 않아야 한다.
이를 위해 챗봇은 `GC-MapleWind/maplewind-chatbot` 에 분리된 repo 로 존재하며, 자체
Dockerfile / CI / 배포 파이프라인을 갖는다.

**Why this priority**: 분리 배포는 운영 안정성의 직접적인 향상이지만 사용자가 인지하는
가치는 P1 보다 작다. P1 만으로도 마이그레이션은 "성공" 이며, P2 는 그 가치를 강화한다.

**Independent Test**: 챗봇 신규 repo 의 GitHub Actions 가 `main` 브랜치 푸시 시
`ghcr.io/gc-maplewind/maplewind-chatbot:<sha>` 이미지를 빌드한다. 운영 서버에서 해당
이미지만 pull / 재기동했을 때 메인 backend 컨테이너는 재시작되지 않고 챗봇 `/health`
가 200 을 반환한다.

**Acceptance Scenarios**:

1. **Given** 두 repo 가 각각 GHCR 에 이미지를 푸시하고, **When** 운영 통합 docker-compose
   가 두 이미지로 컨테이너를 기동하면, **Then** 두 컨테이너가 동일한 PostgreSQL 인스턴스를
   공유하면서 각자의 DB (`maplewind`, `chatbot`) 만 접근한다.
2. **Given** 챗봇만 코드 변경이 있을 때, **When** 챗봇 repo 의 deploy workflow 가 실행되면
   ,**Then** 메인 backend 컨테이너는 재시작되지 않고 챗봇 컨테이너만 새 이미지로 교체된다.
3. **Given** 메인 backend 의 `pyproject.toml`, **When** 분리 후 의존성을 검사하면,
   **Then** `gspread`, `google-api-python-client`, `aiosqlite` 가 더 이상 포함되지 않는다.

---

### User Story 3 - 챗봇 SLA 격리 (Priority: P3)

길드원은 카카오 챗봇의 모든 응답을 5초 이내에 받아야 한다 (카카오 오픈빌더 콜백 SLA).
챗봇이 별도 프로세스로 분리되면 메인 backend 의 무거운 작업 (대량 결산 집계, 어드민
일괄 작업) 이 챗봇 응답 지연을 유발하지 않는다.

**Why this priority**: 현재도 `useCallback` 구조로 5초 SLA 는 지키고 있으나, 이벤트
시즌의 트래픽 피크 또는 운영진의 어드민 작업이 같은 프로세스에서 일어날 때 잠재적
경쟁이 존재한다. 분리 후에는 이 위험이 구조적으로 제거된다.

**Independent Test**: 운영 환경에서 메인 backend 에 부하를 주는 어드민 일괄 작업
(예: 전체 캐릭터 새로고침) 을 실행하면서 동시에 카카오 챗봇 발화 10회를 수행한다.
각 발화의 응답 시간이 4 초 이내인지 확인한다.

**Acceptance Scenarios**:

1. **Given** 메인 backend 에 인위적인 부하를 가한 상태에서, **When** 카카오 챗봇 핵심
   발화 ("메생결산", "메생결산 제출") 를 10회 호출하면, **Then** 모든 호출이 4초 이내에
   응답한다.
2. **Given** 챗봇 컨테이너 단독 OOM 또는 크래시 시나리오가 발생하면, **When** 메인
   backend 에 동일 시간 동안 트래픽을 보내면, **Then** 메인 backend 는 정상 응답한다.

---

### Edge Cases

- pgloader 가 SQLite 의 비표준 타입 (`JSON`, `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`) 을
  PostgreSQL 로 변환하지 못하는 컬럼이 있을 때 어떻게 처리할 것인가? → 변환 실패 컬럼은
  Alembic 마이그레이션 후 수동 SQL 로 보정한다.
- 메인 backend 와 챗봇이 동시에 같은 PostgreSQL 인스턴스에 접속할 때 connection pool
  포화가 발생하지 않는가? → 두 서비스가 각자 `pool_size` 를 별도 관리하며, 인스턴스의
  `max_connections` 는 100 (기본) 으로 충분하다.
- `git filter-repo` 추출 후 신규 repo 의 commit hash 가 메인 repo 와 달라져 두 repo
  사이에서 cherry-pick 이 불가능하다. → 분리 시점 이후의 변경은 각 repo 에서 독립적으로
  관리하며 hot-fix 가 양쪽 모두 필요한 경우에만 수동 동기화한다.
- 운영 컷오버 중 카카오 webhook 호출이 들어오면? → 컷오버 윈도우는 새벽 이용자가 적은
  시간대를 선택하며, 짧은 다운타임 동안 들어온 호출은 카카오 측 재시도 로직에 의존한다.
- `archive/chinbabang-submission` 브랜치는 이미 메인 repo 에 보존되어 있으며, 분리
  후 신규 repo 에도 동일 이름으로 푸시한다.
- pgloader 1차 시도 후 row count 불일치 시 어떻게 할 것인가? → 컷오버를 중단하고
  롤백 (이전 SQLite 이미지로 backend 재기동) 후 원인 분석.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템 MUST 메인 backend 와 챗봇 서비스가 서로 다른 git 저장소
  (`GC-MapleWind/msgs_13_b`, `GC-MapleWind/maplewind-chatbot`) 와 컨테이너 이미지로
  관리되도록 분리되어야 한다.
- **FR-002**: 시스템 MUST 단일 PostgreSQL 17 인스턴스를 운영하며, `maplewind` /
  `chatbot` 두 데이터베이스를 가진다.
- **FR-003**: 시스템 MUST 운영 SQLite (`maplewind.db`, `chatbot.db`) 의 모든 행을
  PostgreSQL 의 대응 데이터베이스로 손실 없이 이전한다.
- **FR-004**: 메인 backend MUST PostgreSQL 의 `maplewind` 데이터베이스에만 접근하며,
  `chatbot` 데이터베이스에 접근하지 않는다.
- **FR-005**: 챗봇 서비스 MUST PostgreSQL 의 `chatbot` 데이터베이스에만 접근한다.
- **FR-006**: 두 서비스 MUST Alembic 으로 스키마 변경을 관리하며, 각 repo 에 독립적인
  Alembic 환경을 갖는다.
- **FR-007**: 메인 backend MUST `gspread`, `google-api-python-client`, `aiosqlite`
  의존성을 더 이상 포함하지 않는다.
- **FR-008**: 챗봇 신규 repo MUST `fastapi`, `sqlalchemy`, `asyncpg`, `alembic`,
  `httpx`, `gspread`, `google-api-python-client`, `sqladmin` 등 자체 운영에 필요한
  의존성을 모두 자체적으로 선언한다.
- **FR-009**: 챗봇 webhook URL MUST 컷오버 후 카카오 오픈빌더 빌더 측에서 새 엔드포인트
  로 갱신되며 (`https://chatbot.maplewind.com/chatbot/chat` 또는 reverse proxy 라우팅),
  이전 URL 로 들어오는 호출이 있을 경우 최소 7일 동안 동작하도록 임시 라우팅을 둔다.
- **FR-010**: 두 서비스 MUST 각자의 컨테이너에서 `alembic upgrade head` 가 lifespan
  시작 전 또는 entrypoint 에서 실행되어 스키마가 자동 동기화된다.
- **FR-011**: 챗봇 서비스 MUST 카카오 오픈빌더 콜백 SLA 를 만족하기 위해 응답 시간이
  4초를 초과할 가능성이 있는 작업은 백그라운드 태스크 + `useCallback` 패턴으로 처리한다
  (현재 패턴 유지).
- **FR-012**: 컷오버 절차 MUST 롤백 가능해야 한다 — pgloader 실패 또는 검증 실패 시
  이전 SQLite 백엔드 이미지로 재기동하여 운영 복귀가 가능해야 한다.
- **FR-013**: 챗봇 추출 시 MUST `git filter-repo` 로 chatbot 관련 파일들의 git 이력을
  보존하여 신규 repo 로 이전한다.
- **FR-014**: `archive/chinbabang-submission` 브랜치 MUST 메인 repo 와 신규 repo 양쪽에
  보존되어야 한다.
- **FR-015**: 시스템 MUST 분리 후 메인 backend 의 sqladmin 대시보드에 챗봇 관련
  ModelView (`EventInfoAdmin`, `InfoListAdmin`, `TemporaryImageAdmin`) 가 노출되지
  않으며, 챗봇 신규 repo 의 sqladmin 에는 동일 ModelView 가 등록된다.
- **FR-016**: 메인 docker-compose MUST 더 이상 `google-credentials.json` 을 마운트
  하지 않으며, 해당 비밀은 챗봇 컨테이너에만 마운트된다.

### Key Entities *(include if feature involves data)*

- **maplewind DB (Postgres)**: 기존 SQLite `maplewind.db` 의 모든 테이블 — `User`,
  `Character`, `Settlement`, `Comment`, `Event`, 등 메인 backend 도메인 전체.
- **chatbot DB (Postgres)**: 기존 SQLite `chatbot.db` 의 모든 테이블 — `EventInfo`,
  `InfoList`, `TemporaryImage`. 챗봇 도메인의 모든 영속 데이터.
- **운영 SQLite 백업 (`*.bak.YYYY-MM-DD`)**: 컷오버 시점의 불변 스냅샷. pgloader 입력으로
  사용. 컷오버 검증 후 최소 30일 보관.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 마이그레이션 후 양쪽 DB 의 모든 테이블 row count 가 SQLite 백업 시점과
  100% 일치한다.
- **SC-002**: 컷오버 윈도우 (운영 다운타임) 가 30분 이하로 끝난다.
- **SC-003**: 컷오버 후 24시간 동안 카카오 챗봇 발화 응답 시간 p95 가 3초 이하, p99 가
  4초 이하를 유지한다.
- **SC-004**: 컷오버 후 7일 동안 메인 backend 의 핵심 엔드포인트 (`/v1/characters`,
  `/v1/settlements`, `/health`) 5xx 비율이 0.1% 이하를 유지한다.
- **SC-005**: 챗봇 신규 repo 가 자체 CI 에서 lint + test 가 통과하고, deploy
  workflow 가 메인 repo 와 무관하게 GHCR 이미지를 푸시할 수 있다.
- **SC-006**: 메인 repo 의 의존성 그래프에서 `gspread`, `google-api-python-client`,
  `aiosqlite` 가 완전히 제거된다.
- **SC-007**: 챗봇 단독 재배포 (이미지 교체) 가 메인 backend 컨테이너 재시작 없이
  완료되며, 재배포 시간이 60초 이하다.

## Assumptions

- 운영 환경은 docker-compose 기반의 단일 호스트이며, 향후 k8s 이전 계획은 본 작업
  범위에 포함되지 않는다.
- 카카오 오픈빌더 webhook URL 변경 권한이 운영진에 있다.
- pgloader 가 현재 SQLite 스키마를 자동 변환할 수 있다 (실패 시 수동 SQL 로 보정).
- 컷오버 윈도우는 새벽 시간대 30분 다운타임이 허용된다.
- 신규 repo `GC-MapleWind/maplewind-chatbot` 의 생성 권한은 운영진 GitHub 조직에 있다.
- PostgreSQL 17 의 단일 인스턴스로 두 서비스의 트래픽을 충분히 감당할 수 있다 (현재
  트래픽 규모 기준).
- 친바방 (chinbabang) 관련 코드는 이미 `archive/chinbabang-submission` 브랜치에 보존
  완료되었다 (선행 작업으로 수행됨).
- 본 변경은 헌법(`/.specify/memory/constitution.md`) 의 모든 핵심 원칙을 준수한다 —
  3-Layer 아키텍처, async-first, type-safe Python, SDD lifecycle, minimum-surprise.
