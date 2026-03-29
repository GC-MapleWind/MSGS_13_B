import os
from fastapi import APIRouter, Header, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.chatbot_dto import ChatbotRequest, ChatbotResponse
from src.services.chatbot_service import chatbot_service
from src.database_chatbot import get_chatbot_db

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

def verify_authorization(
    authorization: str | None = Header(None, alias="Authorization")
) -> bool:
    """
    HTTP 헤더에서 Authorization 값을 가져와 검증합니다.
    """
    expected_key = os.getenv("CHATBOT_AUTHORIZATION_KEY")
    if not expected_key:
        return False
    return authorization == expected_key

def _unauthorized_response() -> ChatbotResponse:
    return ChatbotResponse(
        version="2.0", 
        template={"outputs": [{"simpleText": {"text": "인증되지 않은 요청이담!"}}]}
    )

@router.get("/chat")
async def health_check():
    """카카오 오픈빌더 스킬 URL 검증용 헬스체크"""
    return {"status": "ok"}

@router.post("/chat", response_model=ChatbotResponse)
async def handle_chatbot_chat(
    request_data: ChatbotRequest,
    background_tasks: BackgroundTasks,
    is_authorized: bool = Depends(verify_authorization),
    db: AsyncSession = Depends(get_chatbot_db)
):
    """
    카카오 챗봇의 모든 요청을 처리하는 통합 엔드포인트
    """
    if not is_authorized:
        return _unauthorized_response()
        
    return await chatbot_service.process_chatbot_chat(db, request_data, background_tasks)
