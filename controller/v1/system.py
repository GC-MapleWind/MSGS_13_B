from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/notices")
async def get_notices():
    return {
        "news": [
            {"title": "단풍바람 오픈!", "content": "메이플스토리 결산 서비스가 시작되었습니다."},
            {"title": "새 시즌 업데이트", "content": "2026년 여름 시즌 데이터가 추가되었습니다."},
        ],
        "team_msg": [
            {"author": "운영팀", "content": "항상 이용해 주셔서 감사합니다."},
        ],
    }
