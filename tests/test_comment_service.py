from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fastapi import HTTPException

from services import comment_service
from schemas.comment_dto import CommentCreate, CommentDeleteRequest


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
async def test_create_comment_anonymous_uses_given_nickname(monkeypatch: pytest.MonkeyPatch):
    fake_create = AsyncMock(side_effect=lambda _db, comment: comment)
    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)

    payload = CommentCreate(content="hello", nickname="익명닉", password="pass1234")
    created = await comment_service.create_comment(db=None, data=payload, user=None)

    assert created.author == "익명닉"
    assert created.user_id is None
    assert created.password_hash is not None


@pytest.mark.asyncio
async def test_create_comment_anonymous_without_nickname_uses_random(monkeypatch: pytest.MonkeyPatch):
    fake_create = AsyncMock(side_effect=lambda _db, comment: comment)
    monkeypatch.setattr(comment_service.comment_repo, "create", fake_create)
    monkeypatch.setattr(comment_service, "_random_nickname", lambda: "랜덤닉99")

    payload = CommentCreate(content="hello", password="pass1234")
    created = await comment_service.create_comment(db=None, data=payload, user=None)

    assert created.author == "랜덤닉99"


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
