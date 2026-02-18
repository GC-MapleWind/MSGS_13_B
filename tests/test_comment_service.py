from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fastapi import HTTPException

from services import comment_service
from pydantic import ValidationError

from schemas.comment_dto import CommentCreate, CommentDeleteRequest, CommentResponse


@pytest.mark.asyncio
async def test_create_comment_prefers_user_nickname(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    async def fake_create(_db, comment):
        captured["comment"] = comment
        return comment

    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)

    user = SimpleNamespace(id=1, name="Real Name", nickname="Nick")
    payload = CommentCreate(content="hello")

    created = await comment_service.create_comment(db=None, data=payload, user=user)

    assert created.author == "Nick"
    assert captured["comment"].author == "Nick"
    assert captured["comment"].user_id == 1
    assert captured["comment"].password_hash is None
    assert getattr(created, "delete_token", None) is None


@pytest.mark.asyncio
async def test_create_comment_falls_back_to_user_name(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    async def fake_create(_db, comment):
        captured["comment"] = comment
        return comment

    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)

    user = SimpleNamespace(id=2, name="Real Name", nickname=None)
    payload = CommentCreate(content="hello")

    created = await comment_service.create_comment(db=None, data=payload, user=user)

    assert created.author == "Real Name"
    assert captured["comment"].author == "Real Name"


@pytest.mark.asyncio
async def test_create_comment_logged_in_uses_default_author_when_profile_empty(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    async def fake_create(_db, comment):
        captured["comment"] = comment
        return comment

    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)

    user = SimpleNamespace(id=30, name="   ", nickname="  ")
    payload = CommentCreate(content="hello")

    created = await comment_service.create_comment(db=None, data=payload, user=user)

    assert created.author == "익명"
    assert captured["comment"].author == "익명"


@pytest.mark.asyncio
async def test_create_comment_logged_in_ignores_guest_fields(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    async def fake_create(_db, comment):
        captured["comment"] = comment
        return comment

    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)

    user = SimpleNamespace(id=3, name="Account Name", nickname="AccountNick")
    payload = CommentCreate(content="hello", nickname="손님닉", password="pass1234")

    created = await comment_service.create_comment(db=None, data=payload, user=user)

    assert created.author == "AccountNick"
    assert captured["comment"].user_id == 3
    assert captured["comment"].password_hash is None


@pytest.mark.asyncio
async def test_create_comment_anonymous_always_uses_random_nickname(monkeypatch: pytest.MonkeyPatch):
    fake_create = AsyncMock(side_effect=lambda _db, comment: comment)
    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)
    monkeypatch.setattr(comment_service, "_random_nickname", lambda: "랜덤닉99")

    payload = CommentCreate(content="hello", nickname="익명닉", password="pass1234")
    created = await comment_service.create_comment(db=None, data=payload, user=None)

    assert created.author == "랜덤닉99"
    assert created.user_id is None
    assert created.password_hash is not None
    assert created.delete_token == "pass1234"


@pytest.mark.asyncio
async def test_create_comment_anonymous_without_nickname_uses_random(monkeypatch: pytest.MonkeyPatch):
    fake_create = AsyncMock(side_effect=lambda _db, comment: comment)
    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)
    monkeypatch.setattr(comment_service, "_random_nickname", lambda: "랜덤닉99")

    payload = CommentCreate(content="hello", password="pass1234")
    created = await comment_service.create_comment(db=None, data=payload, user=None)

    assert created.author == "랜덤닉99"


@pytest.mark.asyncio
async def test_create_comment_anonymous_without_password_is_allowed(monkeypatch: pytest.MonkeyPatch):
    fake_create = AsyncMock(side_effect=lambda _db, comment: comment)
    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)
    monkeypatch.setattr(comment_service, "_random_nickname", lambda: "랜덤닉11")

    payload = CommentCreate(content="hello", nickname="게스트닉")
    created = await comment_service.create_comment(db=None, data=payload, user=None)

    assert created.author == "랜덤닉11"
    assert created.password_hash is not None
    assert isinstance(created.delete_token, str)
    assert len(created.delete_token) >= 16


def test_comment_create_blank_nickname_is_treated_as_none():
    payload = CommentCreate(content="hello", nickname="   ", password=" pass1234 ")

    assert payload.nickname is None
    assert payload.password == "pass1234"


def test_comment_create_rejects_blank_content():
    with pytest.raises(ValidationError):
        CommentCreate(content="   ", password="pass1234")


def test_comment_delete_request_blank_password_is_treated_as_none():
    payload = CommentDeleteRequest(password="    ")
    assert payload.password is None


@pytest.mark.asyncio
async def test_delete_comment_logged_in_owner_can_delete(monkeypatch: pytest.MonkeyPatch):
    comment = SimpleNamespace(id=11, user_id=7, password_hash=None)
    fake_delete = AsyncMock()

    monkeypatch.setattr(comment_service.comment_repo, "get_by_id", AsyncMock(return_value=comment))
    monkeypatch.setattr(comment_service.comment_repo, "delete", fake_delete)

    await comment_service.delete_comment(
        db=None,
        comment_id=11,
        user=SimpleNamespace(id=7),
        payload=None,
    )

    fake_delete.assert_awaited_once_with(None, comment)


@pytest.mark.asyncio
async def test_delete_comment_logged_in_non_owner_forbidden(monkeypatch: pytest.MonkeyPatch):
    comment = SimpleNamespace(id=12, user_id=7, password_hash=None)
    fake_delete = AsyncMock()

    monkeypatch.setattr(comment_service.comment_repo, "get_by_id", AsyncMock(return_value=comment))
    monkeypatch.setattr(comment_service.comment_repo, "delete", fake_delete)

    with pytest.raises(HTTPException) as exc:
        await comment_service.delete_comment(
            db=None,
            comment_id=12,
            user=SimpleNamespace(id=8),
            payload=None,
        )

    assert exc.value.status_code == 403
    fake_delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_comment_anonymous_wrong_password_forbidden(monkeypatch: pytest.MonkeyPatch):
    password_hash = comment_service.pwd_context.hash("pass1234")
    comment = SimpleNamespace(id=13, user_id=None, password_hash=password_hash)

    monkeypatch.setattr(comment_service.comment_repo, "get_by_id", AsyncMock(return_value=comment))
    fake_delete = AsyncMock()
    monkeypatch.setattr(comment_service.comment_repo, "delete", fake_delete)

    with pytest.raises(HTTPException) as exc:
        await comment_service.delete_comment(
            db=None,
            comment_id=13,
            user=None,
            payload=CommentDeleteRequest(password="wrong-pass"),
        )

    assert exc.value.status_code == 403
    fake_delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_comment_anonymous_correct_password_can_delete(monkeypatch: pytest.MonkeyPatch):
    password_hash = comment_service.pwd_context.hash("pass1234")
    comment = SimpleNamespace(id=14, user_id=None, password_hash=password_hash)
    fake_delete = AsyncMock()

    monkeypatch.setattr(comment_service.comment_repo, "get_by_id", AsyncMock(return_value=comment))
    monkeypatch.setattr(comment_service.comment_repo, "delete", fake_delete)

    await comment_service.delete_comment(
        db=None,
        comment_id=14,
        user=None,
        payload=CommentDeleteRequest(password="pass1234"),
    )

    fake_delete.assert_awaited_once_with(None, comment)


@pytest.mark.asyncio
async def test_delete_comment_anonymous_without_password_hash_forbidden(
    monkeypatch: pytest.MonkeyPatch,
):
    comment = SimpleNamespace(id=15, user_id=None, password_hash=None)
    fake_delete = AsyncMock()

    monkeypatch.setattr(comment_service.comment_repo, "get_by_id", AsyncMock(return_value=comment))
    monkeypatch.setattr(comment_service.comment_repo, "delete", fake_delete)

    with pytest.raises(HTTPException) as exc:
        await comment_service.delete_comment(
            db=None,
            comment_id=15,
            user=None,
            payload=None,
        )

    assert exc.value.status_code == 403
    fake_delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_comments_sets_is_mine_and_is_anonymous_flags(monkeypatch: pytest.MonkeyPatch):
    comments = [
        SimpleNamespace(id=1, user_id=7, author="u1", content="a", created_at="2026-02-19T00:00:00"),
        SimpleNamespace(id=2, user_id=None, author="anon", content="b", created_at="2026-02-19T00:01:00"),
    ]

    monkeypatch.setattr(comment_service.comment_repo, "get_all", AsyncMock(return_value=comments))

    result = await comment_service.get_comments(
        db=None,
        page=1,
        limit=20,
        current_user=SimpleNamespace(id=7),
    )

    assert len(result) == 2
    assert isinstance(result[0], CommentResponse)
    assert result[0].is_mine is True
    assert result[0].is_anonymous is False
    assert result[1].is_mine is False
    assert result[1].is_anonymous is True


@pytest.mark.asyncio
async def test_delete_comment_logged_out_cannot_delete_logged_in_comment(monkeypatch: pytest.MonkeyPatch):
    comment = SimpleNamespace(id=99, user_id=7, password_hash=None)
    fake_delete = AsyncMock()

    monkeypatch.setattr(comment_service.comment_repo, "get_by_id", AsyncMock(return_value=comment))
    monkeypatch.setattr(comment_service.comment_repo, "delete", fake_delete)

    with pytest.raises(HTTPException) as exc:
        await comment_service.delete_comment(
            db=None,
            comment_id=99,
            user=None,
            payload=None,
        )

    assert exc.value.status_code == 401
    fake_delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_comment_not_found_returns_404(monkeypatch: pytest.MonkeyPatch):
    fake_delete = AsyncMock()

    monkeypatch.setattr(comment_service.comment_repo, "get_by_id", AsyncMock(return_value=None))
    monkeypatch.setattr(comment_service.comment_repo, "delete", fake_delete)

    with pytest.raises(HTTPException) as exc:
        await comment_service.delete_comment(
            db=None,
            comment_id=404,
            user=SimpleNamespace(id=1),
            payload=None,
        )

    assert exc.value.status_code == 404
    fake_delete.assert_not_awaited()
