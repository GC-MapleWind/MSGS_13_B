from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db
from schemas.team_dto import TeamMemberResponse, TeamMemberDetailResponse
from services import character_service, team_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/notices", response_model=dict)
async def get_notices():
    return {
        "news": [
            {
                "title": "단풍바람 오픈!",
                "content": "메이플스토리 결산 서비스가 시작되었습니다.",
            },
            {
                "title": "새 시즌 업데이트",
                "content": "2026년 여름 시즌 데이터가 추가되었습니다.",
            },
        ],
        "team_msg": [
            {"author": "운영팀", "content": "항상 이용해 주셔서 감사합니다."},
        ],
    }


@router.get("/team", response_model=list[TeamMemberResponse])
async def get_team_members(db: AsyncSession = Depends(get_db)):
    """운영팀 전체 정보 및 리스트 조회"""
    return await team_service.get_team_members(db)


@router.get("/team/{member_id}", response_model=TeamMemberDetailResponse)
async def get_team_member_detail(member_id: int, db: AsyncSession = Depends(get_db)):
    """특정 팀원의 상세 한마디 조회"""
    return await team_service.get_team_member_detail(db, member_id)


@router.get("/admin-character", response_model=dict)
async def get_admin_character(db: AsyncSession = Depends(get_db)):
    """사이드바용: 운영팀 캐릭터 ID 반환"""
    character = await character_service.get_admin_character(db)
    if not character:
        return {"id": None}
    return {"id": character.id, "name": character.name}
