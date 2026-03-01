"""
운영팀 초기 데이터 삽입 스크립트.

실제 운영팀 데이터를 ADMIN_TEAM_DATA 리스트에 입력한 후 실행하세요.
Usage: uv run python seed_admin_team.py
"""

import asyncio

from sqlalchemy import select

from src.database import async_session, init_db
from src.models.team import TeamMember, TeamMessage

# ──────────────────────────────────────────────
# 실제 운영팀 정보를 여기에 입력하세요.
# ──────────────────────────────────────────────
ADMIN_TEAM_DATA = [
    {
        "name": "강민",
        "role": "인사팀장",
        "profile_img_url": None,
        "message": {
            "title": "13기 단풍바람을 이끌며",
            "content": "여러분과 함께해서 행복했습니다. 13기도 화이팅!",
            "detail_img_url": None,
        },
    },
    {
        "name": "배승민",
        "role": "행사팀장",
        "profile_img_url": None,
        "message": {
            "title": "함께해서 즐거웠습니다",
            "content": "13기 단풍바람 여러분, 수고 많으셨습니다!",
            "detail_img_url": None,
        },
    },
    {
        "name": "강민아",
        "role": "홍보팀장",
        "profile_img_url": None,
        "message": {
            "title": "단풍바람 홍보를 맡아",
            "content": "열심히 활동해 주신 모든 분들께 감사드립니다.",
            "detail_img_url": None,
        },
    },
]


async def seed_admin_team() -> None:
    await init_db()
    async with async_session() as db:
        result = await db.execute(select(TeamMember).limit(1))
        if result.scalar_one_or_none() is not None:
            print("운영팀 데이터가 이미 존재합니다. 건너뜁니다.")
            return

        for data in ADMIN_TEAM_DATA:
            member = TeamMember(
                name=data["name"],
                role=data["role"],
                profile_img_url=data["profile_img_url"],
            )
            db.add(member)
            await db.flush()

            msg_data = data.get("message")
            if msg_data:
                message = TeamMessage(
                    member_id=member.id,
                    title=msg_data["title"],
                    content=msg_data["content"],
                    detail_img_url=msg_data.get("detail_img_url"),
                )
                db.add(message)

        await db.commit()
        print(f"운영팀 데이터 {len(ADMIN_TEAM_DATA)}명 삽입 완료.")


if __name__ == "__main__":
    asyncio.run(seed_admin_team())
