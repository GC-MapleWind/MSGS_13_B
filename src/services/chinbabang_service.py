import datetime
import os
import re

import httpx
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.database_chatbot import get_chatbot_db
from src.repositories.chatbot_repo import chatbot_repo
from src.schemas.chatbot_dto import ChatbotRequest, ChatbotResponse

STEP_CONFIRM_SUBMITTER = "confirm_submitter"
STEP_INPUT_NAME = "input_name"
STEP_INPUT_ID = "input_id"
STEP_INPUT_MEMBER_TYPE = "input_member_type"
STEP_SELECT_MODE = "select_mode"
STEP_PHOTO = "photo"
STEP_DATE = "date"
STEP_DATE_MANUAL = "date_manual"
STEP_TYPE = "type"
STEP_NEWBIE_NAMES = "newbie_names"
STEP_EXISTING_NAMES = "existing_names"
STEP_CONFIRM = "confirm"
STEP_QUICK_INPUT = "quick_input"

# [LEGACY] 인원수 기반 스텝 - 이름 기반으로 교체됨, 롤백 시 사용
STEP_NEWBIE = "newbie"
STEP_NEWBIE_MANUAL = "newbie_manual"
STEP_EXISTING = "existing"
STEP_EXISTING_MANUAL = "existing_manual"

ACTIVITY_TYPES = [
    "밥/술 먹기",
    "등산하기",
    "피시방 가기",
    "노래방 가기",
    "도서관에서 공부하기",
    "놀이공원 가기",
    "방탈출카페 가기",
    "보드게임카페 가기",
    "관광명소 방문하기",
    "기타",
]
MEMBER_TYPES = ["기존 회원", "신입 회원"]
COUNT_LABELS = ["0", "1", "2", "3", "4+"]

NAME_MIN_LEN = 2
NAME_MAX_LEN = 20
NAME_PATTERN = re.compile(r"^[가-힣a-zA-Z\s]+$")

STUDENT_ID_LEN = 9
STUDENT_ID_YEAR_MIN = 2000
STUDENT_ID_YEAR_MAX = 2030

MANUAL_COUNT_MAX = 50

BACK_TEXT = "뒤로가기"

STEP_BACK_MAP = {
    STEP_INPUT_ID: STEP_INPUT_NAME,
    STEP_INPUT_MEMBER_TYPE: STEP_INPUT_ID,
    STEP_SELECT_MODE: STEP_INPUT_MEMBER_TYPE,
    STEP_QUICK_INPUT: STEP_SELECT_MODE,
    STEP_PHOTO: STEP_SELECT_MODE,
    STEP_DATE: STEP_PHOTO,
    STEP_DATE_MANUAL: STEP_DATE,
    STEP_TYPE: STEP_DATE,
    STEP_NEWBIE_NAMES: STEP_TYPE,
    STEP_EXISTING_NAMES: STEP_NEWBIE_NAMES,
    STEP_CONFIRM: STEP_EXISTING_NAMES,
}


def _kst_today() -> datetime.date:
    """KST 기준 오늘 날짜를 반환합니다."""
    kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return kst_now.date()


class ChinbabangService:
    async def start(self, db: AsyncSession, user_key: str) -> ChatbotResponse:
        """친바방 제출 플로우 시작 - 제출자 프로필 유무에 따라 분기"""
        profile = await chatbot_repo.get_submitter_profile(db, user_key)

        if profile:
            await chatbot_repo.update_data(
                db, user_key, "__step__", STEP_CONFIRM_SUBMITTER
            )
            await db.commit()
            quick_replies = [
                {"label": "맞아요", "action": "message", "messageText": "맞아요"},
                {"label": "수정", "action": "message", "messageText": "수정"},
            ]
            member_label = f" [{profile.member_type}]" if profile.member_type else ""
            return self._build_response(
                f"제출자 정보를 확인하겠담!\n\n"
                f"이름: {profile.name}{member_label}\n"
                f"학번: {profile.student_id}\n\n"
                f"맞으면 바로 넘어가겠담!",
                quick_replies=quick_replies,
            )
        else:
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_INPUT_NAME)
            await db.commit()
            return self._build_response("처음이담! 이름을 알려달람 😊")

    async def quick_start(self, db: AsyncSession, user_key: str) -> ChatbotResponse:
        """빠른 제출 - 양식 한 번에 입력"""
        profile = await chatbot_repo.get_submitter_profile(db, user_key)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_QUICK_INPUT)
        await chatbot_repo.update_data(db, user_key, "_quick_mode", "true")
        await db.commit()

        today_str = _kst_today().strftime("%Y-%m-%d")
        if profile:
            member_label = profile.member_type or "기존 회원"
            example = (
                f"이름: {profile.name}\n"
                f"학번: {profile.student_id}\n"
                f"유형: {member_label}\n"
                f"날짜: {today_str}\n"
                f"활동: 밥/술 먹기\n"
                f"신입: 핑크빈, 예티\n"
                f"기존: 윌, 루시드"
            )
        else:
            example = (
                "이름: 홍길동\n"
                "학번: 202400001\n"
                "유형: 신입 회원\n"
                f"날짜: {today_str}\n"
                "활동: 밥/술 먹기\n"
                "신입: 핑크빈, 예티, 주황버섯\n"
                "기존: 윌, 루시드, 데미안"
            )

        activity_list = ", ".join(ACTIVITY_TYPES)

        guide = (
            "📋 빠른 제출 모드담!\n"
            "아래 양식을 복사해서 수정 후 보내달람!\n\n"
            f"📌 활동 종류:\n{activity_list}\n\n"
            f"📌 유형: 기존 회원, 신입 회원"
        )
        return ChatbotResponse(
            version="2.0",
            template={
                "outputs": [
                    {"simpleText": {"text": guide}},
                    {"simpleText": {"text": example}},
                ],
                "quickReplies": [
                    self._back_reply(),
                    {"label": "취소", "action": "message", "messageText": "취소"},
                ],
            },
        )

    async def process(
        self,
        db: AsyncSession,
        request_data: ChatbotRequest,
        background_tasks: BackgroundTasks,
    ) -> ChatbotResponse:
        user_key = request_data.userRequest.get("user", {}).get("id")
        if not user_key:
            return self._build_response("사용자 정보를 확인할 수 없담!")

        utterance = request_data.userRequest.get("utterance", "").strip()
        params = request_data.action.get("params", {})

        session = await chatbot_repo.get_or_create_session(db, user_key)
        data = session.data or {}
        step = data.get("__step__", STEP_INPUT_NAME)

        if utterance == "취소":
            await chatbot_repo.delete_session(db, user_key)
            await db.commit()
            return self._build_response(
                "제출을 취소했담!\n'친바방 제출'을 눌러 다시 시작할 수 있담!"
            )

        if utterance == BACK_TEXT:
            return await self._go_back(db, user_key, step)

        # STEP_PHOTO 이후 단계에서 도착한 사진도 저장
        STEPS_AFTER_PHOTO = {
            STEP_DATE,
            STEP_DATE_MANUAL,
            STEP_TYPE,
            STEP_NEWBIE_NAMES,
            STEP_EXISTING_NAMES,
            STEP_CONFIRM,
        }
        if step in STEPS_AFTER_PHOTO:
            late_urls = self._extract_image_urls(utterance, params)
            if late_urls:
                total = await self._save_images(db, user_key, late_urls)
                await db.commit()
                if step == STEP_CONFIRM:
                    return await self._build_confirm_response(
                        db,
                        user_key,
                        prefix=f"📸 사진 추가 저장! (총 {total}장)\n\n",
                    )
                return self._build_response(
                    f"📸 사진 추가 저장! (총 {total}장)\n이어서 진행해달람!",
                )

        if step == STEP_CONFIRM_SUBMITTER:
            return await self._handle_confirm_submitter(db, user_key, utterance)
        elif step == STEP_INPUT_NAME:
            return await self._handle_input_name(db, user_key, utterance)
        elif step == STEP_INPUT_ID:
            return await self._handle_input_id(db, user_key, utterance)
        elif step == STEP_INPUT_MEMBER_TYPE:
            return await self._handle_input_member_type(db, user_key, utterance)
        elif step == STEP_SELECT_MODE:
            return await self._handle_select_mode(db, user_key, utterance)
        elif step == STEP_PHOTO:
            return await self._handle_photo(db, user_key, utterance, params, session)
        elif step == STEP_DATE:
            return await self._handle_date(db, user_key, utterance)
        elif step == STEP_DATE_MANUAL:
            return await self._handle_date_manual(db, user_key, utterance)
        elif step == STEP_TYPE:
            return await self._handle_type(db, user_key, utterance)
        elif step == STEP_NEWBIE_NAMES:
            return await self._handle_newbie_names(db, user_key, utterance)
        elif step == STEP_EXISTING_NAMES:
            return await self._handle_existing_names(db, user_key, utterance)
        elif step == STEP_CONFIRM:
            return await self._handle_confirm(
                db, user_key, utterance, data, session, background_tasks, request_data
            )
        elif step == STEP_QUICK_INPUT:
            return await self._handle_quick_input(
                db, user_key, utterance, params, session
            )

        return self._build_response(
            "알 수 없는 단계담! '친바방 제출'로 다시 시작해달람!"
        )

    # ------------------------------------------------------------------ steps

    async def _handle_quick_input(
        self, db, user_key, utterance, params=None, session=None
    ):
        image_urls = self._extract_image_urls(utterance, params or {})
        if image_urls:
            if session is None:
                session = await chatbot_repo.get_or_create_session(db, user_key)
            total = await self._save_images(db, user_key, image_urls)
            await db.commit()
            return self._build_response(
                f"📸 사진 {total}장 저장했담!\n"
                "양식을 이어서 보내달람!\n\n"
                "⚠️ 묶어 보내기는 지원되지 않는담!\n"
                "여러 장이면 한 장씩 따로 보내달람!",
                quick_replies=[
                    {"label": "취소", "action": "message", "messageText": "취소"},
                ],
            )

        parsed = self._parse_quick_form(utterance)
        if isinstance(parsed, str):
            return self._build_response(
                f"❌ {parsed}\n\n양식을 다시 확인해서 보내달람!",
                quick_replies=[
                    {"label": "취소", "action": "message", "messageText": "취소"},
                ],
            )

        errors = self._validate_quick_fields(parsed)
        if errors:
            msg = "❌ 입력값에 문제가 있담!\n\n" + "\n".join(f"• {e}" for e in errors)
            return self._build_response(
                msg + "\n\n수정해서 다시 보내달람!",
                quick_replies=[
                    {"label": "취소", "action": "message", "messageText": "취소"},
                ],
            )

        name = parsed["이름"]
        sid = parsed["학번"]
        member_type = parsed["유형"]
        date_str = parsed["날짜"]
        activity = parsed["활동"]
        newbie_names = parsed["신입"]
        existing_names = parsed["기존"]

        newbie_str = ", ".join(newbie_names) if newbie_names else ""
        existing_str = ", ".join(existing_names) if existing_names else ""

        await chatbot_repo.upsert_submitter_profile(
            db, user_key, name, sid, member_type
        )
        await chatbot_repo.update_data(db, user_key, "activity_date", date_str)
        await chatbot_repo.update_data(db, user_key, "activity_type", activity)
        await chatbot_repo.update_data(db, user_key, "newbie_names", newbie_str)
        await chatbot_repo.update_data(
            db, user_key, "newbie_count", str(len(newbie_names))
        )
        await chatbot_repo.update_data(db, user_key, "existing_names", existing_str)
        await chatbot_repo.update_data(
            db, user_key, "existing_count", str(len(existing_names))
        )
        newbie_label = (
            f"{len(newbie_names)}명 ({newbie_str})" if newbie_names else "0명"
        )
        existing_label = (
            f"{len(existing_names)}명 ({existing_str})" if existing_names else "0명"
        )
        info_summary = (
            f"✅ 정보 입력 완료!\n\n"
            f"👤 {name}({sid}) [{member_type}]\n"
            f"📅 {date_str} | 🎯 {activity}\n"
            f"🌱 신입 {newbie_label} | 👥 기존 {existing_label}\n\n"
        )

        session = await chatbot_repo.get_session(db, user_key)
        photo_count = len(
            [u.strip() for u in (session.image_urls or "").split(",") if u.strip()]
        )
        if photo_count > 0:
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_CONFIRM)
            await db.commit()
            return await self._build_confirm_response(
                db,
                user_key,
                prefix=f"{info_summary}📸 사진 {photo_count}장 확인!\n\n",
            )

        await chatbot_repo.update_data(db, user_key, "__step__", STEP_PHOTO)
        await db.commit()
        return self._ask_photo(info_summary)

    @staticmethod
    def _parse_quick_form(text: str) -> dict | str:
        """양식 텍스트를 파싱합니다. 실패 시 오류 메시지 문자열을 반환합니다."""
        required_keys = ["이름", "학번", "유형", "날짜", "활동", "신입", "기존"]
        result = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or "─" in line:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if key in required_keys:
                    result[key] = value

        missing = [k for k in required_keys if k not in result]
        if missing:
            return f"다음 항목이 빠져 있담: {', '.join(missing)}"

        empty = [k for k, v in result.items() if not v]
        if empty:
            return f"다음 항목이 비어 있담: {', '.join(empty)}"

        return result

    def _validate_quick_fields(self, fields: dict) -> list[str]:
        """파싱된 양식 필드를 검증합니다. 오류 메시지 리스트를 반환합니다."""
        errors: list[str] = []

        name_err = self._validate_name(fields["이름"])
        if name_err:
            errors.append(name_err)

        sid_err = self._validate_student_id(fields["학번"])
        if sid_err:
            errors.append(sid_err)

        if fields["유형"] not in MEMBER_TYPES:
            errors.append(f"유형은 '{', '.join(MEMBER_TYPES)}' 중 하나여야 담")

        date_str = self._parse_date(fields["날짜"])
        if not date_str:
            errors.append("날짜 형식이 맞지 않담 (예: 2026-03-29 또는 3/29)")
        else:
            fields["날짜"] = date_str
            future_err = self._validate_date_not_future(date_str)
            if future_err:
                errors.append(future_err)

        for name_key in ("신입", "기존"):
            raw = fields[name_key]
            names, name_err = self._parse_name_list_static(raw)
            if name_err:
                errors.append(f"{name_key}: {name_err}")
            else:
                fields[name_key] = names

        return errors

    @staticmethod
    def _parse_name_list_static(text: str) -> tuple[list[str], str | None]:
        """콤마로 구분된 이름 목록을 파싱합니다 (static 버전)."""
        stripped = text.strip()
        if stripped in ("없음", "0", "0명"):
            return [], None

        raw_names = [n.strip() for n in stripped.split(",") if n.strip()]
        if not raw_names:
            return [], None

        for name in raw_names:
            if name and name[0] in ("=", "+", "-", "@", "\t", "\r", "|", "\\"):
                return [], f"'{name}'에 사용할 수 없는 문자가 있담"
            if len(name) < NAME_MIN_LEN:
                return [], f"'{name}'이(가) 너무 짧담 ({NAME_MIN_LEN}자 이상)"
            if len(name) > NAME_MAX_LEN:
                return [], f"'{name}'이(가) 너무 길담 ({NAME_MAX_LEN}자 이하)"
            if not NAME_PATTERN.match(name):
                return [], f"'{name}'에 한글/영문 외 문자가 있담"

        return raw_names, None

    async def _handle_select_mode(self, db, user_key, utterance):
        if utterance == "📋 빠른 제출":
            return await self.quick_start(db, user_key)

        if utterance == "💬 일반 제출":
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_PHOTO)
            await db.commit()
            return self._ask_photo()

        return self._ask_submit_mode("아래 버튼으로 선택해달람!")

    async def _handle_confirm_submitter(self, db, user_key, utterance):
        if utterance == "맞아요":
            profile = await chatbot_repo.get_submitter_profile(db, user_key)
            if not profile or not profile.member_type:
                await chatbot_repo.update_data(
                    db, user_key, "__step__", STEP_INPUT_MEMBER_TYPE
                )
                await db.commit()
                return self._ask_member_type("기존 회원인감, 신입 회원인감?\n\n")
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_SELECT_MODE)
            await db.commit()
            return self._ask_submit_mode()

        if utterance == "수정":
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_INPUT_NAME)
            await db.commit()
            return self._build_response("이름을 다시 입력해달람!")

        profile = await chatbot_repo.get_submitter_profile(db, user_key)
        quick_replies = [
            {"label": "맞아요", "action": "message", "messageText": "맞아요"},
            {"label": "수정", "action": "message", "messageText": "수정"},
        ]
        name = profile.name if profile else "?"
        sid = profile.student_id if profile else "?"
        member_label = (
            f" [{profile.member_type}]" if profile and profile.member_type else ""
        )
        return self._build_response(
            f"아래 버튼으로 답해달람!\n\n이름: {name}{member_label}\n학번: {sid}",
            quick_replies=quick_replies,
        )

    @staticmethod
    def _is_safe_input(value: str) -> bool:
        """수식 인젝션 및 특수 명령 입력 여부를 검사합니다."""
        if not value or not value.strip():
            return False
        return value.strip()[0] not in ("=", "+", "-", "@", "\t", "\r", "|", "\\")

    @staticmethod
    def _validate_name(name: str) -> str | None:
        """이름 정합성 검사. 오류가 있으면 안내 메시지를 반환합니다."""
        if len(name) < NAME_MIN_LEN:
            return f"이름이 너무 짧담!\n{NAME_MIN_LEN}자 이상 입력해달람 😊"
        if len(name) > NAME_MAX_LEN:
            return f"이름이 너무 길담!\n{NAME_MAX_LEN}자 이하로 입력해달람 😊"
        if not NAME_PATTERN.match(name):
            return "이름에는 한글 또는 영문만 사용할 수 있담!\n다시 입력해달람 😊"
        return None

    @staticmethod
    def _validate_student_id(sid: str) -> str | None:
        """학번 정합성 검사. 오류가 있으면 안내 메시지를 반환합니다."""
        if not sid.isdigit():
            return "학번은 숫자만 입력해달람! (예: 202400001)"
        if len(sid) != STUDENT_ID_LEN:
            return f"학번은 {STUDENT_ID_LEN}자리 숫자여야 담!\n(예: 202400001)"
        year = int(sid[:4])
        if year < STUDENT_ID_YEAR_MIN or year > STUDENT_ID_YEAR_MAX:
            return (
                f"학번 앞 4자리(입학연도)가 올바르지 않담!\n"
                f"{STUDENT_ID_YEAR_MIN}~{STUDENT_ID_YEAR_MAX} "
                f"범위여야 담 (예: 202400001)"
            )
        return None

    @staticmethod
    def _validate_date_not_future(date_str: str) -> str | None:
        """미래 날짜 검사. 오류가 있으면 안내 메시지를 반환합니다."""
        try:
            parsed = datetime.date.fromisoformat(date_str)
        except ValueError:
            return "날짜 형식이 맞지 않담!"
        today = _kst_today()
        if parsed > today:
            return (
                f"미래 날짜는 선택할 수 없담!\n"
                f"오늘({today.strftime('%Y-%m-%d')}) 이전 "
                f"날짜를 입력해달람 😊"
            )
        return None

    @staticmethod
    def _validate_manual_count(value: str) -> str | None:
        """수동 입력 인원수 정합성 검사. 오류가 있으면 안내 메시지를 반환합니다."""
        if not value.isdigit():
            return "숫자만 입력해달람!"
        count = int(value)
        if count < 0:
            return "인원 수는 0 이상이어야 담!"
        if count > MANUAL_COUNT_MAX:
            return f"인원 수가 너무 크담!\n{MANUAL_COUNT_MAX}명 이하로 입력해달람 😊"
        return None

    async def _handle_input_name(self, db, user_key, utterance):
        if not self._is_safe_input(utterance):
            return self._build_response(
                "이름에 사용할 수 없는 문자가 포함돼 있담!\n이름만 입력해달람 😊"
            )
        name = utterance.strip()

        name_error = self._validate_name(name)
        if name_error:
            return self._build_response(name_error)

        await chatbot_repo.update_data(db, user_key, "_name_tmp", name)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_INPUT_ID)
        await db.commit()
        return self._build_response(
            f"'{name}'님, 반갑담! 학번을 입력해달람!\n(예: 202400001)",
            quick_replies=[self._back_reply()],
        )

    async def _handle_input_id(self, db, user_key, utterance):
        sid = utterance.strip()

        sid_error = self._validate_student_id(sid)
        if sid_error:
            return self._build_response(sid_error)

        session = await chatbot_repo.get_session(db, user_key)
        data = session.data or {}
        name = data.get("_name_tmp", "")

        await chatbot_repo.upsert_submitter_profile(db, user_key, name, sid)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_INPUT_MEMBER_TYPE)
        await db.commit()
        return self._ask_member_type(f"이름: {name} / 학번: {sid} 저장했담!\n\n")

    async def _handle_input_member_type(self, db, user_key, utterance):
        if utterance not in MEMBER_TYPES:
            return self._ask_member_type("아래 버튼으로 선택해달람!")

        await chatbot_repo.update_member_type(db, user_key, utterance)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_SELECT_MODE)
        await db.commit()
        return self._ask_submit_mode(f"[{utterance}]으로 등록했담!\n\n")

    def _extract_image_urls(self, utterance: str, params: dict) -> list[str]:
        """요청에서 이미지 URL을 추출합니다."""
        raw = params.get("kakaobot_image", "")
        if not raw and utterance.startswith("https://talk.kakaocdn.net/"):
            raw = utterance
        if not raw:
            return []

        match = re.search(r"List\((.*?)\)", raw)
        if match:
            return [u.strip() for u in match.group(1).split(",") if u.strip()]
        return [raw.strip()] if raw.strip() else []

    async def _save_images(self, db, user_key: str, urls: list[str]) -> int:
        """이미지 URL들을 세션에 저장하고 총 사진 수를 반환합니다."""
        for url in urls:
            if url:
                await chatbot_repo.add_image_url(db, user_key, url)
        await db.flush()

        fresh = await chatbot_repo.get_session(db, user_key)
        all_urls = [u.strip() for u in (fresh.image_urls or "").split(",") if u.strip()]
        return len(all_urls)

    async def _handle_photo(self, db, user_key, utterance, params, session):
        image_urls = self._extract_image_urls(utterance, params)

        if image_urls:
            total = await self._save_images(db, user_key, image_urls)

            data = session.data or {}
            is_quick = data.get("_quick_mode") == "true"

            if is_quick:
                await chatbot_repo.update_data(db, user_key, "__step__", STEP_CONFIRM)
                await db.commit()
                return await self._build_confirm_response(
                    db,
                    user_key,
                    prefix=f"사진 {total}장을 받았담! 📸\n\n",
                )

            await chatbot_repo.update_data(db, user_key, "__step__", STEP_DATE)
            await db.commit()
            return self._ask_date(
                f"사진 {total}장을 받았담! 📸\n\n활동 날짜를 선택해달람!"
            )

        return self._ask_photo()

    async def _handle_date(self, db, user_key, utterance):
        kst_today = datetime.datetime.utcnow() + datetime.timedelta(hours=9)

        if utterance == "오늘":
            date_str = kst_today.strftime("%Y-%m-%d")
        elif utterance == "어제":
            date_str = (kst_today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        elif utterance == "직접 입력":
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_DATE_MANUAL)
            await db.commit()
            return self._build_response(
                "날짜를 입력해달람!\n(예: 2026-03-29 또는 3/29)",
                quick_replies=[self._back_reply()],
            )
        else:
            return self._ask_date("아래 버튼으로 날짜를 선택해달람!")

        await chatbot_repo.update_data(db, user_key, "activity_date", date_str)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_TYPE)
        await db.commit()
        return self._ask_type(f"📅 날짜: {date_str}\n\n어떤 활동이었남?")

    async def _handle_date_manual(self, db, user_key, utterance):
        date_str = self._parse_date(utterance.strip())
        if not date_str:
            return self._build_response(
                "날짜 형식이 맞지 않담!\n(예: 2026-03-29 또는 3/29)"
            )

        future_error = self._validate_date_not_future(date_str)
        if future_error:
            return self._build_response(future_error)

        await chatbot_repo.update_data(db, user_key, "activity_date", date_str)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_TYPE)
        await db.commit()
        return self._ask_type(f"📅 날짜: {date_str}\n\n어떤 활동이었남?")

    async def _handle_type(self, db, user_key, utterance):
        if not utterance.strip():
            return self._ask_type("활동 종류를 입력하거나 선택해달람!")

        await chatbot_repo.update_data(db, user_key, "activity_type", utterance)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_NEWBIE_NAMES)
        await db.commit()
        return self._build_response(
            "함께한 신입 회원 이름을 입력해달람!\n"
            "(콤마로 구분, 없으면 '없음')\n\n"
            "예: 핑크빈, 예티, 주황버섯",
            quick_replies=[self._back_reply()],
        )

    # ------------------------------------------------- name-based input

    async def _handle_newbie_names(self, db, user_key, utterance):
        names, error = self._parse_name_list(utterance)
        if error:
            return self._build_response(
                f"❌ {error}\n\n"
                "신입 회원 이름을 콤마(,)로 구분해서 입력해달람!\n"
                "(없으면 '없음' 입력)",
                quick_replies=[self._back_reply()],
            )

        count = len(names)
        names_str = ", ".join(names) if names else ""
        await chatbot_repo.update_data(db, user_key, "newbie_names", names_str)
        await chatbot_repo.update_data(db, user_key, "newbie_count", str(count))
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_EXISTING_NAMES)
        await db.commit()

        if names:
            prefix = f"🌱 신입 {count}명: {names_str}\n\n"
        else:
            prefix = "🌱 신입 0명\n\n"
        return self._build_response(
            f"{prefix}이번엔 함께한 기존 회원 이름을 입력해달람!\n"
            "(콤마로 구분, 없으면 '없음')",
            quick_replies=[self._back_reply()],
        )

    async def _handle_existing_names(self, db, user_key, utterance):
        names, error = self._parse_name_list(utterance)
        if error:
            return self._build_response(
                f"❌ {error}\n\n"
                "기존 회원 이름을 콤마(,)로 구분해서 입력해달람!\n"
                "(없으면 '없음' 입력)",
                quick_replies=[self._back_reply()],
            )

        count = len(names)
        names_str = ", ".join(names) if names else ""
        await chatbot_repo.update_data(db, user_key, "existing_names", names_str)
        await chatbot_repo.update_data(db, user_key, "existing_count", str(count))
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_CONFIRM)
        await db.commit()
        return await self._build_confirm_response(db, user_key)

    def _parse_name_list(self, text: str) -> tuple[list[str], str | None]:
        """콤마로 구분된 이름 목록을 파싱합니다. (names, error) 튜플 반환."""
        return self._parse_name_list_static(text)

    # ---------------------------------- [LEGACY] 인원수 기반 핸들러 (롤백 시 사용)
    # 이름 기반 입력으로 교체됨.
    # 롤백하려면: process()에서 STEP_NEWBIE_NAMES → STEP_NEWBIE,
    #   STEP_EXISTING_NAMES → STEP_EXISTING 으로 변경하고
    #   _handle_type에서 STEP_NEWBIE_NAMES → STEP_NEWBIE 로 변경

    async def _legacy_handle_newbie(self, db, user_key, utterance):
        if utterance == "4+":
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_NEWBIE_MANUAL)
            await db.commit()
            return self._build_response(
                "신입 인원 수를 직접 입력해달람 (숫자만)",
                quick_replies=[self._back_reply()],
            )

        if utterance in ["0", "1", "2", "3"]:
            await chatbot_repo.update_data(db, user_key, "newbie_count", utterance)
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_EXISTING)
            await db.commit()
            return self._ask_count("기존 회원이 몇 명이었담?")

        return self._ask_count("아래 버튼으로 신입 인원을 선택해달람!")

    async def _legacy_handle_newbie_manual(self, db, user_key, utterance):
        count_error = self._validate_manual_count(utterance)
        if count_error:
            return self._build_response(count_error)

        await chatbot_repo.update_data(db, user_key, "newbie_count", utterance)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_EXISTING)
        await db.commit()
        return self._ask_count("기존 회원이 몇 명이었담?")

    async def _legacy_handle_existing(self, db, user_key, utterance):
        if utterance == "4+":
            await chatbot_repo.update_data(
                db, user_key, "__step__", STEP_EXISTING_MANUAL
            )
            await db.commit()
            return self._build_response(
                "기존 회원 수를 직접 입력해달람 (숫자만)",
                quick_replies=[self._back_reply()],
            )

        if utterance in ["0", "1", "2", "3"]:
            await chatbot_repo.update_data(db, user_key, "existing_count", utterance)
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_CONFIRM)
            await db.commit()
            return await self._build_confirm_response(db, user_key)

        return self._ask_count("아래 버튼으로 기존 회원 수를 선택해달람!")

    async def _legacy_handle_existing_manual(self, db, user_key, utterance):
        count_error = self._validate_manual_count(utterance)
        if count_error:
            return self._build_response(count_error)

        await chatbot_repo.update_data(db, user_key, "existing_count", utterance)
        await chatbot_repo.update_data(db, user_key, "__step__", STEP_CONFIRM)
        await db.commit()
        return await self._build_confirm_response(db, user_key)

    async def _handle_confirm(
        self, db, user_key, utterance, data, session, background_tasks, request_data
    ):
        if utterance == "✅ 제출":
            profile = await chatbot_repo.get_submitter_profile(db, user_key)
            photo_urls = [
                u.strip() for u in (session.image_urls or "").split(",") if u.strip()
            ]
            callback_url = request_data.userRequest.get("callbackUrl")

            newbie_count = int(data.get("newbie_count", 0))
            existing_count = int(data.get("existing_count", 0))
            member_type = profile.member_type if profile else "기존 회원"
            if member_type == "신입 회원":
                score = newbie_count + existing_count
            else:
                score = newbie_count

            submission_data = {
                "user_key": user_key,
                "submitter_name": profile.name if profile else "?",
                "submitter_student_id": profile.student_id if profile else "?",
                "photo_urls": ",".join(photo_urls),
                "activity_date": data.get("activity_date", ""),
                "activity_type": data.get("activity_type", ""),
                "newbie_count": newbie_count,
                "existing_count": existing_count,
                "newbie_names": data.get("newbie_names", ""),
                "existing_names": data.get("existing_names", ""),
                "score": score,
            }

            submission = await chatbot_repo.create_submission(db, **submission_data)
            submission_id = submission.id
            await chatbot_repo.delete_session(db, user_key)
            await db.commit()

            background_tasks.add_task(
                self._process_submission_task,
                submission_id,
                submission_data,
                photo_urls,
                callback_url,
            )

            return ChatbotResponse(
                version="2.0",
                template={"outputs": [], "quickReplies": []},
                useCallback=True,
            )

        is_quick = data.get("_quick_mode") == "true"

        if utterance == "🔄 처음부터 다시" and not is_quick:
            await chatbot_repo.delete_session(db, user_key)
            await chatbot_repo.get_or_create_session(db, user_key)
            await chatbot_repo.update_data(db, user_key, "active_event", "친바방제출")
            await chatbot_repo.update_data(db, user_key, "__started__", "true")
            await db.commit()
            return await self.start(db, user_key)

        if is_quick and utterance == "📝 양식 수정":
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_QUICK_INPUT)
            await db.commit()
            return await self.quick_start(db, user_key)

        if is_quick and utterance == "📸 사진 수정":
            await chatbot_repo.update_data(db, user_key, "__step__", STEP_PHOTO)
            session.image_urls = ""
            await db.commit()
            return self._ask_photo("사진을 다시 올려달람!\n\n")

        if utterance == "취소":
            await chatbot_repo.delete_session(db, user_key)
            await db.commit()
            return self._build_response("제출을 취소했담!")

        return await self._build_confirm_response(db, user_key)

    # ------------------------------------------------------------------ back

    @staticmethod
    def _back_reply() -> dict:
        return {
            "label": "◀ 뒤로가기",
            "action": "message",
            "messageText": BACK_TEXT,
        }

    async def _go_back(self, db, user_key, current_step) -> ChatbotResponse:
        session = await chatbot_repo.get_session(db, user_key)
        data = session.data or {} if session else {}
        is_quick = data.get("_quick_mode") == "true"

        if is_quick and current_step == STEP_PHOTO:
            prev_step = STEP_QUICK_INPUT
        elif is_quick and current_step == STEP_CONFIRM:
            prev_step = STEP_PHOTO
        else:
            prev_step = STEP_BACK_MAP.get(current_step)

        if not prev_step:
            return self._build_response("더 이상 뒤로 갈 수 없담! 계속 진행해달람 😊")

        await chatbot_repo.update_data(db, user_key, "__step__", prev_step)
        await db.commit()
        return await self._prompt_for_step(db, user_key, prev_step)

    async def _prompt_for_step(self, db, user_key, step) -> ChatbotResponse:
        if step == STEP_CONFIRM_SUBMITTER:
            profile = await chatbot_repo.get_submitter_profile(db, user_key)
            quick_replies = [
                {"label": "맞아요", "action": "message", "messageText": "맞아요"},
                {"label": "수정", "action": "message", "messageText": "수정"},
            ]
            member_label = (
                f" [{profile.member_type}]" if profile and profile.member_type else ""
            )
            name = profile.name if profile else "?"
            sid = profile.student_id if profile else "?"
            return self._build_response(
                f"제출자 정보를 확인하겠담!\n\n"
                f"이름: {name}{member_label}\n"
                f"학번: {sid}\n\n"
                f"맞으면 바로 넘어가겠담!",
                quick_replies=quick_replies,
            )
        if step == STEP_INPUT_NAME:
            return self._build_response("이름을 입력해달람 😊")
        if step == STEP_INPUT_ID:
            return self._build_response(
                "학번을 입력해달람!\n(예: 202400001)",
                quick_replies=[self._back_reply()],
            )
        if step == STEP_INPUT_MEMBER_TYPE:
            return self._ask_member_type()
        if step == STEP_SELECT_MODE:
            return self._ask_submit_mode()
        if step == STEP_PHOTO:
            return self._ask_photo()
        if step == STEP_DATE:
            return self._ask_date()
        if step == STEP_DATE_MANUAL:
            return self._build_response(
                "날짜를 입력해달람!\n(예: 2026-03-29 또는 3/29)",
                quick_replies=[self._back_reply()],
            )
        if step == STEP_TYPE:
            return self._ask_type()
        if step == STEP_NEWBIE_NAMES:
            return self._build_response(
                "함께한 신입 회원 이름을 입력해달람!\n"
                "(콤마로 구분, 없으면 '없음')\n\n"
                "예: 김철수, 박영희, 이민수",
                quick_replies=[self._back_reply()],
            )
        if step == STEP_EXISTING_NAMES:
            return self._build_response(
                "함께한 기존 회원 이름을 입력해달람!\n(콤마로 구분, 없으면 '없음')",
                quick_replies=[self._back_reply()],
            )
        if step == STEP_CONFIRM:
            return await self._build_confirm_response(db, user_key)
        if step == STEP_QUICK_INPUT:
            return await self.quick_start(db, user_key)
        return self._build_response(
            "알 수 없는 단계담! '친바방 제출'로 다시 시작해달람!"
        )

    # ------------------------------------------------------------------ helpers

    async def _build_confirm_response(
        self, db, user_key, prefix: str = ""
    ) -> ChatbotResponse:
        session = await chatbot_repo.get_session(db, user_key)
        data = session.data or {}
        profile = await chatbot_repo.get_submitter_profile(db, user_key)

        photo_count = len(
            [u for u in (session.image_urls or "").split(",") if u.strip()]
        )
        sid_suffix = profile.student_id if profile else "?"

        newbie_count = int(data.get("newbie_count", 0))
        existing_count = int(data.get("existing_count", 0))
        member_type = profile.member_type if profile else "기존 회원"
        if member_type == "신입 회원":
            score = newbie_count + existing_count
        else:
            score = newbie_count

        past_total = await chatbot_repo.get_total_score(db, user_key)

        newbie_names = data.get("newbie_names", "")
        existing_names = data.get("existing_names", "")
        newbie_label = (
            f"{newbie_count}명 ({newbie_names})"
            if newbie_names
            else f"{newbie_count}명"
        )
        existing_label = (
            f"{existing_count}명 ({existing_names})"
            if existing_names
            else f"{existing_count}명"
        )

        summary = (
            f"{prefix}아래 내용으로 제출하겠담?\n\n"
            f"👤 제출자: {profile.name if profile else '?'}({sid_suffix}) [{member_type}]\n"
            f"📸 사진: {photo_count}장\n"
            f"📅 날짜: {data.get('activity_date', '?')}\n"
            f"🎯 활동: {data.get('activity_type', '?')}\n"
            f"🌱 신입: {newbie_label}\n"
            f"👥 기존회원: {existing_label}\n"
            f"⭐ 이번 점수: {score}점\n"
            f"📊 제출 후 누적: {past_total + score}점"
        )

        is_quick = data.get("_quick_mode") == "true"
        if is_quick:
            quick_replies = [
                {"label": "✅ 제출", "action": "message", "messageText": "✅ 제출"},
                {
                    "label": "📝 양식 수정",
                    "action": "message",
                    "messageText": "📝 양식 수정",
                },
                {
                    "label": "📸 사진 수정",
                    "action": "message",
                    "messageText": "📸 사진 수정",
                },
                {"label": "취소", "action": "message", "messageText": "취소"},
            ]
        else:
            quick_replies = [
                {"label": "✅ 제출", "action": "message", "messageText": "✅ 제출"},
                self._back_reply(),
                {
                    "label": "🔄 처음부터 다시",
                    "action": "message",
                    "messageText": "🔄 처음부터 다시",
                },
                {"label": "취소", "action": "message", "messageText": "취소"},
            ]
        return self._build_response(summary, quick_replies=quick_replies)

    async def show_history(self, db: AsyncSession, user_key: str) -> ChatbotResponse:
        submissions = await chatbot_repo.get_submissions_by_user(db, user_key, limit=5)

        quick_replies = [
            {"label": "친바방 제출", "action": "message", "messageText": "친바방 제출"}
        ]

        if not submissions:
            return self._build_response(
                "아직 제출 내역이 없담!\n'친바방 제출'로 첫 제출을 해달람 😊",
                quick_replies=quick_replies,
            )

        total_score = await chatbot_repo.get_total_score(db, user_key)

        lines = [f"📊 누적 점수: {total_score}점\n", "📋 최근 제출 내역 (최대 5건)\n"]
        for s in submissions:
            lines.append(
                f"• {s.activity_date} | {s.activity_type} | "
                f"신입 {s.newbie_count}+기존 {s.existing_count} → {s.score}점"
            )

        return self._build_response("\n".join(lines), quick_replies=quick_replies)

    async def _process_submission_task(
        self,
        submission_id: int,
        submission_data: dict,
        photo_urls: list[str],
        callback_url: str | None,
    ):
        try:
            # 1. CDN에서 다운로드 → 서버 로컬 저장
            local_paths = await self._download_photos_locally(
                photo_urls,
                submission_data.get("activity_date", "unknown"),
                submission_data.get("submitter_name", "unknown"),
            )

            # 2. DB의 photo_urls를 로컬 경로로 업데이트 + 누적 점수 조회
            total_score = 0
            async for db in get_chatbot_db():
                await chatbot_repo.update_submission_photo_urls(
                    db, submission_id, ",".join(local_paths)
                )
                await db.commit()
                total_score = await chatbot_repo.get_total_score(
                    db, submission_data["user_key"]
                )
                break

            # 3. Google Drive 동기화 (열람용, 실패해도 제출 완료 처리)
            try:
                from src.services.google_sheet_service import google_sheet_service

                if google_sheet_service.creds:
                    await google_sheet_service.register_chinbabang_submission(
                        submission_data, local_paths, submission_id=submission_id
                    )
            except Exception as drive_err:
                print(
                    f"[WARN] Google Drive sync failed (submission saved locally): {drive_err}"
                )

            msg = (
                f"✅ 제출 완료!\n\n"
                f"⭐ 이번 점수: {submission_data.get('score', 0)}점\n"
                f"📊 누적 점수: {total_score}점\n\n"
                f"다음부터는 제출자 정보를 다시 입력하지 않아도 된담 😊"
            )
            await self._send_callback(callback_url, msg)
        except Exception as e:
            print(f"[ERROR] Chinbabang submission task failed: {e}")
            await self._send_callback(
                callback_url,
                "앗! 제출은 완료됐지만 사진 저장 중 오류가 발생했담! 운영진에게 문의해달람!",
            )

    async def _download_photos_locally(
        self,
        photo_urls: list[str],
        activity_date: str,
        submitter_name: str,
    ) -> list[str]:
        """CDN URL에서 사진을 다운로드해 서버 로컬에 저장합니다."""
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        timestamp = int(datetime.datetime.utcnow().timestamp())
        save_dir = os.path.join(
            base_dir,
            "media",
            "chinbabang",
            activity_date,
            f"{submitter_name}_{timestamp}",
        )
        os.makedirs(save_dir, exist_ok=True)

        local_paths: list[str] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, url in enumerate(photo_urls):
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        filename = f"photo_{i + 1:03d}.jpg"
                        path = os.path.join(save_dir, filename)
                        with open(path, "wb") as f:
                            f.write(resp.content)
                        local_paths.append(path)
                    else:
                        print(
                            f"[WARN] Photo download failed (HTTP {resp.status_code}): {url}"
                        )
                except Exception as e:
                    print(f"[ERROR] Photo download error: {e}")
        return local_paths

    async def _send_callback(self, callback_url: str | None, text: str):
        if not callback_url:
            return
        payload = {
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": text}}]},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                await client.post(callback_url, json=payload)
            except Exception as e:
                print(f"[ERROR] Callback failed: {e}")

    # ------------------------------------------------------------------ builders

    def _ask_submit_mode(self, prefix: str = "") -> ChatbotResponse:
        text = (
            f"{prefix}제출 방식을 선택해달람!\n\n"
            "📋 빠른 제출 — 양식 한 번에 입력\n"
            "💬 일반 제출 — 대화형으로 하나씩 입력"
        )
        quick_replies = [
            {
                "label": "📋 빠른 제출",
                "action": "message",
                "messageText": "📋 빠른 제출",
            },
            {
                "label": "💬 일반 제출",
                "action": "message",
                "messageText": "💬 일반 제출",
            },
            self._back_reply(),
        ]
        return self._build_response(text, quick_replies=quick_replies)

    def _ask_photo(self, prefix: str = "") -> ChatbotResponse:
        text = (
            f"{prefix}📸 인증 사진을 올려달람!\n"
            "사진을 보내면 자동으로 다음 단계로 넘어가겠담!\n\n"
            "⚠️ 묶어 보내기는 지원되지 않는담!\n"
            "여러 장이면 한 장씩 따로 보내달람!"
        )
        return self._build_response(
            text,
            quick_replies=[
                self._back_reply(),
                {"label": "취소", "action": "message", "messageText": "취소"},
            ],
        )

    def _ask_member_type(self, prefix: str = "") -> ChatbotResponse:
        text = f"{prefix}기존 회원인감, 신입 회원인감?"
        quick_replies = [
            {"label": t, "action": "message", "messageText": t} for t in MEMBER_TYPES
        ]
        quick_replies.append(self._back_reply())
        return self._build_response(text, quick_replies=quick_replies)

    def _ask_date(self, text: str = "활동 날짜를 선택해달람!") -> ChatbotResponse:
        quick_replies = [
            {"label": "오늘", "action": "message", "messageText": "오늘"},
            {"label": "어제", "action": "message", "messageText": "어제"},
            {"label": "직접 입력", "action": "message", "messageText": "직접 입력"},
            self._back_reply(),
        ]
        return self._build_response(text, quick_replies=quick_replies)

    def _ask_type(
        self, text: str = "어떤 활동이었담?\n버튼을 누르거나 직접 입력해도 된담!"
    ) -> ChatbotResponse:
        quick_replies = [
            {"label": t, "action": "message", "messageText": t} for t in ACTIVITY_TYPES
        ]
        quick_replies.append(self._back_reply())
        return self._build_response(text, quick_replies=quick_replies)

    def _ask_count(self, text: str) -> ChatbotResponse:
        quick_replies = [
            {"label": c, "action": "message", "messageText": c} for c in COUNT_LABELS
        ]
        quick_replies.append(self._back_reply())
        return self._build_response(text, quick_replies=quick_replies)

    def _build_response(
        self, text: str, quick_replies: list | None = None
    ) -> ChatbotResponse:
        return ChatbotResponse(
            version="2.0",
            template={
                "outputs": [{"simpleText": {"text": text}}],
                "quickReplies": quick_replies or [],
            },
        )

    @staticmethod
    def _parse_date(s: str) -> str | None:
        if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", s):
            parts = s.split("-")
            try:
                return datetime.date(
                    int(parts[0]), int(parts[1]), int(parts[2])
                ).strftime("%Y-%m-%d")
            except ValueError:
                return None
        if re.match(r"^\d{1,2}/\d{1,2}$", s):
            parts = s.split("/")
            try:
                year = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).year
                return datetime.date(year, int(parts[0]), int(parts[1])).strftime(
                    "%Y-%m-%d"
                )
            except ValueError:
                return None
        return None


chinbabang_service = ChinbabangService()
