import re
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.chatbot_dto import ChatbotRequest, ChatbotResponse
from src.repositories.chatbot_repo import chatbot_repo


class ChatbotService:
    async def process_chatbot_image(self, db: AsyncSession, request_data: ChatbotRequest) -> ChatbotResponse:
        """
        카카오 챗봇 이미지 업로드 및 Carousel 응답
        """
        user_key = request_data.userRequest.get("user", {}).get("id", "unknown_user")
        params = request_data.action.get("params", {})
        image_url_raw = params.get("kakaobot_image", "")

        if not image_url_raw:
            saved_images = await chatbot_repo.get_all_by_user(db, user_key)
            if not saved_images:
                return self._build_empty_response("이미지를 찾을 수 없담! 사진을 먼저 보내달람.")
            return self._build_carousel_response([img.image_url for img in saved_images])

        match = re.search(r"List\((.*?)\)", image_url_raw)
        if match:
            urls_content = match.group(1).strip()
            image_urls = [url.strip() for url in urls_content.split(",") if url.strip()]
        else:
            image_urls = [image_url_raw.strip()]

        for url in image_urls:
            if url:
                await chatbot_repo.add_image(db, user_key, url)
        await db.commit()

        saved_images = await chatbot_repo.get_all_by_user(db, user_key)
        all_image_urls = [img.image_url for img in saved_images]

        return self._build_carousel_response(all_image_urls[:10])

    async def delete_all_images(self, db: AsyncSession, request_data: ChatbotRequest) -> ChatbotResponse:
        """사용자의 모든 임시 데이터 삭제"""
        user_key = request_data.userRequest.get("user", {}).get("id", "unknown_user")
        await chatbot_repo.delete_all_by_user(db, user_key)
        await db.commit()
        return self._build_empty_response("보냈던 사진과 정보를 모두 삭제했담! 다시 보내달람.")

    async def process_chatbot_chat(self, db: AsyncSession, request_data: ChatbotRequest) -> ChatbotResponse:
        """
        /chat 요청 처리: 
        1. 진행 중인 이벤트가 있다면 답변 저장 및 다음 질문 진행
        2. 진행 중인 이벤트가 없다면 이벤트 선택 목록 반환
        """
        user_key = request_data.userRequest.get("user", {}).get("id", "unknown_user")
        utterance = request_data.userRequest.get("utterance", "").strip()
        
        session = await chatbot_repo.get_or_create_session(db, user_key)
        current_data = session.data or {}
        active_event = current_data.get("active_event")

        # 1. 이미 진행 중인 이벤트가 있는 경우 -> 질문 답변 처리로 넘김
        if active_event and current_data.get("__started__"):
            return await self.process_chatbot_info(db, request_data)

        # 2. 새로운 이벤트 선택인지 확인
        event = await chatbot_repo.get_event_info(db, utterance)
        if event:
            # 이벤트를 새로 선택한 경우
            await chatbot_repo.update_data(db, user_key, "active_event", event.name)
            await chatbot_repo.update_data(db, user_key, "__started__", "true")
            
            steps = await chatbot_repo.get_steps_by_event(db, event.name)
            if not steps:
                await db.commit()
                return self._build_empty_response(f"'{event.name}' 이벤트에 등록된 질문이 없담!")
            
            await db.commit()
            return self._build_empty_response(
                f"알겠담! **{event.name}** 참여를 시작하겠담.\n\n{steps[0].question_text}",
                contexts=[{"name": "infolist", "lifeSpan": 10}]
            )

        # 3. 아무것도 해당하지 않으면 이벤트 목록 반환
        events = await chatbot_repo.get_all_events(db)
        if not events:
            return self._build_empty_response("현재 진행 중인 이벤트가 없담! 다음에 다시 확인해달람.")

        quick_replies = [{"label": e.name, "action": "message", "messageText": e.name} for e in events]
        return self._build_empty_response(
            "참여할 이벤트를 아래의 버튼을 눌러 선택해달람!",
            quick_replies=quick_replies
        )

    async def process_chatbot_info(self, db: AsyncSession, request_data: ChatbotRequest) -> ChatbotResponse:
        """
        백엔드 주도형 질문 시스템: 세션의 active_event에 따른 질문을 순차적으로 던집니다.
        """
        user_key = request_data.userRequest.get("user", {}).get("id", "unknown_user")
        utterance = request_data.userRequest.get("utterance", "").strip()
        
        # 1. 사용자의 세션 및 질문 목록 조회
        session = await chatbot_repo.get_or_create_session(db, user_key)
        current_data = session.data or {}
        active_event = current_data.get("active_event")

        # 활성 이벤트가 있으면 해당 이벤트 질문만, 없으면 전체 질문 조회
        if active_event:
            steps = await chatbot_repo.get_steps_by_event(db, active_event)
        else:
            steps = await chatbot_repo.get_steps(db)
        
        if not steps:
            return self._build_empty_response("질문 목록이 비어있담!")

        # 2. 첫 진입 처리
        if not current_data.get("__started__"):
            # 시작 흔적만 남기고 첫 번째 질문 던짐
            await chatbot_repo.update_data(db, user_key, "__started__", "true")
            await db.commit()
            return self._build_empty_response(
                f"알겠담! {steps[0].question_text}",
                contexts=[{"name": "infolist", "lifeSpan": 10}] # 문맥 부여
            )

        # 3. 답변 저장 (현재 채워야 할 필드 찾기)
        target_step = None
        for step in steps:
            if step.field_name not in current_data:
                target_step = step
                break
        
        if target_step:
            # 현재 들어온 발화를 해당 필드에 저장
            await chatbot_repo.update_data(db, user_key, target_step.field_name, utterance)
            await db.commit()

        # 4. 다음 질문 결정
        updated_session = await chatbot_repo.get_session(db, user_key)
        updated_data = updated_session.data or {}
        next_step = None
        for step in steps:
            if step.field_name not in updated_data:
                next_step = step
                break
        
        # 5. 응답 생성
        if next_step:
            # 다음 질문이 있으면 문맥을 유지하며 질문 던짐
            return self._build_empty_response(
                f"'{utterance}'(이)가 맞담? 이제 **{next_step.question_text}**",
                contexts=[{"name": "infolist", "lifeSpan": 10}]
            )
        else:
            # 모든 질문 완료 시 문맥 삭제 및 요약
            img_list = [url for url in (updated_session.image_urls or "").split(",") if url.strip()]
            
            summary_parts = []
            if active_event:
                summary_parts.append(f"**[{active_event} 참여 정보]**")
            
            for s in steps:
                if s.field_name == "__started__" or s.field_name == "active_event":
                    continue
                val = updated_data.get(s.field_name, "미입력")
                summary_parts.append(f"- {s.field_name}: {val}")
            
            summary = "\n".join(summary_parts)
            text = (f"모든 정보를 받았담!\n{summary}\n\n현재까지 총 {len(img_list)}장의 사진이 있담. 등록을 완료해달람!")
            return self._build_final_response(text, contexts=[{"name": "infolist", "lifeSpan": 0}])

    def _build_final_response(self, text: str, contexts: list[dict] | None = None) -> ChatbotResponse:
        quick_replies = [
            {"messageText": "사진을 더 보내겠담", "action": "block", "blockId": "69bbb962bc19300ad3dcae77", "label": "사진 더 보내기"},
            {"messageText": "정보를 처음부터 다시 입력하겠담", "action": "block", "blockId": "69bc119e6a7a1b7876fb7382", "label": "정보/사진 초기화"},
            {"messageText": "등록을 완료하겠담", "action": "block", "blockId": "REGISTER_COMPLETE_BLOCK_ID", "label": "최종 등록하기"}
        ]
        return self._build_empty_response(text, quick_replies=quick_replies, contexts=contexts)

    def _build_carousel_response(self, image_urls: list[str]) -> ChatbotResponse:
        items = [{"thumbnail": {"imageUrl": url}} for url in image_urls]
        quick_replies = [
            {"messageText": "사진을 더 보내겠담", "action": "block", "blockId": "69bbb962bc19300ad3dcae77", "label": "사진 더 보내기"},
            {"messageText": "정보를 입력하겠담", "action": "block", "blockId": "69bbd997aafcbe124ef9a6c9", "label": "정보 입력하기"},
            {"messageText": "사진을 전부 삭제하고 다시 보내겠담", "action": "block", "blockId": "69bc119e6a7a1b7876fb7382", "label": "전체 삭제"}
        ]
        template = {
            "outputs": [
                {"carousel": {"type": "basicCard", "items": items}},
                {"simpleText": {"text": f"현재까지 총 {len(image_urls)}장의 사진을 받았담!"}},
                {"simpleText": {"text": "정보를 입력하려면 하단 버튼을 눌러줘람!"}}
            ],
            "quickReplies": quick_replies
        }
        return ChatbotResponse(version="2.0", template=template)

    def _build_empty_response(self, text: str, quick_replies: list[dict] | None = None, contexts: list[dict] | None = None) -> ChatbotResponse:
        template = {
            "outputs": [{"simpleText": {"text": text}}],
            "quickReplies": quick_replies if quick_replies else []
        }
        res = ChatbotResponse(version="2.0", template=template)
        if contexts:
            res.contextControl = {"values": contexts}
        return res


chatbot_service = ChatbotService()
