from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from repositories import team_repo
from models.team import TeamMember

async def get_team_members(db: AsyncSession) -> list[TeamMember]:
    return await team_repo.get_all_members(db)

async def get_team_member_detail(db: AsyncSession, member_id: int) -> TeamMember:
    member = await team_repo.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    return member
