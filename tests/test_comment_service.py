from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services import comment_service
from schemas.comment_dto import CommentCreate


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
