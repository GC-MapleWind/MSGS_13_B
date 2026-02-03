import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from database import async_session, init_db
from models.character import Character
from models.settlement import Settlement
from models.comment import Comment


async def seed_data():
    """Insert dummy data if the database is empty."""
    async with async_session() as db:
        result = await db.execute(select(Character).limit(1))
        if result.scalar_one_or_none() is not None:
            return

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

        comments = [
            Comment(author="메생러", content="올해도 수고했어요!", password=None),
            Comment(author="단풍잎", content="결산 보니까 뿌듯하네요 ㅎㅎ", password="1234"),
            Comment(author="익명유저", content="다들 대단하시다...", password=None),
        ]
        db.add_all(comments)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_data()
    yield


app = FastAPI(title="단풍바람 (MapleWind) API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from controller.v1.characters import router as characters_router
from controller.v1.settlements import router as settlements_router
from controller.v1.comments import router as comments_router
from controller.v1.system import router as system_router

app.include_router(characters_router, prefix="/api/v1")
app.include_router(settlements_router, prefix="/api/v1")
app.include_router(comments_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")
