# 단풍바람 (MapleWind) 코딩 컨벤션

이 문서는 프로젝트 전반에 걸쳐 일관된 코드 스타일을 유지하기 위한 규칙을 정의합니다.

---

## 1. 아키텍처 규칙

### 3-Layer Architecture

모든 기능은 반드시 아래 4개 계층을 거쳐 구현합니다.

```
Controller (Router)  →  HTTP 요청/응답, 라우팅, response_model 지정
       ↓
Service              →  비즈니스 로직, 유효성 검증, 예외 발생
       ↓
Repository           →  DB 쿼리 실행, ORM 모델 반환
       ↓
Model                →  SQLAlchemy 테이블 정의
```

**금지 사항:**
- Controller에서 직접 Repository를 호출하지 않습니다.
- Repository에서 `HTTPException`을 발생시키지 않습니다.
- Service에서 `select()`, `db.execute()` 등 직접 쿼리를 작성하지 않습니다.

### 계층별 책임

| 계층 | 파일 위치 | 책임 | 의존 대상 |
|------|-----------|------|-----------|
| Controller | `controller/v1/<도메인>.py` | 라우팅, DI, response_model | Service |
| Service | `services/<도메인>_service.py` | 비즈니스 로직, 예외 처리 | Repository |
| Repository | `repositories/<도메인>_repo.py` | DB CRUD | Model |
| Model | `models/<도메인>.py` | 테이블 스키마 | Base |
| Schema (DTO) | `schemas/<도메인>_dto.py` | 요청/응답 직렬화 | - |

---

## 2. 네이밍 규칙

### 파일명

| 대상 | 규칙 | 예시 |
|------|------|------|
| 모델 | `<도메인>.py` (단수) | `character.py` |
| 스키마 | `<도메인>_dto.py` | `character_dto.py` |
| 리포지토리 | `<도메인>_repo.py` | `character_repo.py` |
| 서비스 | `<도메인>_service.py` | `character_service.py` |
| 컨트롤러 | `<도메인>.py` (복수) | `characters.py` |

### 클래스/함수/변수

| 대상 | 규칙 | 예시 |
|------|------|------|
| 클래스 | PascalCase, 단수형 | `Character`, `Settlement` |
| 테이블명 | snake_case, 복수형 | `characters`, `settlements` |
| 함수 | snake_case | `get_all_characters()` |
| 변수 | snake_case | `char_id`, `settlement_id` |
| 상수 | UPPER_SNAKE_CASE | `DATABASE_URL` |
| Pydantic DTO | PascalCase + 용도 접미사 | `CharacterResponse`, `CommentCreate` |

### DTO 네이밍 패턴

| 접미사 | 용도 | 예시 |
|--------|------|------|
| `Base` | 공통 필드 정의 (상속용) | `CharacterBase` |
| `Create` | POST 요청 바디 | `CommentCreate` |
| `Response` | 목록/기본 응답 | `CharacterResponse` |
| `DetailResponse` | 상세 조회 응답 | `CharacterDetailResponse` |

---

## 3. 임포트 순서

모든 파일에서 아래 순서를 따릅니다. 그룹 사이에 빈 줄 하나를 넣습니다.

```python
# 1. 표준 라이브러리
import datetime
from contextlib import asynccontextmanager

# 2. 서드파티 패키지
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. 로컬 모듈
from database import Base
from models.character import Character
from repositories import character_repo
from schemas.character_dto import CharacterResponse
```

---

## 4. 타입 어노테이션

### Python 3.12 스타일 사용

```python
# Optional → | None
detail_txt: str | None = None

# 내장 list 사용 (typing.List 사용 금지)
async def get_all(...) -> list[Character]:

# 함수 시그니처 전체에 타입 명시
async def get_by_id(db: AsyncSession, char_id: int) -> Character | None:
```

### SQLAlchemy Mapped 타입

```python
# Mapped[] + mapped_column() 패턴 사용
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
name: Mapped[str] = mapped_column(String, nullable=False)
detail_txt: Mapped[str | None] = mapped_column(String, nullable=True)
```

---

## 5. 비동기 패턴

### 모든 계층에서 async/await 사용

```python
# Controller
async def get_characters(db: AsyncSession = Depends(get_db)):

# Service
async def get_all_characters(db: AsyncSession) -> list[Character]:

# Repository
async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Character]:
```

### DB 세션 관리

- Controller: `Depends(get_db)` 로 주입
- Service/Repository: 첫 번째 인자로 `db: AsyncSession` 전달
- 직접 세션 생성 금지 (seed 함수 등 특수 경우 제외)

---

## 6. 에러 처리

### 계층별 에러 처리 전략

| 계층 | 처리 방식 |
|------|-----------|
| Repository | `None` 반환 (not found 시) |
| Service | `HTTPException` 발생 |
| Controller | Service에 위임 (직접 에러 처리 안 함) |

```python
# Repository - None 반환
async def get_by_id(db: AsyncSession, char_id: int) -> Character | None:
    result = await db.execute(select(Character).where(Character.id == char_id))
    return result.scalar_one_or_none()

# Service - HTTPException 발생
async def get_character_info(db: AsyncSession, char_id: int) -> Character:
    character = await character_repo.get_by_id(db, char_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character

# Controller - 위임만
@router.get("/{character_id}", response_model=CharacterDetailResponse)
async def get_character(character_id: int, db: AsyncSession = Depends(get_db)):
    return await character_service.get_character_info(db, character_id)
```

---

## 7. SQLAlchemy 쿼리 패턴

### 조회 패턴

```python
# 단건 조회
result = await db.execute(select(Model).where(Model.id == id))
return result.scalar_one_or_none()

# 목록 조회
result = await db.execute(select(Model).offset(skip).limit(limit))
return list(result.scalars().all())

# 정렬 포함 조회
result = await db.execute(
    select(Model)
    .where(Model.field == value)
    .order_by(Model.date_field.desc())
)
return list(result.scalars().all())

# 카운트
result = await db.execute(select(func.count(Model.id)))
return result.scalar_one()
```

### 생성 패턴

```python
async def create(db: AsyncSession, item: Model) -> Model:
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
```

---

## 8. Pydantic DTO 패턴

### 상속 구조

```python
class DomainBase(BaseModel):
    """공통 필드 - 생성/응답 모두에서 사용"""
    name: str
    field: str | None = None

class DomainResponse(DomainBase):
    """응답용 - id 포함, ORM 변환 활성화"""
    id: int
    model_config = {"from_attributes": True}

class DomainDetailResponse(DomainResponse):
    """상세 응답 - 추가 필드 확장용"""
    pass
```

### 요청/응답 분리

```python
class CommentCreate(BaseModel):
    """요청용 - 사용자 입력 필드만"""
    author: str
    content: str
    password: str | None = None

class CommentResponse(BaseModel):
    """응답용 - 민감 정보(password) 제외"""
    id: int
    author: str
    content: str
    created_at: datetime.datetime
    model_config = {"from_attributes": True}
```

---

## 9. Router(Controller) 패턴

### 라우터 정의

```python
router = APIRouter(prefix="/<도메인복수>", tags=["<도메인복수>"])
```

### 엔드포인트 선언

```python
# GET 목록
@router.get("", response_model=list[DomainResponse])
async def get_items(db: AsyncSession = Depends(get_db)):
    return await domain_service.get_all(db)

# GET 단건
@router.get("/{item_id}", response_model=DomainDetailResponse)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    return await domain_service.get_item(db, item_id)

# POST 생성
@router.post("", response_model=DomainResponse, status_code=201)
async def create_item(data: DomainCreate, db: AsyncSession = Depends(get_db)):
    return await domain_service.create_item(db, data)
```

### 쿼리 파라미터 (페이지네이션)

```python
@router.get("", response_model=list[CommentResponse])
async def get_comments(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await comment_service.get_comments(db, page=page, limit=limit)
```

---

## 10. 프로젝트 구조 규칙

### 새 도메인 추가 시 필수 생성 파일

1. `models/<도메인>.py` - SQLAlchemy 모델
2. `schemas/<도메인>_dto.py` - Pydantic DTO
3. `repositories/<도메인>_repo.py` - Repository 함수들
4. `services/<도메인>_service.py` - Service 함수들
5. `controller/v1/<도메인복수>.py` - Router

### API 버전 관리

- 모든 엔드포인트는 `/api/v1` prefix 아래에 위치
- 새 버전이 필요하면 `controller/v2/` 디렉토리 생성
- `main.py`에서 라우터 등록

### `__init__.py`

- `models/__init__.py`: 모든 모델 클래스를 export
- 나머지 `__init__.py`: 비워 둠 (패키지 인식용)

---

## 11. 기타 규칙

### 독스트링/주석

- 명확한 함수는 독스트링 불필요
- 복잡한 비즈니스 로직에만 간결한 영문 독스트링 작성
- 인라인 주석은 최소화

### 날짜 처리

- DB 저장: ISO 8601 (`YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SS`)
- API 응답: ISO 8601 원본 반환 (포맷팅은 프론트엔드 담당)

### CORS

- `main.py`에서 `CORSMiddleware` 설정
- 개발 환경: `allow_origins=["*"]`

### 의존성 관리

- 패키지 매니저: `uv`
- `uv add <패키지>` 로 의존성 추가
- `pyproject.toml` + `uv.lock` 으로 관리
