from sqladmin import Admin, ModelView

from models.character import Character
from models.comment import Comment
from models.settlement import Settlement
from models.user import User


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
        User.student_id,
        User.nickname,
        User.gender,
    ]
    column_searchable_list = [User.username, User.name, User.student_id, User.nickname]
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


def setup_admin(app, engine) -> Admin:
    admin = Admin(app, engine, title="MapleWind Admin")
    admin.add_view(UserAdmin)
    admin.add_view(CharacterAdmin)
    admin.add_view(SettlementAdmin)
    admin.add_view(CommentAdmin)
    return admin
