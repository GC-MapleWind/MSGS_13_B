from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.models.team import TeamMember


async def get_all_members(db: AsyncSession) -> list[TeamMember]:
    role_priority = case(
        (TeamMember.role == "행사팀원", 1),
        (TeamMember.role == "행사팀", 1),
        (TeamMember.role == "홍보팀원", 2),
        (TeamMember.role == "홍보팀", 2),
        (TeamMember.role == "인사팀원", 3),
        (TeamMember.role == "인사팀", 3),
        (TeamMember.role == "행사팀장", 4),
        (TeamMember.role == "홍보팀장", 5),
        (TeamMember.role == "인사팀장", 6),
        (TeamMember.role == "회장", 7),
        else_=99,
    )

    result = await db.execute(
        select(TeamMember).order_by(role_priority.asc(), TeamMember.name.asc())
    )
    return list(result.scalars().all())


async def get_member_by_id(db: AsyncSession, member_id: int) -> TeamMember | None:
    result = await db.execute(
        select(TeamMember)
        .options(joinedload(TeamMember.message))
        .filter(TeamMember.id == member_id)
    )
    return result.scalar_one_or_none()
