import os
import secrets

from fastapi import FastAPI
from sqladmin.authentication import AuthenticationBackend
from sqladmin import Admin, ModelView
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.requests import Request

from src.models.character import Character
from src.models.comment import Comment
from src.models.settlement import Settlement
from src.models.team import TeamMember, TeamMessage
from src.models.user import User
from src.models.chatbot import ActivitySubmission, InfoList, EventInfo, SubmitterProfile, TemporaryImage
from src.database_chatbot import chatbot_async_session


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str):
        super().__init__(secret_key=secret_key)
        self._username = os.getenv("ADMIN_USERNAME", "admin")
        self._password = os.getenv("ADMIN_PASSWORD")

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if (
            isinstance(username, str)
            and isinstance(password, str)
            and self._password
            and secrets.compare_digest(username, self._username)
            and secrets.compare_digest(password, self._password)
        ):
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_authenticated"))


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    category = "Accounts"

    column_list = [
        User.id,
        User.username,
        User.name,
        User.kakao_id,
        User.nickname,
        User.gender,
    ]
    column_searchable_list = [User.username, User.name, User.nickname]
    column_sortable_list = [User.id, User.username, User.name]
    column_details_exclude_list = [User.hashed_password, User.refresh_token_hash]
    form_excluded_columns = [
        User.hashed_password,
        User.refresh_token_hash,
        User.refresh_token_expires_at,
    ]


class CharacterAdmin(ModelView, model=Character):
    name = "Character"
    name_plural = "Characters"
    icon = "fa-solid fa-gamepad"
    category = "Game"

    column_list = [
        Character.id,
        Character.name,
        Character.level,
        Character.job,
        Character.server,
    ]
    column_searchable_list = [Character.name, Character.job, Character.server]
    column_sortable_list = [Character.id, Character.name, Character.level]


class SettlementAdmin(ModelView, model=Settlement):
    name = "Settlement"
    name_plural = "Settlements"
    icon = "fa-solid fa-scroll"
    category = "Game"

    column_list = [
        Settlement.id,
        Settlement.character_id,
        Settlement.title,
        Settlement.acquired_at,
    ]
    column_searchable_list = [Settlement.title]
    column_sortable_list = [Settlement.id, Settlement.acquired_at]


class CommentAdmin(ModelView, model=Comment):
    name = "Comment"
    name_plural = "Comments"
    icon = "fa-solid fa-comment"
    category = "Content"

    column_list = [
        Comment.id,
        Comment.user_id,
        Comment.author,
        Comment.content,
        Comment.created_at,
    ]
    column_searchable_list = [Comment.author, Comment.content]
    column_sortable_list = [Comment.id, Comment.created_at]
    column_default_sort = (Comment.created_at, True)


class TeamMemberAdmin(ModelView, model=TeamMember):
    name = "Team Member"
    name_plural = "Team Members"
    icon = "fa-solid fa-users"
    category = "Content"

    column_list = (
        TeamMember.id,
        TeamMember.name,
        TeamMember.role,
        TeamMember.profile_img_url,
    )
    column_searchable_list = (TeamMember.name, TeamMember.role)
    column_sortable_list = (TeamMember.id, TeamMember.name)


class TeamMessageAdmin(ModelView, model=TeamMessage):
    name = "Team Message"
    name_plural = "Team Messages"
    icon = "fa-solid fa-envelope"
    category = "Content"

    column_list = (
        TeamMessage.id,
        TeamMessage.member_id,
        TeamMessage.title,
        TeamMessage.content,
        TeamMessage.detail_img_url,
    )
    column_searchable_list = (TeamMessage.title, TeamMessage.content)
    column_sortable_list = (TeamMessage.id, TeamMessage.member_id)


class EventInfoAdmin(ModelView, model=EventInfo):
    name = "Event"
    name_plural = "Events"
    icon = "fa-solid fa-calendar"
    category = "Chatbot"
    sessionmaker = chatbot_async_session

    column_list = [EventInfo.id, EventInfo.name, EventInfo.start_day, EventInfo.end_day]
    column_searchable_list = [EventInfo.name]
    column_sortable_list = [EventInfo.id, EventInfo.name, EventInfo.start_day]


class InfoListAdmin(ModelView, model=InfoList):
    name = "Question"
    name_plural = "Questions"
    icon = "fa-solid fa-list-ol"
    category = "Chatbot"
    sessionmaker = chatbot_async_session

    column_list = [InfoList.id, InfoList.step_order, InfoList.event_name, InfoList.field_name, InfoList.question_text]
    column_searchable_list = [InfoList.field_name, InfoList.event_name, InfoList.question_text]
    column_sortable_list = [InfoList.id, InfoList.step_order, InfoList.event_name]
    column_default_sort = (InfoList.step_order, False)


class TemporaryImageAdmin(ModelView, model=TemporaryImage):
    name = "Session"
    name_plural = "Sessions"
    icon = "fa-solid fa-clock"
    category = "Chatbot"
    sessionmaker = chatbot_async_session
    can_create = False

    column_list = [TemporaryImage.id, TemporaryImage.user_key, TemporaryImage.data, TemporaryImage.image_urls]
    column_searchable_list = [TemporaryImage.user_key]
    column_sortable_list = [TemporaryImage.id]


class SubmitterProfileAdmin(ModelView, model=SubmitterProfile):
    name = "Submitter Profile"
    name_plural = "Submitter Profiles"
    icon = "fa-solid fa-id-card"
    category = "친바방"
    sessionmaker = chatbot_async_session

    column_list = [SubmitterProfile.id, SubmitterProfile.user_key, SubmitterProfile.name, SubmitterProfile.student_id]
    column_searchable_list = [SubmitterProfile.name, SubmitterProfile.student_id]
    column_sortable_list = [SubmitterProfile.id, SubmitterProfile.name]


class ActivitySubmissionAdmin(ModelView, model=ActivitySubmission):
    name = "Submission"
    name_plural = "Submissions"
    icon = "fa-solid fa-paper-plane"
    category = "친바방"
    sessionmaker = chatbot_async_session
    can_create = False

    column_list = [
        ActivitySubmission.id,
        ActivitySubmission.submitter_name,
        ActivitySubmission.submitter_student_id,
        ActivitySubmission.activity_date,
        ActivitySubmission.activity_type,
        ActivitySubmission.newbie_count,
        ActivitySubmission.existing_count,
        ActivitySubmission.submitted_at,
    ]
    column_searchable_list = [ActivitySubmission.submitter_name, ActivitySubmission.activity_type]
    column_sortable_list = [ActivitySubmission.id, ActivitySubmission.submitted_at, ActivitySubmission.activity_date]
    column_default_sort = (ActivitySubmission.submitted_at, True)


def setup_admin(app: FastAPI, engine: AsyncEngine) -> Admin:
    session_secret = os.getenv("ADMIN_SESSION_SECRET")
    if not session_secret:
        raise RuntimeError("ADMIN_SESSION_SECRET must be set")
    authentication_backend = AdminAuth(secret_key=session_secret)
    admin = Admin(
        app,
        engine,
        title="MapleWind Admin",
        authentication_backend=authentication_backend,
    )
    admin.add_view(UserAdmin)
    admin.add_view(CharacterAdmin)
    admin.add_view(SettlementAdmin)
    admin.add_view(CommentAdmin)
    admin.add_view(TeamMemberAdmin)
    admin.add_view(TeamMessageAdmin)
    admin.add_view(EventInfoAdmin)
    admin.add_view(InfoListAdmin)
    admin.add_view(TemporaryImageAdmin)
    admin.add_view(SubmitterProfileAdmin)
    admin.add_view(ActivitySubmissionAdmin)
    return admin
