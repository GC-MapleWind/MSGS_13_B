프론트엔드 기획서와 짝을 이루는 **단풍바람(MapleWind) 백엔드 개발 상세 기획서**입니다.
이 문서는 **FastAPI** 프레임워크를 기반으로 하며, 요청하신 **Controller - Service - Repository** 계층형 아키텍처(Layered Architecture) 패턴을 따르도록 작성되었습니다.

---

# 🍁 프로젝트명: 단풍바람 (MapleWind) 백엔드 기획서

## 1. 프로젝트 개요 및 아키텍처
*   **프레임워크:** FastAPI
*   **언어:** Python 3.10+
*   **데이터베이스:** SQLite (파일 기반, 개발 및 소규모 배포 용이)
*   **ORM:** SQLAlchemy (비동기 지원 `aiosqlite` 권장) 또는 SQLModel
*   **아키텍처 패턴:** 3-Layered Architecture
    1.  **Controller (Router):** HTTP 요청/응답 처리, 데이터 검증 (Pydantic).
    2.  **Service:** 비즈니스 로직, 트랜잭션 관리, 예외 처리.
    3.  **Repository:** DB 접근 로직 (CRUD), 쿼리 실행.

---

## 2. 디렉토리 구조 (Project Structure)
기능별 모듈화보다는 **계층별 분리**를 명확히 하는 구조를 제안합니다.

```text
backend/
├── main.py                  # 앱 진입점 (FastAPI 인스턴스 생성, 미들웨어, 라우터 등록)
├── database.py              # DB 연결 설정 (SessionLocal, Base)
├── models/                  # SQLAlchemy DB 모델 (Table 정의)
│   ├── __init__.py
│   ├── character.py
│   ├── settlement.py
│   ├── comment.py
│   └── user.py
├── schemas/                 # Pydantic DTO (Request/Response 모델)
│   ├── __init__.py
│   ├── character_dto.py
│   ├── settlement_dto.py
│   ├── comment_dto.py
│   └── user_dto.py
├── repositories/            # DB 접근 계층
│   ├── __init__.py
│   ├── character_repo.py
│   ├── settlement_repo.py
│   ├── comment_repo.py
│   └── user_repo.py
├── services/                # 비즈니스 로직 계층
│   ├── __init__.py
│   ├── character_service.py
│   ├── settlement_service.py
│   ├── comment_service.py
│   └── user_service.py
└── controller/                     # Controller 계층 (Routers)
    ├── __init__.py
    ├── dependencies.py      # 의존성 주입 (get_db 등)
    └── v1/
        ├── characters.py    # 캐릭터 관련 엔드포인트
        ├── comments.py      # 톡(댓글) 관련 엔드포인트
        ├── system.py        # 소식, 운영팀 한마디 등
        └── users.py         # 사용자/인증 관련 엔드포인트
```

---

## 3. 데이터베이스 모델 설계 (ERD Concept)

### 3.1. Character (캐릭터)
메인 페이지의 카드 및 상세 정보에 사용됩니다.
*   **Table Name:** `characters`

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 캐릭터 고유 ID |
| `name` | String | Unique, Not Null | 캐릭터 닉네임 (예: 강민아) |
| `detail_txt` | String | Nullable | 서브 텍스트 (예: 담와) |
| `level` | Integer | Not Null | 레벨 (예: 265) |
| `job` | String | Not Null | 직업 (예: 아크) |
| `server` | String | Not Null | 서버 (예: 이브리스) |
| `avatar_url` | String | Nullable | 캐릭터 이미지 URL |

### 3.2. Settlement (메생결산 아이템)
캐릭터별로 귀속되는 결산(업적) 내역입니다.
*   **Table Name:** `settlements`

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 결산 아이템 ID |
| `character_id` | Integer | FK(`characters.id`) | 소유 캐릭터 ID |
| `title` | String | Not Null | 제목 (예: 길어도 두 줄로 안 내려가요) |
| `description` | Text | Nullable | 상세 내용 (Textbox) |
| `img_url` | String | Nullable | 업적 이미지 URL |
| `acquired_at` | Date | Not Null | 획득 일자 (예: 2026-08-29) |

### 3.3. Comment (메생결산 톡)
전체 유저가 남기는 방명록/댓글입니다. (로그인 필수)
*   **Table Name:** `comments`

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 댓글 ID |
| `user_id` | Integer | FK(`users.id`) | 작성자 User ID |
| `author` | String | Not Null | 작성자 닉네임 (Snapshot) |
| `content` | Text | Not Null | 댓글 내용 |
| `created_at` | DateTime | Default: Now | 작성 일시 |

### 3.4. User (사용자)
서비스 이용자 및 관리자 계정입니다. 로컬 로그인과 카카오 소셜 로그인을 모두 지원합니다.
*   **Table Name:** `users`

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 유저 ID |
| `username` | String | Unique, Not Null | 로그인 ID (카카오는 ID값 사용) |
| `hashed_password` | String | Nullable | 비밀번호 (로컬 로그인용) |
| `name` | String | Not Null | 실명 |
| `kakao_id` | Integer | Unique, Nullable | 카카오 고유 ID |
| `nickname` | String | Nullable | 닉네임 |
| `refresh_token_hash`| String | Nullable | Refresh Token 해시값 |

---

## 4. API 명세 (API Specification)

모든 API는 `/api/v1` prefix를 가집니다.

### 4.1. 캐릭터 및 결산 (Characters Domain)

**Controller:** `api/v1/characters.py`

1.  **캐릭터 목록 조회 (메인 페이지)**
    *   `GET /characters`
    *   **Response:** `List[CharacterResponse]`
    *   **Logic:** DB에서 모든 캐릭터 조회 (필요 시 페이징).

2.  **캐릭터 상세 정보 조회**
    *   `GET /characters/{character_id}`
    *   **Response:** `CharacterDetailResponse`
    *   **Logic:** 특정 ID의 캐릭터 정보 조회. 없으면 404 에러.

3.  **특정 캐릭터의 결산 목록 조회**
    *   `GET /characters/{character_id}/settlements`
    *   **Response:** `List[SettlementResponse]`
    *   **Logic:** 해당 캐릭터 ID를 가진 Settlement 데이터 조회. 날짜 내림차순 정렬.

4.  **결산 상세 조회 (모달/상세)**
    *   `GET /settlements/{settlement_id}`
    *   **Response:** `SettlementDetailResponse`
    *   **Logic:** 특정 결산 아이템의 상세 내용 반환.

### 4.2. 톡/커뮤니티 (Comments Domain)

**Controller:** `api/v1/comments.py`

1.  **댓글 목록 조회**
    *   `GET /comments`
    *   **Query Params:** `page` (default=1), `limit` (default=20)
    *   **Response:** `List[CommentResponse]`
    *   **Logic:** 작성일시 내림차순 조회.

2.  **댓글 작성**
    *   `POST /comments`
    *   **Request Body:**
        ```json
        {
          "content": "안녕하세요!"
        }
        ```
    *   **Response:** `CommentResponse` (생성된 객체)

### 4.3. 시스템/기타 (System Domain)

**Controller:** `api/v1/system.py`

1.  **사이드바 소식/한마디 조회**
    *   `GET /system/notices`
    *   **Response:** `{ "news": [], "team_msg": [] }`
    *   **Logic:** 공지사항 테이블(Notices)이 있다면 조회, 없다면 하드코딩된 데이터 혹은 설정 파일 반환.

### 4.4. 사용자 및 인증 (Users Domain)

**Controller:** `api/v1/users.py`

1.  **회원가입 (로컬)**
    *   `POST /users/signup`
    *   **Logic:** ID 중복 검사 후 유저 생성.

2.  **로그인 (로컬)**
    *   `POST /users/login`
    *   **Response:** Access Token (Body), Refresh Token (HttpOnly Cookie)

3.  **카카오 로그인 (Phase 1)**
    *   `POST /users/auth/kakao/login`
    *   **Logic:** 인가 코드로 카카오 토큰 발급 → 기존 회원이면 로그인, 신규 회원이면 `register_token` 반환.

4.  **카카오 회원가입 (Phase 2)**
    *   `POST /users/auth/kakao/register`
    *   **Logic:** `register_token` 검증 후 추가 정보(학번 등) 받아 가입 완료.

5.  **토큰 갱신 (Silent Refresh)**
    *   `POST /users/refresh`
    *   **Logic:** 쿠키의 Refresh Token 검증 후 Access Token 재발급 및 RT Rotation.

6.  **회원 탈퇴**
    *   `DELETE /users/me`
    *   **Logic:** 카카오 연결 해제(필요 시) 후 DB 데이터 삭제.

---

## 5. 계층별 상세 구현 가이드

### 5.1. DTO (Schemas - Pydantic)
프론트엔드와 통신하는 데이터 포맷을 정의합니다.

*   `schemas/character_dto.py`:
    ```python
    from pydantic import BaseModel

    class CharacterBase(BaseModel):
        name: str
        level: int
        job: str
        # ...

    class CharacterResponse(CharacterBase):
        id: int
        
        class Config:
            orm_mode = True
    ```

### 5.2. Repository Layer
SQLAlchemy Session을 받아 직접적인 DB 쿼리를 수행합니다.

*   `repositories/character_repo.py`:
    ```python
    from sqlalchemy.orm import Session
    from models.character import Character

    def get_all(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Character).offset(skip).limit(limit).all()

    def get_by_id(db: Session, char_id: int):
        return db.query(Character).filter(Character.id == char_id).first()
    ```

### 5.3. Service Layer
Repository를 호출하고, 데이터 가공 및 예외 처리를 담당합니다.

*   `services/character_service.py`:
    ```python
    from sqlalchemy.orm import Session
    from repositories import character_repo
    from fastapi import HTTPException

    def get_character_info(db: Session, char_id: int):
        character = character_repo.get_by_id(db, char_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        return character
    ```

### 5.4. Controller Layer
Router를 정의하고 Service 함수를 호출합니다.

*   `api/v1/characters.py`:
    ```python
    from fastapi import APIRouter, Depends
    from sqlalchemy.orm import Session
    from api.dependencies import get_db
    from services import character_service
    from schemas.character_dto import CharacterResponse

    router = APIRouter()

    @router.get("/{character_id}", response_model=CharacterResponse)
    def read_character(character_id: int, db: Session = Depends(get_db)):
        return character_service.get_character_info(db, character_id)
    ```

---

## 6. 개발 시 고려사항 (Prompt Context for AI)

AI 코딩 에이전트에게 전달할 때 다음 사항을 강조해 주세요.

1.  **비동기 처리:** 가능하다면 `async def` 컨트롤러와 `aiosqlite`를 사용하여 비동기적으로 구현해줘. (어렵다면 동기식 `sqlite3`도 무방함).
2.  **CORS 설정:** 프론트엔드(SvelteKit)가 로컬의 다른 포트에서 실행되므로, `main.py`에 `CORSMiddleware` 설정을 반드시 포함하여 `allow_origins=["*"]` 또는 프론트엔드 주소를 허용해줘.
3.  **초기 데이터:** DB가 비어있으면 테스트가 어려우므로, `main.py` 실행 시(startup event) 자동으로 더미 데이터를 삽입하는 `init_db` 스크립트를 포함해줘.
4.  **날짜 포맷:** 프론트엔드에서 "2026년 8월 30일" 처럼 한글 포맷을 원하므로, Response DTO에서 `@validator`를 쓰거나 Service 계층에서 포맷팅을 해서 문자열로 내려줄지, 프론트에서 할지 결정해야 함. (일반적으로 백엔드는 ISO 8601 `YYYY-MM-DD`를 보내고 프론트가 변환하는 것이 정석).

이 기획서를 통해 백엔드 개발을 진행하시면 됩니다.