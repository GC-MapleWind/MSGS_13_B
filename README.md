# 🍁 단풍바람 (MapleWind) Backend API

메이플스토리 캐릭터의 한 해 결산 및 업적을 추적하는 서비스의 백엔드 API입니다.

> **"메생결산"** - 메이플스토리 인생 결산 서비스

사용자는 캐릭터별로 달성한 업적, 기억하고 싶은 순간들을 기록하고 공유할 수 있으며, 커뮤니티 댓글 기능을 통해 다른 유저들과 소통할 수 있습니다.

---

## 📚 목차

- [기능](#-기능)
- [기술 스택](#-기술 스택)
- [빠른 시작](#-빠른 시작)
- [아키텍처](#-아키텍처)
- [프로젝트 구조](#-프로젝트-구조)
- [API 엔드포인트](#-api-엔드포인트)
- [개발 문서](#-개발-문서)
- [개발 워크플로우](#-개발-워크플로우)

---

## ✨ 기능

- **캐릭터 관리**: 메이플스토리 캐릭터 정보 조회
- **결산 추적**: 캐릭터별 업적 및 기록 관리
- **커뮤니티 댓글**: 방명록 형태의 댓글 시스템
- **사용자 시스템**: 로컬 회원가입/로그인 및 카카오 소셜 로그인 (JWT + Refresh Token)
- **시스템 소식**: 운영팀 메시지 및 공지사항
- **자동 시드 데이터**: 첫 실행 시 테스트 데이터 자동 생성
- **API 문서 자동 생성**: Swagger UI & ReDoc 지원

---

## 🛠 기술 스택

| 항목 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | FastAPI | 0.128+ |
| 언어 | Python | 3.12+ |
| 데이터베이스 | SQLite | (aiosqlite) |
| ORM | SQLAlchemy | 2.0+ (Async) |
| 인증 | JWT, OAuth2 | (python-jose) |
| 패키지 매니저 | uv | - |
| 아키텍처 패턴 | 3-Layer Architecture | - |
| API 서버 | Uvicorn | 0.40+ |

---

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- 카카오 개발자 센터 앱 키 (소셜 로그인 사용 시)

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone <repository-url>
cd dpbr_13_B

# 2. 환경 변수 설정 (.env)
cp .env.example .env
# .env 파일에 JWT_SECRET_KEY, KAKAO_CLIENT_ID 등을 설정하세요.

# 3. 의존성 설치
uv sync

# 4. 개발 서버 실행
uv run uvicorn main:app --reload
```

### 접속 정보

서버가 실행되면 다음 주소에서 확인할 수 있습니다:

| 서비스 | URL |
|--------|-----|
| **API 엔드포인트** | http://127.0.0.1:8000/api/v1 |
| **Swagger UI** | http://127.0.0.1:8000/docs |
| **ReDoc** | http://127.0.0.1:8000/redoc |

### 초기 데이터

첫 실행 시 다음 시드 데이터가 자동으로 삽입됩니다:
- 테스트 유저 (`test` / `password123`)
- 캐릭터 3건 (강민아, 하늘빛, 바람의검)
- 결산 4건
- 댓글 3건

## 🏗 아키텍처

### 3-Layer Architecture

프로젝트는 명확한 책임 분리를 위해 3계층 아키텍처를 사용합니다:

```
┌─────────────────────────────────────────────────┐
│  Controller (Router)                            │  ← HTTP 요청/응답 처리
│  - 라우팅 정의                                   │
│  - 요청 검증 (Pydantic)                         │
│  - response_model 지정                          │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│  Service                                        │  ← 비즈니스 로직
│  - 도메인 로직 처리                              │
│  - 유효성 검증                                   │
│  - 예외 처리 (HTTPException)                    │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│  Repository                                     │  ← 데이터 접근
│  - DB 쿼리 실행 (SQLAlchemy)                    │
│  - CRUD 작업                                    │
│  - ORM 모델 반환                                 │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│  Model (Database)                               │  ← 데이터 정의
│  - 테이블 스키마 정의                            │
│  - 관계 매핑                                     │
└─────────────────────────────────────────────────┘
```

### 데이터 흐름

**조회 (GET) 요청**
```
HTTP Request → Controller → Service → Repository → Database
                    ↓            ↓         ↓
HTTP Response ← Pydantic ← ORM Model ← Query Result
```

**생성 (POST) 요청**
```
HTTP Request (JSON) → Pydantic Validation → Service → Repository → Database
                                                ↓           ↓
HTTP Response ← Pydantic Serialization ← ORM Model ← db.commit()
```

## 📂 프로젝트 구조

```
dpbr_13_B/
│
├── main.py                         # 🚀 앱 진입점 (FastAPI 인스턴스, CORS, 라우터 등록)
├── database.py                     # 💾 DB 설정 (엔진, 세션, Base 클래스)
├── pyproject.toml                  # 📦 의존성 정의 (uv)
├── uv.lock                         # 🔒 의존성 잠금 파일
│
├── models/                         # 🗃️ SQLAlchemy ORM 모델 (테이블 정의)
│   ├── __init__.py                 #    - 모델 클래스 export
│   ├── character.py                #    - characters 테이블
│   ├── settlement.py               #    - settlements 테이블
│   ├── comment.py                  #    - comments 테이블
│   └── user.py                     #    - users 테이블
│
├── schemas/                        # 📋 Pydantic DTO (Request/Response)
│   ├── __init__.py
│   ├── character_dto.py            #    - CharacterResponse
│   ├── settlement_dto.py           #    - SettlementResponse
│   ├── comment_dto.py              #    - CommentCreate, CommentResponse
│   └── user_dto.py                 #    - UserCreate, Token, KakaoLoginResponse
│
├── repositories/                   # 🔍 데이터 접근 계층 (DB 쿼리)
│   ├── __init__.py
│   ├── character_repo.py           #    - get_all(), get_by_id()
│   ├── settlement_repo.py          #    - get_by_id(), get_by_character_id()
│   ├── comment_repo.py             #    - get_all(), create()
│   └── user_repo.py                #    - get_by_username(), create()
│
├── services/                       # ⚙️ 비즈니스 로직 계층
│   ├── __init__.py
│   ├── character_service.py        #    - get_all_characters()
│   ├── settlement_service.py       #    - get_settlement_info()
│   ├── comment_service.py          #    - get_comments()
│   └── user_service.py             #    - signup(), login(), process_kakao_login()
│
├── controller/                     # 🌐 API 라우터 계층
│   ├── __init__.py
│   ├── dependencies.py             #    - get_db() 의존성 주입
│   └── v1/                         #    - API v1 엔드포인트
│       ├── __init__.py
│       ├── characters.py           #       GET /characters
│       ├── settlements.py          #       GET /settlements
│       ├── comments.py             #       GET /comments, POST /comments
│       ├── system.py               #       GET /system/notices
│       └── users.py                #       POST /users/signup, /login, /auth/kakao...
│
└── 📄 문서들
    ├── README.md                   # 📖 프로젝트 소개 (이 문서)
    ├── DEVELOPMENT.md              # 🛠️ 개발 가이드 (새 기능 추가 방법)
    ├── CONVENTIONS.md              # 📏 코딩 컨벤션
    └── plan.md                     # 📝 원본 기획서
```

## 🔌 API 엔드포인트

> 모든 엔드포인트는 `/api/v1` 접두사를 사용합니다.

### 캐릭터 (Characters)

| Method | 경로 | 설명 | Response |
|--------|------|------|----------|
| `GET` | `/characters` | 전체 캐릭터 목록 조회 | `List[CharacterResponse]` |
| `GET` | `/characters/{id}` | 특정 캐릭터 상세 정보 | `CharacterDetailResponse` |
| `GET` | `/characters/{id}/settlements` | 캐릭터의 결산 목록 | `List[SettlementResponse]` |

### 결산 (Settlements)

| Method | 경로 | 설명 | Response |
|--------|------|------|----------|
| `GET` | `/settlements/{id}` | 결산 상세 조회 | `SettlementDetailResponse` |

### 댓글 (Comments)

| Method | 경로 | 설명 | Request | Response |
|--------|------|------|---------|----------|
| `GET` | `/comments?page=1&limit=20` | 댓글 목록 (페이지네이션) | - | `List[CommentResponse]` |
| `POST` | `/comments` | 댓글 작성 (로그인 필요) | `CommentCreate` | `CommentResponse` |

### 사용자 (Users)

| Method | 경로 | 설명 | Response |
|--------|------|------|----------|
| `POST` | `/users/signup` | 회원가입 | `UserResponse` |
| `POST` | `/users/login` | 로그인 (JWT 발급) | `Token` |
| `POST` | `/users/auth/kakao/login` | 카카오 로그인 | `KakaoLoginResponse` |

### 시스템 (System)

| Method | 경로 | 설명 | Response |
|--------|------|------|----------|
| `GET` | `/system/notices` | 소식 및 운영팀 메시지 | `NoticesResponse` |

### 응답 예시

<details>
<summary>GET /characters 응답</summary>

```json
[
  {
    "id": 1,
    "name": "강민아",
    "detail_txt": "담와",
    "level": 265,
    "job": "아크",
    "server": "이브리스",
    "avatar_url": null
  }
]
```
</details>

<details>
<summary>GET /characters/1/settlements 응답</summary>

```json
[
  {
    "id": 1,
    "character_id": 1,
    "title": "검은 마법사 클리어",
    "description": "검은 마법사를 처음으로 클리어했습니다!",
    "img_url": null,
    "acquired_at": "2026-08-29"
  }
]
```
</details>

## 📖 개발 문서

개발을 시작하기 전에 아래 문서들을 참고하세요:

| 문서 | 설명 | 주요 내용 |
|------|------|-----------|
| **[📖 README.md](README.md)** | 프로젝트 소개 | 기능, 기술 스택, 빠른 시작 가이드 |
| **[🛠️ DEVELOPMENT.md](DEVELOPMENT.md)** | 개발 가이드 | 환경 설정, 새 기능 추가 방법, 데이터 흐름 |
| **[📏 CONVENTIONS.md](CONVENTIONS.md)** | 코딩 컨벤션 | 아키텍처 규칙, 네이밍 규칙, 코드 스타일 |
| **[📝 plan.md](plan.md)** | 원본 기획서 | 백엔드 상세 기획, ERD, API 명세 |

### 📚 읽는 순서 추천

1. **처음 시작하는 경우**: `README.md` (이 문서) → `DEVELOPMENT.md` → `CONVENTIONS.md`
2. **새 기능을 추가하는 경우**: `CONVENTIONS.md` → `DEVELOPMENT.md` (5. 새 도메인 추가 가이드)
3. **프로젝트 기획을 이해하려면**: `plan.md`

---

## 💻 개발 워크플로우

### 의존성 관리

```bash
# 새 패키지 추가
uv add <패키지명>

# 개발 전용 패키지 추가
uv add --dev <패키지명>

# 의존성 동기화 (uv.lock 기반)
uv sync
```

### DB 초기화

DB를 초기화하려면 `maplewind.db` 파일을 삭제하고 서버를 재시작하세요.

```bash
# Windows (PowerShell)
Remove-Item maplewind.db
uv run uvicorn main:app --reload

# Linux/Mac
rm maplewind.db
uv run uvicorn main:app --reload
```

### 새 기능 추가하기

새로운 도메인(예: `Notification`)을 추가하는 전체 과정은 [DEVELOPMENT.md](DEVELOPMENT.md#5-새-도메인기능-추가-가이드)를 참고하세요.

**간단 요약:**
1. `models/notification.py` - 테이블 정의
2. `schemas/notification_dto.py` - Request/Response DTO
3. `repositories/notification_repo.py` - DB 쿼리
4. `services/notification_service.py` - 비즈니스 로직
5. `controller/v1/notifications.py` - API 라우터
6. `main.py` - 라우터 등록

### 코드 스타일 체크

```bash
# 린터 실행 (추후 추가 예정)
# ruff check .

# 포맷터 실행 (추후 추가 예정)
# ruff format .
```

---

## 🤝 기여 가이드

1. 새 브랜치를 생성합니다: `git checkout -b feature/new-feature`
2. 변경사항을 커밋합니다: `git commit -m "Add new feature"`
3. 브랜치에 푸시합니다: `git push origin feature/new-feature`
4. Pull Request를 생성합니다

**주의사항:**
- [CONVENTIONS.md](CONVENTIONS.md)의 코딩 컨벤션을 준수해주세요
- 3-Layer Architecture 패턴을 따라주세요
- 모든 함수에 타입 어노테이션을 추가해주세요

---

## 🚧 향후 개발 계획

### 미구현 기능

- [ ] **테스트**: pytest 기반 테스트 코드
- [ ] **로깅**: 구조화된 로깅 시스템
- [ ] **페이지네이션**: 캐릭터 목록 페이지네이션
- [ ] **DB 마이그레이션**: Alembic 도입
- [ ] **에러 핸들링**: 전역 예외 핸들러
- [ ] **API 버전 관리**: v2 엔드포인트 준비

### 완료된 기능 ✅

- [x] **인증/인가**: JWT 기반 사용자 인증 (로컬 + 카카오)
- [x] **환경 변수**: `.env` 파일 지원
- [x] **댓글 보안**: 로그인 기반 작성으로 변경

### 개선 사항

- [ ] API 응답 캐싱 (Redis)
- [ ] 이미지 업로드 기능
- [ ] 검색 및 필터링 기능
- [ ] 관리자 대시보드

---

## 📄 라이선스

이 프로젝트는 개인 프로젝트입니다.

---

## 📞 연락처

문의사항이나 버그 제보는 이슈를 통해 남겨주세요.

---

**Made with ❤️ for MapleStory lovers**
