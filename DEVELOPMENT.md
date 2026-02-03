# 단풍바람 (MapleWind) 개발 가이드

이 문서는 새로운 개발자가 프로젝트에 합류하여 개발을 이어갈 수 있도록 작성되었습니다.

---

## 1. 프로젝트 개요

메이플스토리 캐릭터 결산/업적 추적 백엔드 API 서비스입니다.

| 항목 | 내용 |
|------|------|
| 프레임워크 | FastAPI |
| Python | 3.12 |
| DB | SQLite (aiosqlite 비동기) |
| ORM | SQLAlchemy 2.0 (Async) |
| 패키지 매니저 | uv |
| 아키텍처 | 3-Layer (Controller → Service → Repository) |

---

## 2. 환경 설정

### 사전 요구사항

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 패키지 매니저

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone <repository-url>
cd dpbr_13_B

# 2. 의존성 설치
uv sync

# 3. 서버 실행
uv run uvicorn main:app --reload

# 4. API 문서 확인
# http://127.0.0.1:8000/docs       (Swagger UI)
# http://127.0.0.1:8000/redoc      (ReDoc)
```

### 초기 데이터

서버 첫 실행 시 DB가 비어 있으면 자동으로 시드 데이터가 삽입됩니다.
- 캐릭터 3건 (강민아, 하늘빛, 바람의검)
- 결산 4건
- 댓글 3건

DB 초기화가 필요하면 `maplewind.db` 파일을 삭제하고 서버를 재시작하세요.

---

## 3. 디렉토리 구조

```
.
├── main.py                     # 앱 진입점 (FastAPI 인스턴스, 미들웨어, 라우터 등록, 시드)
├── database.py                 # DB 엔진, 세션, Base 클래스, init_db
├── pyproject.toml              # 의존성 정의
├── uv.lock                     # 의존성 잠금 파일
├── plan.md                     # 원본 기획서
├── CONVENTIONS.md              # 코딩 컨벤션
├── DEVELOPMENT.md              # 이 문서
│
├── models/                     # SQLAlchemy ORM 모델
│   ├── __init__.py             # 모델 클래스 export
│   ├── character.py
│   ├── settlement.py
│   └── comment.py
│
├── schemas/                    # Pydantic DTO (Request/Response)
│   ├── __init__.py
│   ├── character_dto.py
│   ├── settlement_dto.py
│   └── comment_dto.py
│
├── repositories/               # 데이터 접근 계층 (DB 쿼리)
│   ├── __init__.py
│   ├── character_repo.py
│   ├── settlement_repo.py
│   └── comment_repo.py
│
├── services/                   # 비즈니스 로직 계층
│   ├── __init__.py
│   ├── character_service.py
│   ├── settlement_service.py
│   └── comment_service.py
│
└── controller/                 # API 라우터 계층
    ├── __init__.py
    ├── dependencies.py         # get_db 의존성 주입
    └── v1/
        ├── __init__.py
        ├── characters.py       # GET /characters, /{id}, /{id}/settlements
        ├── settlements.py      # GET /settlements/{id}
        ├── comments.py         # GET /comments, POST /comments
        └── system.py           # GET /system/notices
```

---

## 4. 데이터 흐름

### 읽기 (GET) 요청

```
HTTP Request
  → Controller: 라우팅, DB 세션 주입
    → Service: 비즈니스 로직, 존재 여부 검증
      → Repository: SQLAlchemy 쿼리 실행
        → DB: 데이터 반환
      ← Repository: ORM 모델 반환
    ← Service: ORM 모델 반환 (없으면 HTTPException)
  ← Controller: response_model로 Pydantic 직렬화
HTTP Response (JSON)
```

### 쓰기 (POST) 요청

```
HTTP Request (JSON Body)
  → Controller: Pydantic DTO로 검증 (CommentCreate)
    → Service: DTO → ORM 모델 변환, 비즈니스 로직
      → Repository: db.add → db.commit → db.refresh
      ← Repository: 저장된 ORM 모델 반환
    ← Service: ORM 모델 반환
  ← Controller: response_model로 직렬화 (민감 필드 제외)
HTTP Response (201 Created, JSON)
```

---

## 5. 새 도메인(기능) 추가 가이드

예시: `Notification`(알림) 기능을 추가한다고 가정합니다.

### Step 1: Model 정의

`models/notification.py`:

```python
import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
```

`models/__init__.py`에 추가:

```python
from models.notification import Notification
```

### Step 2: Schema(DTO) 정의

`schemas/notification_dto.py`:

```python
import datetime

from pydantic import BaseModel


class NotificationBase(BaseModel):
    title: str
    content: str


class NotificationCreate(NotificationBase):
    pass


class NotificationResponse(NotificationBase):
    id: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
```

### Step 3: Repository 작성

`repositories/notification_repo.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification


async def get_all(db: AsyncSession, skip: int = 0, limit: int = 20) -> list[Notification]:
    result = await db.execute(
        select(Notification).order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, notification_id: int) -> Notification | None:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, notification: Notification) -> Notification:
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification
```

### Step 4: Service 작성

`services/notification_service.py`:

```python
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from repositories import notification_repo
from schemas.notification_dto import NotificationCreate


async def get_all_notifications(db: AsyncSession, page: int = 1, limit: int = 20) -> list[Notification]:
    skip = (page - 1) * limit
    return await notification_repo.get_all(db, skip=skip, limit=limit)


async def get_notification(db: AsyncSession, notification_id: int) -> Notification:
    notification = await notification_repo.get_by_id(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


async def create_notification(db: AsyncSession, data: NotificationCreate) -> Notification:
    notification = Notification(
        title=data.title,
        content=data.content,
    )
    return await notification_repo.create(db, notification)
```

### Step 5: Controller(Router) 작성

`controller/v1/notifications.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db
from schemas.notification_dto import NotificationCreate, NotificationResponse
from services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
async def get_notifications(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_all_notifications(db, page=page, limit=limit)


@router.post("", response_model=NotificationResponse, status_code=201)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.create_notification(db, data)
```

### Step 6: 라우터 등록

`main.py`에 추가:

```python
from controller.v1.notifications import router as notifications_router

app.include_router(notifications_router, prefix="/api/v1")
```

---

## 6. 현재 API 엔드포인트

모든 엔드포인트는 `/api/v1` 접두사를 가집니다.

### 캐릭터

| Method | 경로 | 설명 |
|--------|------|------|
| GET | `/characters` | 전체 캐릭터 목록 |
| GET | `/characters/{character_id}` | 캐릭터 상세 |
| GET | `/characters/{character_id}/settlements` | 캐릭터의 결산 목록 |

### 결산

| Method | 경로 | 설명 |
|--------|------|------|
| GET | `/settlements/{settlement_id}` | 결산 상세 |

### 댓글

| Method | 경로 | 설명 |
|--------|------|------|
| GET | `/comments?page=1&limit=20` | 댓글 목록 (페이지네이션) |
| POST | `/comments` | 댓글 작성 |

### 시스템

| Method | 경로 | 설명 |
|--------|------|------|
| GET | `/system/notices` | 소식 및 운영팀 메시지 |

---

## 7. 의존성 관리

```bash
# 패키지 추가
uv add <패키지명>

# 개발 전용 패키지 추가
uv add --dev <패키지명>

# 의존성 동기화 (uv.lock 기반)
uv sync
```

### 현재 의존성

| 패키지 | 용도 |
|--------|------|
| `fastapi` | 웹 프레임워크 |
| `uvicorn[standard]` | ASGI 서버 |
| `sqlalchemy` | ORM |
| `aiosqlite` | SQLite 비동기 드라이버 |

---

## 8. 향후 개발 참고사항

### 미구현 사항

- **인증/인가**: 현재 모든 엔드포인트가 공개 상태
- **테스트**: 테스트 프레임워크 및 테스트 코드 없음
- **로깅**: 구조화된 로깅 미적용
- **환경 변수**: `DATABASE_URL` 등이 하드코딩 상태
- **댓글 비밀번호**: 평문 저장 (해싱 필요)
- **캐릭터 목록 페이지네이션**: 현재 전체 반환

### 프론트엔드 연동

- 프론트엔드: SvelteKit 기반
- CORS: `allow_origins=["*"]` 설정 완료
- 날짜 포맷: 백엔드는 ISO 8601 반환, 프론트엔드에서 한글 포맷 변환

### DB 변경 시

현재 마이그레이션 도구(Alembic 등)는 미적용 상태입니다.
- 개발 중: `maplewind.db` 삭제 후 재시작으로 스키마 재생성
- 운영 적용 시: Alembic 도입 권장
