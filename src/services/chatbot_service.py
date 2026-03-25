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
        """사용자의 사진 데이터만 전체 삭제"""
        user_key = request_data.userRequest.get("user", {}).get("id", "unknown_user")
        await chatbot_repo.clear_image_urls(db, user_key)
        await db.commit()
        return self._build_empty_response("보냈던 사진들을 모두 삭제했담! 사진을 다시 보내달람.")

    async def reset_all_data(self, db: AsyncSession, request_data: ChatbotRequest) -> ChatbotResponse:
        """사용자의 모든 데이터(정보+사진) 삭제 및 초기화"""
        user_key = request_data.userRequest.get("user", {}).get("id", "unknown_user")
        await chatbot_repo.delete_session(db, user_key)
        await db.commit()
        return self._build_empty_response("모든 정보와 사진을 초기화했담! 처음부터 다시 시작해달람.")

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

        # [추가] 1-0. 보낸 이미지 확인하기 처리
        if utterance == "보낸 이미지 확인하기":
            saved_images = await chatbot_repo.get_all_by_user(db, user_key)
            if not saved_images:
                return self._build_empty_response("아직 보낸 사진이 없담! 사진을 먼저 보내달람.")
            
            all_image_urls = [img.image_url for img in saved_images]
            return self._build_carousel_response(all_image_urls[:10], text="현재까지 받은 사진들이담!")

        # [추가] 1-0. 정보 확인하기 처리
        if utterance == "정보 확인하기":
            img_list = [url for url in (session.image_urls or "").split(",") if url.strip()]
            summary_parts = []
            if active_event:
                summary_parts.append(f"**[{active_event} 참여 정보]**")
            for s in steps:
                if s.field_name == "__started__" or s.field_name == "active_event":
                    continue
                val = current_data.get(s.field_name, "미입력")
                summary_parts.append(f"- {s.field_name}: {val}")
            summary = "\n".join(summary_parts)
            
            # 1. 확인 중인 정보가 있는지 확인
            confirming_field = current_data.get("__confirming__")
            if confirming_field:
                val = current_data.get(confirming_field, "알 수 없음")
                label = "이름" if confirming_field == "name" else "학번" if confirming_field == "student_id" else confirming_field
                text = f"현재까지 입력된 정보담!\n\n{summary}\n\n사진은 총 {len(img_list)}장이담.\n\n그건 그렇고, 입력한 {label} '{val}'(이)가 맞담? 다시 알려줘람!"
                quick_replies = [
                    {"messageText": "보낸 이미지 확인하기", "action": "message", "label": "보낸 이미지 확인하기"},
                    {"messageText": "정보/사진 초기화하겠담", "action": "message", "label": "정보/사진 초기화"},
                    {"label": "맞다", "action": "message", "messageText": "맞다"},
                    {"label": "다시 입력하기", "action": "message", "messageText": "다시 입력하기"}
                ]
                return self._build_empty_response(text, quick_replies=quick_replies, contexts=[{"name": "infolist", "lifeSpan": 10}])

            # 2. 다음 질문이 있는지 확인
            next_step = None
            for step in steps:
                if step.field_name not in current_data:
                    next_step = step
                    break
            
            if next_step:
                text = f"현재까지 입력된 정보담!\n\n{summary}\n\n사진은 총 {len(img_list)}장이담.\n\n계속해서 답변해달람.\n{next_step.question_text}"
                quick_replies = [
                    {"messageText": "보낸 이미지 확인하기", "action": "message", "label": "보낸 이미지 확인하기"},
                    {"messageText": "정보/사진 초기화하겠담", "action": "message", "label": "정보/사진 초기화"}
                ]
                return self._build_empty_response(text, quick_replies=quick_replies, contexts=[{"name": "infolist", "lifeSpan": 10}])
            else:
                # 모든 정보 입력 완료 상태
                text = f"모든 정보를 받았담!\n{summary}\n\n현재까지 총 {len(img_list)}장의 사진이 있담. 등록을 완료해달람!"
                return self._build_final_response(text, contexts=[{"name": "infolist", "lifeSpan": 0}])

        # [추가] 1-0. 개별 이미지 삭제 처리 (clientExtra 데이터 활용)
        client_extra = request_data.action.get("clientExtra", {})
        if utterance == "이 사진을 삭제할게람!" and "image_url" in client_extra:
            url_to_delete = client_extra["image_url"]
            await chatbot_repo.delete_image_url(db, user_key, url_to_delete)
            await db.commit()
            
            saved_images = await chatbot_repo.get_all_by_user(db, user_key)
            if not saved_images:
                return self._build_empty_response("모든 사진이 삭제되었담! 사진을 다시 보내달람.")
            
            all_image_urls = [img.image_url for img in saved_images]
            return self._build_carousel_response(all_image_urls[:10], text="해당 사진을 삭제했담! 현재 남은 사진들이담.")

        # [추가] 1-0. 발화가 카카오톡 이미지 링크인 경우 이미지로 저장 처리
        if utterance.startswith("https://talk.kakaocdn.net/"):
            await chatbot_repo.add_image_url(db, user_key, utterance)
            await db.commit()
            
            # 현재 상태에 따라 적절한 재안내 문구 생성
            confirming_field = current_data.get("__confirming__")
            img_count_msg = "보내준 사진을 이미지로 저장했담!"
            quick_replies = [
                {"messageText": "보낸 이미지 확인하기", "action": "message", "label": "보낸 이미지 확인하기"},
                {"messageText": "정보 확인하기", "action": "message", "label": "정보 확인하기"}
            ]

            if confirming_field:
                val = current_data.get(confirming_field, "알 수 없음")
                label = "이름" if confirming_field == "name" else "학번" if confirming_field == "student_id" else confirming_field
                quick_replies.extend([
                    {"label": "맞다", "action": "message", "messageText": "맞다"},
                    {"label": "다시 입력하기", "action": "message", "messageText": "다시 입력하기"}
                ])
                return self._build_empty_response(
                    f"{img_count_msg}\n\n그건 그렇고, 입력한 {label} '{val}'(이)가 맞담? 다시 알려줘람!",
                    quick_replies=quick_replies,
                    contexts=[{"name": "infolist", "lifeSpan": 10}]
                )
            
            # 진행 중인 질문 찾기
            next_step = None
            for step in steps:
                if step.field_name not in current_data:
                    next_step = step
                    break
            
            re_question = next_step.question_text if next_step else "이미지 저장 완료! 이제 등록을 마무리해달람."
            return self._build_empty_response(
                f"{img_count_msg}\n\n계속해서 답변해달람.\n{re_question}",
                quick_replies=quick_replies,
                contexts=[{"name": "infolist", "lifeSpan": 10}]
            )

        # [추가] 1-0. 버튼 발화 처리
        if utterance == "사진을 더 보내겠담":
            return self._build_empty_response("알겠담! 사진을 보내달람. (한 번에 여러 장 보내도 된담!)")
        
        if utterance == "사진을 전부 삭제하겠담":
            return await self.delete_all_images(db, request_data)
        
        if utterance == "정보/사진 초기화하겠담":
            return await self.reset_all_data(db, request_data)

        # 1-1. 확인 프로세스 처리 (이름, 학번 등 중요 정보 확인)
        confirming_field = current_data.get("__confirming__")
        skip_storage = False # 답변 저장을 건너뛸지 여부

        if utterance == "정보를 입력하겠담":
            skip_storage = True
        
        if confirming_field and not skip_storage:
            if utterance == "맞다":
                # 확인 완료: 다음 단계로 진행 (저장은 건너뜀)
                await chatbot_repo.delete_data(db, user_key, "__confirming__")
                await db.commit()
                skip_storage = True
                # 갱신된 데이터로 세션 동기화
                session = await chatbot_repo.get_session(db, user_key)
                current_data = session.data or {}
            elif utterance == "다시 입력하기":
                # 다시 입력: 해당 필드 삭제 후 다시 해당 질문 던짐
                target_q = next((s for s in steps if s.field_name == confirming_field), None)
                await chatbot_repo.delete_data(db, user_key, confirming_field)
                await chatbot_repo.delete_data(db, user_key, "__confirming__")
                await db.commit()
                
                re_question = target_q.question_text if target_q else "다시 입력해달람."
                return self._build_empty_response(
                    f"알겠담! 다시 입력해달람.\n\n{re_question}",
                    contexts=[{"name": "infolist", "lifeSpan": 10}]
                )
            else:
                # 엉뚱한 입력 시 다시 확인 요청
                val = current_data.get(confirming_field, "알 수 없음")
                field_label = "이름" if confirming_field == "name" else "학번" if confirming_field == "student_id" else confirming_field
                
                quick_replies = [
                    {"label": "맞다", "action": "message", "messageText": "맞다"},
                    {"label": "다시 입력하기", "action": "message", "messageText": "다시 입력하기"}
                ]
                return self._build_empty_response(
                    f"입력한 {field_label} '{val}'(이)가 맞담? 아래 버튼으로 알려줘람!",
                    quick_replies=quick_replies,
                    contexts=[{"name": "infolist", "lifeSpan": 10}]
                )

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
        if not skip_storage:
            for step in steps:
                if step.field_name not in current_data:
                    target_step = step
                    break
            
            if target_step:
                # 현재 들어온 발화를 해당 필드에 저장
                await chatbot_repo.update_data(db, user_key, target_step.field_name, utterance)
                
                # [수정] 이름 또는 학번 입력 시에는 확인 프로세스 진입
                if target_step.field_name in ["name", "student_id"]:
                    await chatbot_repo.update_data(db, user_key, "__confirming__", target_step.field_name)
                    await db.commit()
                    
                    label = "이름" if target_step.field_name == "name" else "학번"
                    quick_replies = [
                        {"label": "맞다", "action": "message", "messageText": "맞다"},
                        {"label": "다시 입력하기", "action": "message", "messageText": "다시 입력하기"}
                    ]
                    return self._build_empty_response(
                        f"입력한 {label} '{utterance}'(이)가 맞담? (맞으면 [맞다], 틀리면 [다시 입력하기]를 눌러줘람!)",
                        quick_replies=quick_replies,
                        contexts=[{"name": "infolist", "lifeSpan": 10}]
                    )
                
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
            if utterance == "맞다":
                msg = f"알겠담! 이제 **{next_step.question_text}**"
            else:
                msg = f"'{utterance}'(이)가 맞담? 이제 **{next_step.question_text}**"
                
            return self._build_empty_response(
                msg,
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
            {"messageText": "보낸 이미지 확인하기", "action": "message", "label": "보낸 이미지 확인하기"},
            {"messageText": "정보/사진 초기화하겠담", "action": "message", "label": "정보/사진 초기화"},
            {"messageText": "등록을 완료하겠담", "action": "block", "blockId": "REGISTER_COMPLETE_BLOCK_ID", "label": "최종 등록하기"}
        ]
        return self._build_empty_response(text, quick_replies=quick_replies, contexts=contexts)

    def _build_carousel_response(self, image_urls: list[str], text: str | None = None) -> ChatbotResponse:
        items = []
        for url in image_urls:
            items.append({
                "title": "업로드된 사진",
                "thumbnail": {"imageUrl": url},
                "buttons": [
                    {
                        "action": "message",
                        "label": "이 사진 삭제",
                        "messageText": "이 사진을 삭제할게람!",
                        "extra": {"image_url": url}
                    }
                ]
            })
            
        quick_replies = [
            {"messageText": "사진을 더 보내겠담", "action": "message", "label": "사진 더 보내기"},
            {"messageText": "정보를 입력하겠담", "action": "message", "label": "정보 입력하기"},
            {"messageText": "사진을 전부 삭제하겠담", "action": "message", "label": "전체 삭제"}
        ]

        template = {
            "outputs": [
                {"carousel": {"type": "basicCard", "items": items}},
                {"simpleText": {"text": text if text else f"현재까지 총 {len(image_urls)}장의 사진을 받았담!"}},
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
