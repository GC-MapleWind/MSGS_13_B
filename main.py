import datetime
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controller.v1.characters import router as characters_router
from controller.v1.comments import router as comments_router
from controller.v1.settlements import router as settlements_router
from controller.v1.system import router as system_router
from controller.v1.users import router as users_router
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from admin import setup_admin
from database import async_session, engine, init_db
from models.character import Character
from models.comment import Comment
from models.settlement import Settlement
from models.team import TeamMember, TeamMessage

# 환경 변수 로드
load_dotenv()


def _normalize_router_prefix(value: str | None, default: str) -> str:
    raw_value = default if value is None else value.strip()
    if not raw_value:
        raise ValueError("API_V1_PREFIX cannot be empty")

    if not raw_value.startswith("/"):
        raw_value = f"/{raw_value}"

    normalized = raw_value.rstrip("/")
    if normalized in {"", "/"}:
        raise ValueError("API_V1_PREFIX must include at least one path segment")

    return normalized


def _normalize_root_path(value: str | None) -> str:
    if value is None:
        return ""

    raw_value = value.strip()
    if not raw_value:
        return ""

    if not raw_value.startswith("/"):
        raw_value = f"/{raw_value}"

    return raw_value.rstrip("/")


def _normalize_optional_path(value: str | None, default: str) -> str | None:
    raw_value = default if value is None else value.strip()
    if raw_value == "" or raw_value.lower() in {"none", "null", "off", "false"}:
        return None

    if not raw_value.startswith("/"):
        raw_value = f"/{raw_value}"

    normalized = raw_value.rstrip("/")
    return normalized or "/"


API_V1_PREFIX = _normalize_router_prefix(os.getenv("API_V1_PREFIX"), "/api/v1")
API_ROOT_PATH = _normalize_root_path(os.getenv("API_ROOT_PATH"))
API_DOCS_URL = _normalize_optional_path(os.getenv("API_DOCS_URL"), "/docs")
API_REDOC_URL = _normalize_optional_path(os.getenv("API_REDOC_URL"), "/redoc")
API_OPENAPI_URL = _normalize_optional_path(
    os.getenv("API_OPENAPI_URL"), "/openapi.json"
)
ADMIN_SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET", "maplewind-admin-session")


class ImageOnlyStaticFiles(StaticFiles):
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}

    async def get_response(self, path: str, scope):
        if Path(path).suffix.lower() not in self.ALLOWED_EXTENSIONS:
            return PlainTextResponse("Not Found", status_code=404)
        return await super().get_response(path, scope)


async def seed_data():
    """
    데이터베이스에 테스트용 기본 데이터를 필요할 경우 생성한다.

    데이터베이스의 각 테이블(User, Character, Settlement, Comment)에 레코드가 없을 때에 한해 테스트 사용자, 예제 캐릭터들, 해당 캐릭터에 연관된 결산 항목들 및 댓글들을 생성하여 영속화하고 커밋한다.
    """
    async with async_session() as db:
        from models.user import User
        from services.user_service import get_password_hash

        # 1. 테스트 유저 생성
        result = await db.execute(select(User).limit(1))
        test_user = result.scalar_one_or_none()

        if test_user is None:
            test_user = User(
                username="test",
                hashed_password=get_password_hash("password123"),
                name="강민",
                student_id="202145123",
            )
            db.add(test_user)
            await db.flush()  # ID 생성을 위해 flush

        # 2. 캐릭터 생성
        result = await db.execute(select(Character).limit(1))
        if result.scalar_one_or_none() is None:
            characters = [
                Character(
                    name="강민아",
                    detail_txt="담와",
                    level=265,
                    job="아크",
                    server="이브리스",
                    avatar_url=None,
                ),
                Character(
                    name="하늘빛",
                    detail_txt="하빛",
                    level=280,
                    job="아델",
                    server="스카니아",
                    avatar_url=None,
                ),
                Character(
                    name="바람의검",
                    detail_txt=None,
                    level=255,
                    job="나이트로드",
                    server="루나",
                    avatar_url=None,
                ),
            ]
            db.add_all(characters)
            await db.flush()

            # 3. 결산 생성
            settlements = [
                Settlement(
                    character_id=characters[0].id,
                    title="검은 마법사 클리어",
                    description="검은 마법사를 처음으로 클리어했습니다!",
                    img_url=None,
                    acquired_at=datetime.date(2026, 8, 29),
                ),
                Settlement(
                    character_id=characters[0].id,
                    title="레벨 265 달성",
                    description="꾸준한 사냥 끝에 265 레벨을 달성했습니다.",
                    img_url=None,
                    acquired_at=datetime.date(2026, 7, 15),
                ),
                Settlement(
                    character_id=characters[1].id,
                    title="스우 솔로 클리어",
                    description="스우를 솔로로 클리어하는 데 성공!",
                    img_url=None,
                    acquired_at=datetime.date(2026, 8, 10),
                ),
                Settlement(
                    character_id=characters[2].id,
                    title="유니온 8000 달성",
                    description="유니온 레벨 8000을 달성했습니다.",
                    img_url=None,
                    acquired_at=datetime.date(2026, 6, 20),
                ),
            ]
            db.add_all(settlements)

        # 4. 댓글 생성 (유저 연동)
        result = await db.execute(select(Comment).limit(1))
        if result.scalar_one_or_none() is None:
            comments = [
                Comment(
                    user_id=test_user.id,
                    author=test_user.name,
                    content="올해도 수고했어요!",
                ),
                Comment(
                    user_id=test_user.id,
                    author=test_user.name,
                    content="결산 보니까 뿌듯하네요 ㅎㅎ",
                ),
                Comment(
                    user_id=test_user.id,
                    author=test_user.name,
                    content="다들 대단하시다...",
                ),
            ]
            db.add_all(comments)

        # 5. 운영팀 테스트 데이터 생성
        result = await db.execute(select(TeamMember).limit(1))
        if result.scalar_one_or_none() is None:
            new_member = TeamMember(name="테스트", role="테스터", profile_img_url=None)
            db.add(new_member)
            await db.flush()

            new_message = TeamMessage(
                member_id=new_member.id,
                title="제목테스트입니다.",
                content="테스트입니다.",
                detail_img_url=None,
            )
            db.add(new_message)

        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    init_data_dir = Path(os.environ.get("INIT_DATA_DIR", "13기 메생결산"))
    if init_data_dir.exists():
        # INIT_DATA_DIR이 마운트되어 있으면 실제 데이터로 자동 초기화
        from seed_real_data import seed as seed_real
        await seed_real()
    else:
        # 마운트된 데이터 없음 → 테스트 데이터로 초기화
        await seed_data()
    yield


app = FastAPI(
    title="단풍바람 (MapleWind) API",
    version="1.0.0",
    lifespan=lifespan,
    root_path=API_ROOT_PATH,
    docs_url=API_DOCS_URL,
    redoc_url=API_REDOC_URL,
    openapi_url=API_OPENAPI_URL,
)

# CORS 설정: 보안을 위해 허용할 도메인을 명시합니다.
# .env 파일에 ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 와 같이 설정하세요.
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
)
ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=ADMIN_SESSION_SECRET,
)

setup_admin(app, engine)

# 메생결산 이미지 static 서빙
# URL: /static/settlements/{이름}/{이미지명}.png
# 실제 경로: INIT_DATA_DIR/{이름}/{이미지명}.png (기본값: 13기 메생결산/)
_settlements_dir = os.environ.get("INIT_DATA_DIR", "13기 메생결산")
app.mount(
    "/static/settlements",
    ImageOnlyStaticFiles(directory=_settlements_dir),
    name="settlements",
)

# 아바타 이미지 static 서빙
# URL: /static/avatars/{폴더}/avatar_image.png
# 실제 경로: avatars/{폴더}/avatar_image.png
app.mount(
    "/static/avatars",
    StaticFiles(directory="avatars"),
    name="avatars",
)

app.include_router(characters_router, prefix=API_V1_PREFIX)
app.include_router(settlements_router, prefix=API_V1_PREFIX)
app.include_router(comments_router, prefix=API_V1_PREFIX)
app.include_router(system_router, prefix=API_V1_PREFIX)
app.include_router(users_router, prefix=API_V1_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}
