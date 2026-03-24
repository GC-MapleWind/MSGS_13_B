import os
from fastapi import APIRouter, Header, Depends
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
        return True
        
    return authorization == expected_key

@router.post("/image", response_model=ChatbotResponse)
async def handle_chatbot_image(
    request_data: ChatbotRequest,
    is_authorized: bool = Depends(verify_authorization),
    db: AsyncSession = Depends(get_chatbot_db)
):
    """
    카카오 챗봇 이미지 요청 처리 (저장 및 Carousel 응답)
    """
    if not is_authorized:
        return ChatbotResponse(
            version="2.0", 
            template={"outputs": [{"simpleText": {"text": "인증되지 않은 요청이담!"}}]}
        )
        
    return await chatbot_service.process_chatbot_image(db, request_data)

@router.post("/info", response_model=ChatbotResponse)
async def handle_chatbot_info(
    request_data: ChatbotRequest,
    is_authorized: bool = Depends(verify_authorization),
    db: AsyncSession = Depends(get_chatbot_db)
):
    """
    카카오 챗봇 사용자 정보(이름, 학번, 한마디) 입력 처리
    """
    if not is_authorized:
        return ChatbotResponse(
            version="2.0", 
            template={"outputs": [{"simpleText": {"text": "인증되지 않은 요청이담!"}}]}
        )
        
    return await chatbot_service.process_chatbot_info(db, request_data)

@router.post("/image/delete", response_model=ChatbotResponse)
async def handle_delete_images(
    request_data: ChatbotRequest,
    is_authorized: bool = Depends(verify_authorization),
    db: AsyncSession = Depends(get_chatbot_db)
):
    """
    사용자의 모든 임시 이미지 및 정보 삭제 요청 처리
    """
    if not is_authorized:
        return ChatbotResponse(
            version="2.0", 
            template={"outputs": [{"simpleText": {"text": "인증되지 않은 요청이담!"}}]}
        )
        
    return await chatbot_service.delete_all_images(db, request_data)
