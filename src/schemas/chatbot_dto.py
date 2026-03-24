from pydantic import BaseModel
from typing import Any


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
    # 카카오 규격에 맞게 camelCase 필드명을 직접 정의
    contextControl: dict[str, Any] | None = None
