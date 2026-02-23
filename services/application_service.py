import os
import re

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application, ApplicationType, Member
from models.user import User
from repositories import application_repo
from schemas.application_dto import (
    MyApplicationResponse,
    NewApplicationCreate,
    RenewApplicationCreate,
)

APPLICATION_CURRENT_TERM = os.getenv("APPLICATION_CURRENT_TERM", "2025-2")
APPLICATION_ALLOW_EDIT_AFTER_SUBMIT = (
    os.getenv("APPLICATION_ALLOW_EDIT_AFTER_SUBMIT", "true").lower() == "true"
)


def _normalize_phone(phone_number: str) -> str:
    return re.sub(r"\D", "", phone_number)


def _validate_common(term: str, rule_agreed: bool) -> None:
    if term != APPLICATION_CURRENT_TERM:
        raise HTTPException(status_code=400, detail="현재 모집 학기가 아닙니다.")
    if not rule_agreed:
        raise HTTPException(status_code=400, detail="회칙 동의는 필수입니다.")


def _validate_new(data: NewApplicationCreate) -> None:
    if not data.student_card_confirmed:
        raise HTTPException(status_code=400, detail="학생증 제출 확인이 필요합니다.")
    if not data.privacy_agreed:
        raise HTTPException(status_code=400, detail="개인정보 수집 동의가 필요합니다.")


def _validate_renew(data: RenewApplicationCreate) -> None:
    if not data.fee_notice_ack:
        raise HTTPException(status_code=400, detail="회비 납부 안내 확인이 필요합니다.")


async def _upsert_member(db: AsyncSession, current_user: User, data) -> Member:
    normalized_phone = _normalize_phone(data.phone_number)

    existing_by_student = await application_repo.get_member_by_student_id(db, data.student_id)
    if existing_by_student and existing_by_student.user_id != current_user.id:
        raise HTTPException(status_code=409, detail="이미 등록된 학번입니다.")

    member = await application_repo.get_member_by_user_id(db, current_user.id)
    if not member:
        member = Member(
            user_id=current_user.id,
            name=data.name,
            student_id=data.student_id,
            department=data.department,
            phone_number=normalized_phone,
            gender=data.gender,
            academic_status=data.academic_status,
        )
        await application_repo.create_member(db, member)
    else:
        await application_repo.update_member(
            db,
            member,
            name=data.name,
            student_id=data.student_id,
            department=data.department,
            phone_number=normalized_phone,
            gender=data.gender,
            academic_status=data.academic_status,
        )

    return member


async def submit_new_application(
    db: AsyncSession,
    current_user: User,
    data: NewApplicationCreate,
) -> Application:
    _validate_common(data.term, data.rule_agreed)
    _validate_new(data)

    member = await _upsert_member(db, current_user, data)
    application = await application_repo.get_application_by_member_term_type(
        db, member.id, data.term, ApplicationType.NEW
    )

    payload = {
        "nickname": data.nickname,
        "job": data.job,
        "world": data.world,
        "level": data.level,
        "union_level": data.union_level,
        "rule_agreed": data.rule_agreed,
        "opening_party_intent": data.opening_party_intent,
        "interview_date_option": data.interview_date_option,
        "student_card_confirmed": data.student_card_confirmed,
        "privacy_agreed": data.privacy_agreed,
        "military_member_option": None,
        "free_chat_participation": None,
        "alliance_chat_participation": None,
        "fee_notice_ack": None,
        "reason_for_reregistration": None,
        "desired_event_style": None,
        "suggestions": None,
    }

    if not application:
        application = Application(
            member_id=member.id,
            term=data.term,
            application_type=ApplicationType.NEW,
            **payload,
        )
        await application_repo.create_application(db, application)
    else:
        if not APPLICATION_ALLOW_EDIT_AFTER_SUBMIT:
            raise HTTPException(status_code=403, detail="이미 제출한 신청서는 수정할 수 없습니다.")
        await application_repo.update_application(db, application, **payload)

    await db.commit()
    await db.refresh(application)
    return application


async def submit_renew_application(
    db: AsyncSession,
    current_user: User,
    data: RenewApplicationCreate,
) -> Application:
    _validate_common(data.term, data.rule_agreed)
    _validate_renew(data)

    member = await _upsert_member(db, current_user, data)
    application = await application_repo.get_application_by_member_term_type(
        db, member.id, data.term, ApplicationType.RENEW
    )

    payload = {
        "nickname": data.nickname,
        "job": data.job,
        "world": data.world,
        "level": data.level,
        "union_level": data.union_level,
        "rule_agreed": data.rule_agreed,
        "opening_party_intent": data.opening_party_intent,
        "interview_date_option": None,
        "student_card_confirmed": None,
        "privacy_agreed": None,
        "military_member_option": data.military_member_option,
        "free_chat_participation": data.free_chat_participation,
        "alliance_chat_participation": data.alliance_chat_participation,
        "fee_notice_ack": data.fee_notice_ack,
        "reason_for_reregistration": data.reason_for_reregistration,
        "desired_event_style": data.desired_event_style,
        "suggestions": data.suggestions,
    }

    if not application:
        application = Application(
            member_id=member.id,
            term=data.term,
            application_type=ApplicationType.RENEW,
            **payload,
        )
        await application_repo.create_application(db, application)
    else:
        if not APPLICATION_ALLOW_EDIT_AFTER_SUBMIT:
            raise HTTPException(status_code=403, detail="이미 제출한 신청서는 수정할 수 없습니다.")
        await application_repo.update_application(db, application, **payload)

    await db.commit()
    await db.refresh(application)
    return application


async def get_my_latest_application(db: AsyncSession, current_user: User) -> MyApplicationResponse:
    member = await application_repo.get_member_by_user_id(db, current_user.id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="신청 내역이 없습니다.")

    application = await application_repo.get_latest_application_by_member(db, member.id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="신청 내역이 없습니다.")

    new_detail = None
    renew_detail = None
    if application.application_type == ApplicationType.NEW:
        new_detail = {
            "interview_date_option": application.interview_date_option,
            "student_card_confirmed": application.student_card_confirmed,
            "privacy_agreed": application.privacy_agreed,
        }
    else:
        renew_detail = {
            "military_member_option": application.military_member_option,
            "free_chat_participation": application.free_chat_participation,
            "alliance_chat_participation": application.alliance_chat_participation,
            "fee_notice_ack": application.fee_notice_ack,
            "reason_for_reregistration": application.reason_for_reregistration,
            "desired_event_style": application.desired_event_style,
            "suggestions": application.suggestions,
        }

    return MyApplicationResponse(
        member={
            "name": member.name,
            "student_id": member.student_id,
            "department": member.department,
            "phone_number": member.phone_number,
            "gender": member.gender,
            "academic_status": member.academic_status,
        },
        application=application,
        new_detail=new_detail,
        renew_detail=renew_detail,
    )
