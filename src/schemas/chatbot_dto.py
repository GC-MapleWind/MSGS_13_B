from pydantic import BaseModel
from typing import Any, Optional


class ChatbotRequest(BaseModel):
    """카카오 챗봇으로부터 오는 요청 스키마"""
    bot: dict[str, Any]
    intent: dict[str, Any]
    action: dict[str, Any]
    userRequest: dict[str, Any]
    contexts: list[Any] = []
    flow: dict[str, Any] = {}


class ChatbotResponse(BaseModel):
    """카카오 챗봇으로 보낼 응답 스키마"""
    version: str = "2.0"
    template: dict[str, Any]
    useCallback: Optional[bool] = None # 콜백 사용 여부 (AI 챗봇 콜백 가이드)
