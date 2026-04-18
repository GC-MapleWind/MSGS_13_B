import re
import httpx
import json
import asyncio
from typing import Any
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.chatbot_dto import ChatbotRequest, ChatbotResponse
from src.repositories.chatbot_repo import chatbot_repo
from src.services.google_sheet_service import google_sheet_service
from src.services.chinbabang_service import chinbabang_service
from src.database_chatbot import get_chatbot_db


class ChatbotService:
    async def process_chatbot_chat(self, db: AsyncSession, request_data: ChatbotRequest, background_tasks: BackgroundTasks) -> ChatbotResponse:
        """
        통합 요청 처리: 
        1. 진행 중인 이벤트가 있다면 답변 저장 및 다음 질문 진행
        2. 진행 중인 이벤트가 없다면 이벤트 선택 목록 반환
        """
        user_key = request_data.userRequest.get("user", {}).get("id")
        if not user_key:
            return self._build_empty_response("사용자 정보를 확인할 수 없담! 카카오 앱에서 다시 시도해달람")
        utterance = request_data.userRequest.get("utterance", "").strip()

        session = await chatbot_repo.get_or_create_session(db, user_key)
        current_data = session.data or {}
        active_event = current_data.get("active_event")

        # 0-a. 친바방 제출 트리거
        if utterance == "친바방 제출":
            await chatbot_repo.delete_session(db, user_key)
            await chatbot_repo.get_or_create_session(db, user_key)
            await chatbot_repo.update_data(db, user_key, "active_event", "친바방제출")
            await chatbot_repo.update_data(db, user_key, "__started__", "true")
            await db.commit()
            return await chinbabang_service.start(db, user_key)

        # 0-a2. 빠른 제출 트리거
        if utterance == "빠른 제출":
            await chatbot_repo.delete_session(db, user_key)
            await chatbot_repo.get_or_create_session(db, user_key)
            await chatbot_repo.update_data(db, user_key, "active_event", "친바방제출")
            await chatbot_repo.update_data(db, user_key, "__started__", "true")
            await db.commit()
            return await chinbabang_service.quick_start(db, user_key)

        # 0-b. 제출 내역 조회
        if utterance == "제출 내역":
            return await chinbabang_service.show_history(db, user_key)

        # 0-c. 친바방 플로우 진행 중
        if active_event == "친바방제출" and current_data.get("__started__"):
            return await chinbabang_service.process(db, request_data, background_tasks)

        # 1. 이미 진행 중인 이벤트가 있는 경우 -> 질문 답변 처리로 넘김
        if active_event and current_data.get("__started__"):
            return await self.process_chatbot_info(db, request_data, background_tasks)

        # 2. 새로운 이벤트 선택인지 확인
        event = await chatbot_repo.get_event_info(db, utterance)
        if event:
            await chatbot_repo.update_data(db, user_key, "active_event", event.name)
            await chatbot_repo.update_data(db, user_key, "__started__", "true")

            steps = await chatbot_repo.get_steps_by_event(db, event.name)
            if not steps:
                await db.commit()
                return self._build_empty_response(f"{event.name}에 등록된 질문이 없담! 운영진에게 문의해 주면 좋겠담..")

            await db.commit()
            return self._build_empty_response(f"알겠담! {event.name} 참여를 시작하겠담\n\n{steps[0].question_text}")

        # 3. 아무것도 해당하지 않으면 메뉴 반환
        events = await chatbot_repo.get_all_events(db)
        quick_replies = [
            {"label": "친바방 제출", "action": "message", "messageText": "친바방 제출"},
            {"label": "빠른 제출", "action": "message", "messageText": "빠른 제출"},
            {"label": "제출 내역", "action": "message", "messageText": "제출 내역"},
        ]
        for e in events:
            quick_replies.append({"label": e.name, "action": "message", "messageText": e.name})

        return self._build_empty_response(
            "무엇을 도와드릴깜? 아래 버튼을 눌러달람!",
            quick_replies=quick_replies,
        )

    async def process_chatbot_info(self, db: AsyncSession, request_data: ChatbotRequest, background_tasks: BackgroundTasks) -> ChatbotResponse:
        """
        질문 답변 시스템: 세션 정보를 바탕으로 질문을 순차적으로 던지고 답변을 저장함.
        """
        user_key = request_data.userRequest.get("user", {}).get("id")
        if not user_key:
            return self._build_empty_response("사용자 정보를 확인할 수 없담! 카카오 앱에서 다시 시도해달람")
        utterance = request_data.userRequest.get("utterance", "").strip()
        params = request_data.action.get("params", {})
        
        # 1. 세션 및 질문 목록 조회
        session = await chatbot_repo.get_or_create_session(db, user_key)
        current_data = session.data or {}
        active_event = current_data.get("active_event")

        if active_event:
            steps = await chatbot_repo.get_steps_by_event(db, active_event)
        else:
            steps = await chatbot_repo.get_steps(db)
        
        if not steps:
            return self._build_empty_response("질문 목록이 비어있담! 운영진에게 문의해 주면 좋겠담..")

        # 2. 특수 명령 처리
        if utterance == "사진을 전부 삭제하겠담":
            await chatbot_repo.clear_image_urls(db, user_key)
            await db.commit()
            return self._build_empty_response("보냈던 사진들을 모두 삭제했담! 사진을 다시 보내달람")

        if utterance == "모든 정보와 사진을 삭제하겠담":
            await chatbot_repo.delete_session(db, user_key)
            await db.commit()
            return self._build_empty_response("모든 정보와 사진을 삭제했담! 처음부터 다시 시작해달람")

        if utterance == "정보를 다시 입력하겠담!":
            await chatbot_repo.clear_data(db, user_key)
            await db.commit()
            return self._build_empty_response(f"사진은 남겨두고 정보만 초기화했담!\n\n{steps[0].question_text}")

        if utterance == "보낸 사진이 궁금하담!":
            all_image_urls = [url.strip() for url in (session.image_urls or "").split(",") if url.strip()]
            if not all_image_urls:
                return self._build_empty_response("아직 보낸 사진이 없담! 사진을 먼저 보내달람")
            return self._build_carousel_response(all_image_urls[:10], text="현재까지 받은 사진들이담!")

        if utterance == "입력한 정보를 확인하겠담":
            return await self._build_summary_response(db, user_key, session, current_data, steps, active_event)

        if utterance == "등록을 완료하겠담!":
            if not active_event:
                return self._build_empty_response("진행 중인 이벤트가 없담! 처음부터 다시 시작해달람")

            return await self._build_final_response(db, user_key, session, current_data, active_event, request_data, background_tasks)

        client_extra = request_data.action.get("clientExtra", {})
        if utterance == "이 사진을 삭제하겠담!" and "image_url" in client_extra:
            url_to_delete = client_extra["image_url"]
            await chatbot_repo.delete_image_url(db, user_key, url_to_delete)
            await db.commit()
            
            updated_session = await chatbot_repo.get_session(db, user_key)
            all_image_urls = [url.strip() for url in (updated_session.image_urls or "").split(",") if url.strip()]
            if not all_image_urls:
                return self._build_empty_response("모든 사진이 삭제되었담! 사진을 다시 보내달람")
            return self._build_carousel_response(all_image_urls[:10], text="해당 사진을 삭제했담! 현재 남은 사진들이담")

        # 3. 이미지 업로드 처리
        image_url_raw = params.get("kakaobot_image", "")
        if not image_url_raw and utterance.startswith("https://talk.kakaocdn.net/"):
            image_url_raw = utterance

        if image_url_raw:
            match = re.search(r"List\((.*?)\)", image_url_raw)
            if match:
                urls_content = match.group(1).strip()
                image_urls = [url.strip() for url in urls_content.split(",") if url.strip()]
            else:
                image_urls = [image_url_raw.strip()]

            for url in image_urls:
                if url:
                    await chatbot_repo.add_image_url(db, user_key, url)
            await db.commit()
            return await self._build_after_image_response(db, user_key, current_data, steps)

        # 4. 버튼 발화 처리
        if utterance == "사진을 더 보내겠담":
            return self._build_empty_response("알겠담! 사진을 보내달람")
        
        if utterance == "정보를 입력하겠담":
            if not current_data.get("__started__"):
                await chatbot_repo.update_data(db, user_key, "__started__", "true")
                await db.commit()
                return self._build_empty_response(f"알겠담! {steps[0].question_text}")
            
            next_step = self._get_next_step(current_data, steps)
            if next_step:
                return self._build_empty_response(next_step.question_text)

        # 5. 확인 프로세스
        confirming_field = current_data.get("__confirming__")
        if confirming_field:
            if utterance == "정확하담":
                await chatbot_repo.delete_data(db, user_key, "__confirming__")
                await db.commit()
                session = await chatbot_repo.get_session(db, user_key)
                current_data = session.data or {}
            elif utterance == "잘못 입력했담":
                target_q = next((s for s in steps if s.field_name == confirming_field), None)
                await chatbot_repo.delete_data(db, user_key, confirming_field)
                await chatbot_repo.delete_data(db, user_key, "__confirming__")
                await db.commit()
                re_question = target_q.question_text if target_q else "다시 입력해달람"
                return self._build_empty_response(f"알겠담! 다시 입력해달람\n\n{re_question}")
            else:
                val = current_data.get(confirming_field, "알 수 없음")
                quick_replies = [
                    {"label": "정확하담", "action": "message", "messageText": "정확하담"},
                    {"label": "잘못 입력했담", "action": "message", "messageText": "잘못 입력했담"}
                ]
                return self._build_empty_response(f"{confirming_field}: {val}\n이 정보가 맞담? 아래 버튼으로 알려달람!", quick_replies=quick_replies)

        # 6. 답변 저장 (제어용 발화가 아닐 때만 실행)
        target_step = self._get_next_step(current_data, steps)
        if target_step and utterance and utterance not in ["정확하담", "잘못 입력했담"]:
            await chatbot_repo.update_data(db, user_key, target_step.field_name, utterance)
            await chatbot_repo.update_data(db, user_key, "__confirming__", target_step.field_name)
            await db.commit()
            
            quick_replies = [
                {"label": "정확하담", "action": "message", "messageText": "정확하담"},
                {"label": "잘못 입력했담", "action": "message", "messageText": "잘못 입력했담"}
            ]
            return self._build_empty_response(
                f"{target_step.field_name}: {utterance}\n이 정보가 맞담? 아래 버튼으로 알려달람!",
                quick_replies=quick_replies
            )

        # 7. 최종 결과 및 다음 질문 생성
        updated_session = await chatbot_repo.get_session(db, user_key)
        updated_data = updated_session.data or {}
        next_step = self._get_next_step(updated_data, steps)
        
        if next_step:
            msg = f"알겠담! 이제 {next_step.question_text}" if utterance == "정확하담" else next_step.question_text
            return self._build_empty_response(msg)
        else:
            return await self._build_summary_response(db, user_key, updated_session, updated_data, steps, active_event, is_final=True)

    def _get_next_step(self, data: dict, steps: list) -> Any | None:
        for step in steps:
            if step.field_name not in data:
                return step
        return None

    async def _build_after_image_response(self, db: AsyncSession, user_key: str, current_data: dict, steps: list) -> ChatbotResponse:
        img_count_msg = "보내준 사진을 저장했담!"
        quick_replies = [
            {"messageText": "보낸 사진이 궁금하담!", "action": "message", "label": "보낸 사진이 궁금하담!"},
            {"messageText": "입력한 정보를 확인하겠담", "action": "message", "label": "정보 확인하기"}
        ]
        
        confirming_field = current_data.get("__confirming__")
        if confirming_field:
            val = current_data.get(confirming_field, "알 수 없음")
            quick_replies.extend([
                {"label": "정확하담", "action": "message", "messageText": "정확하담"},
                {"label": "잘못 입력했담", "action": "message", "messageText": "잘못 입력했담"}
            ])
            return self._build_empty_response(f"{img_count_msg}\n\n그건 그렇고, 입력한 {confirming_field}: {val}\n이 정보가 맞담? 아래 버튼으로 알려달람!", quick_replies=quick_replies)
        
        next_step = self._get_next_step(current_data, steps)
        re_question = next_step.question_text if next_step else "등록을 완료하려면 먼저 입력한 정보를 확인해야 한담"
        return self._build_empty_response(f"{img_count_msg}\n\n계속해서 답변해달람\n{re_question}", quick_replies=quick_replies)

    async def _build_summary_response(self, db: AsyncSession, user_key: str, session: Any, data: dict, steps: list, active_event: str | None, is_final: bool = False) -> ChatbotResponse:
        img_list = [url for url in (session.image_urls or "").split(",") if url.strip()]
        summary_parts = [f"[{active_event} 참여 정보]"] if active_event else ["[입력 정보 요약]"]
        for s in steps:
            if s.field_name in ["__started__", "active_event"]: continue
            summary_parts.append(f"- {s.field_name}: {data.get(s.field_name, '아직 알려주지 않았담..')}")
        
        summary = "\n".join(summary_parts)
        text = f"{summary}\n\n사진은 총 {len(img_list)}장이담"
        
        if is_final or not self._get_next_step(data, steps):
            return self._build_confirm_registration_response(f"모든 정보를 받았담!\n{text}\n\n등록 완료 버튼을 눌러줘람!")
        
        quick_replies = [
            {"messageText": "보낸 사진이 궁금하담!", "action": "message", "label": "보낸 사진이 궁금하담!"},
            {"messageText": "정보를 다시 입력하겠담!", "action": "message", "label": "정보를 다시 입력하겠담!"},
            {"messageText": "모든 정보와 사진을 삭제하겠담", "action": "message", "label": "모든 정보와 사진을 삭제하겠담"}
        ]
        return self._build_empty_response(f"현재까지 입력된 정보담!\n{text}\n\n계속해서 답변해달람", quick_replies=quick_replies)

    async def _build_final_response(self, db: AsyncSession, user_key: str, session: Any, data: dict, active_event: str, request_data: ChatbotRequest, background_tasks: BackgroundTasks) -> ChatbotResponse:
        """가이드에 맞춰 'useCallback: true'를 포함한 즉시 응답을 반환하고 백그라운드 작업을 시작합니다."""
        callback_url = request_data.userRequest.get("callbackUrl")
        
        # 실제 등록 로직에 필요한 데이터 추출
        filtered_data = {k: v for k, v in data.items() if not k.startswith("__") and k != "active_event"}
        img_list = [url.strip() for url in (session.image_urls or "").split(",") if url.strip()]

        # 백그라운드 태스크 등록
        background_tasks.add_task(
            self._process_registration_task,
            user_key,
            active_event,
            filtered_data,
            img_list,
            callback_url
        )

        # AI 챗봇 콜백 가이드에 따른 필수 응답 구조
        return ChatbotResponse(
            version="2.0",
            template={
                "outputs": [],
                "quickReplies": []
            },
            useCallback=True # 카카오 서버에 콜백을 사용할 것임을 알림
        )

    async def _process_registration_task(self, user_key: str, active_event: str, data: dict, img_list: list[str], callback_url: str | None):
        """백그라운드 등록 및 결과 전송"""
        try:
            # 새로운 DB 세션 생성
            async for db in get_chatbot_db():
                all_steps = await chatbot_repo.get_steps_by_event(db, active_event)
                all_field_names = [s.field_name for s in all_steps]

                # 구글 시트 연동
                await google_sheet_service.register_final_data(
                    active_event, 
                    data, 
                    img_list, 
                    all_field_names
                )

                # 성공 시 세션 삭제 및 커밋
                await chatbot_repo.delete_session(db, user_key)
                await db.commit()
                
                success_msg = f"성공적으로 {active_event}에 등록했담! 참여해줘서 고맙담~"
                await self._send_callback_response(callback_url, success_msg)
                break
                
        except Exception as e:
            print(f"[ERROR] Background registration failed for {user_key}: {e}")
            error_msg = "앗! 등록 중에 구글 서버와 통신 문제가 발생했담.. 잠시 후 다시 시도해달람!"
            await self._send_callback_response(callback_url, error_msg)

    async def _send_callback_response(self, callback_url: str | None, text: str):
        """가이드에 명시된 형식으로 콜백 URL에 POST 요청 전송"""
        if not callback_url:
            print("[WARNING] No callbackUrl provided.")
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 가이드에 따른 표준 스킬 응답 구조
            payload = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {"simpleText": {"text": text}}
                    ]
                }
            }
            try:
                # Content-Type은 자동으로 application/json으로 설정됨
                res = await client.post(callback_url, json=payload)
                if res.status_code not in [200, 201]:
                    print(f"[ERROR] Callback failed. Status: {res.status_code}, Response: {res.text}")
            except Exception as e:
                print(f"[ERROR] Callback Exception: {e}")

    def _build_confirm_registration_response(self, text: str) -> ChatbotResponse:
        quick_replies = [
            {"messageText": "보낸 사진이 궁금하담!", "action": "message", "label": "보낸 사진이 궁금하담!"},
            {"messageText": "등록을 완료하겠담!", "action": "message", "label": "최종 등록하기"},
            {"messageText": "정보를 다시 입력하겠담!", "action": "message", "label": "정보를 다시 입력하겠담!"},
            {"messageText": "모든 정보와 사진을 삭제하겠담", "action": "message", "label": "모든 정보와 사진을 삭제하겠담"}
        ]
        return self._build_empty_response(text, quick_replies=quick_replies)

    def _build_carousel_response(self, image_urls: list[str], text: str | None = None) -> ChatbotResponse:
        items = [{"title": "보내준 사진이담", "thumbnail": {"imageUrl": url}, "buttons": [{"action": "message", "label": "이 사진을 삭제하겠담!", "messageText": "이 사진을 삭제하겠담!", "extra": {"image_url": url}}]} for url in image_urls]
        quick_replies = [
            {"messageText": "사진을 더 보내겠담", "action": "message", "label": "사진을 더 보내겠담"},
            {"messageText": "정보를 입력하겠담", "action": "message", "label": "정보를 입력하겠담"},
            {"messageText": "사진을 전부 삭제하겠담", "action": "message", "label": "사진을 전부 삭제하겠담"}
        ]
        template = {"outputs": [{"carousel": {"type": "basicCard", "items": items}}, {"simpleText": {"text": text if text else f"현재까지 총 {len(image_urls)}장의 사진을 받았담!"}}, {"simpleText": {"text": "정보를 입력하려면 하단 버튼을 눌러줘람!"}}], "quickReplies": quick_replies}
        return ChatbotResponse(version="2.0", template=template)

    def _build_empty_response(self, text: str, quick_replies: list[dict] | None = None) -> ChatbotResponse:
        template = {"outputs": [{"simpleText": {"text": text}}], "quickReplies": quick_replies if quick_replies else []}
        return ChatbotResponse(version="2.0", template=template)


chatbot_service = ChatbotService()
