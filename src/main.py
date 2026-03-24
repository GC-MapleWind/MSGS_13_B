import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.controller.v1.characters import router as characters_router
from src.controller.v1.comments import router as comments_router
from src.controller.v1.settlements import router as settlements_router
from src.controller.v1.system import router as system_router
from src.controller.v1.users import router as users_router
from src.controller.v1.chatbot import router as chatbot_router
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse, Response
from starlette.types import Scope
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from src.admin import setup_admin
from src.database import async_session, engine, init_db
from src.database_chatbot import init_chatbot_db

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
ADMIN_SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET")
if not ADMIN_SESSION_SECRET:
    raise RuntimeError("ADMIN_SESSION_SECRET is required")


class ImageOnlyStaticFiles(StaticFiles):
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}

    async def get_response(self, path: str, scope: Scope) -> Response:
        if Path(path).suffix.lower() not in self.ALLOWED_EXTENSIONS:
            return PlainTextResponse("Not Found", status_code=404)
        return await super().get_response(path, scope)


async def migrate_user_student_id_to_username() -> None:
    async with async_session() as db:
        bind = db.get_bind()
        if bind.dialect.name != "sqlite":
            return

        columns_result = await db.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in columns_result.fetchall()]
        if "student_id" not in columns:
            return

        users_result = await db.execute(
            text("SELECT id, username, student_id FROM users WHERE student_id IS NOT NULL")
        )
        users = users_result.fetchall()

        for user_id, username, student_id in users:
            if not student_id:
                continue
            if username == student_id:
                continue
            conflict_result = await db.execute(
                text("SELECT id FROM users WHERE username = :student_id AND id != :user_id"),
                {"student_id": student_id, "user_id": user_id},
            )
            if conflict_result.scalar_one_or_none() is None:
                await db.execute(
                    text("UPDATE users SET username = :student_id WHERE id = :user_id"),
                    {"student_id": student_id, "user_id": user_id},
                )

        index_result = await db.execute(text("PRAGMA index_list(users)"))
        for _seq, index_name, _unique, _origin, _partial in index_result.fetchall():
            if "student_id" in index_name:
                await db.execute(text(f"DROP INDEX IF EXISTS {index_name}"))

        version_result = await db.execute(text("SELECT sqlite_version()"))
        sqlite_version = version_result.scalar_one()
        version_parts = tuple(int(part) for part in str(sqlite_version).split(".")[:3])
        if version_parts >= (3, 35, 0):
            await db.execute(text("ALTER TABLE users DROP COLUMN student_id"))
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_chatbot_db()
    await migrate_user_student_id_to_username()
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
Path(_settlements_dir).mkdir(parents=True, exist_ok=True)
_avatars_dir = Path("avatars")
_avatars_dir.mkdir(parents=True, exist_ok=True)
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
    ImageOnlyStaticFiles(directory=_avatars_dir),
    name="avatars",
)

app.include_router(characters_router, prefix=API_V1_PREFIX)
app.include_router(settlements_router, prefix=API_V1_PREFIX)
app.include_router(comments_router, prefix=API_V1_PREFIX)
app.include_router(system_router, prefix=API_V1_PREFIX)
app.include_router(users_router, prefix=API_V1_PREFIX)
app.include_router(chatbot_router, prefix=API_V1_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}
