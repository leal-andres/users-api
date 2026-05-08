from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.users.exceptions import UserAlreadyExists, UserNotFound
from src.users.models import User, UserRole
from src.users.schemas import UserCreate, UserUpdate
from src.users.service import UserService


def _make_user(**overrides: object) -> User:
    user = User(
        id=overrides.get("id", uuid4()),
        username=overrides.get("username", "ada"),
        email=overrides.get("email", "ada@example.com"),
        first_name=overrides.get("first_name", "Ada"),
        last_name=overrides.get("last_name", "Lovelace"),
        role=overrides.get("role", UserRole.USER),
        active=overrides.get("active", True),
    )
    return user


def _make_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_username = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.list_ = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    repo.create = AsyncMock(side_effect=lambda u: u)
    repo.update = AsyncMock(side_effect=lambda u: u)
    repo.delete = AsyncMock(return_value=None)
    return repo


async def test_get_by_id_raises_when_not_found() -> None:
    repo = _make_repo()
    service = UserService(repo)

    with pytest.raises(UserNotFound):
        await service.get_by_id(uuid4())


async def test_create_persists_user() -> None:
    repo = _make_repo()
    service = UserService(repo)
    payload = UserCreate(
        username="ada",
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
    )

    created = await service.create(payload)

    assert created.username == "ada"
    repo.create.assert_awaited_once()


async def test_create_rejects_duplicate_username() -> None:
    repo = _make_repo()
    repo.get_by_username = AsyncMock(return_value=_make_user())
    service = UserService(repo)
    payload = UserCreate(
        username="ada",
        email="new@example.com",
        first_name="Ada",
        last_name="Lovelace",
    )

    with pytest.raises(UserAlreadyExists):
        await service.create(payload)


async def test_create_rejects_duplicate_email() -> None:
    repo = _make_repo()
    repo.get_by_email = AsyncMock(return_value=_make_user())
    service = UserService(repo)
    payload = UserCreate(
        username="new",
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
    )

    with pytest.raises(UserAlreadyExists):
        await service.create(payload)


async def test_update_applies_partial_changes() -> None:
    existing = _make_user()
    repo = _make_repo()
    repo.get_by_id = AsyncMock(return_value=existing)
    service = UserService(repo)

    updated = await service.update(existing.id, UserUpdate(first_name="Augusta"))

    assert updated.first_name == "Augusta"
    assert updated.last_name == "Lovelace"


async def test_update_raises_when_not_found() -> None:
    repo = _make_repo()
    service = UserService(repo)

    with pytest.raises(UserNotFound):
        await service.update(uuid4(), UserUpdate(first_name="X"))


async def test_delete_calls_repo() -> None:
    existing = _make_user()
    repo = _make_repo()
    repo.get_by_id = AsyncMock(return_value=existing)
    service = UserService(repo)

    await service.delete(existing.id)

    repo.delete.assert_awaited_once_with(existing)


async def test_activate_sets_active_true() -> None:
    existing = _make_user(active=False)
    repo = _make_repo()
    repo.get_by_id = AsyncMock(return_value=existing)
    service = UserService(repo)

    result = await service.activate(existing.id)

    assert result.active is True
    repo.update.assert_awaited_once()


async def test_activate_is_idempotent_when_already_active() -> None:
    existing = _make_user(active=True)
    repo = _make_repo()
    repo.get_by_id = AsyncMock(return_value=existing)
    service = UserService(repo)

    result = await service.activate(existing.id)

    assert result.active is True
    repo.update.assert_not_awaited()


async def test_deactivate_sets_active_false() -> None:
    existing = _make_user(active=True)
    repo = _make_repo()
    repo.get_by_id = AsyncMock(return_value=existing)
    service = UserService(repo)

    result = await service.deactivate(existing.id)

    assert result.active is False
    repo.update.assert_awaited_once()


async def test_deactivate_is_idempotent_when_already_inactive() -> None:
    existing = _make_user(active=False)
    repo = _make_repo()
    repo.get_by_id = AsyncMock(return_value=existing)
    service = UserService(repo)

    result = await service.deactivate(existing.id)

    assert result.active is False
    repo.update.assert_not_awaited()


async def test_list_passes_active_filter_to_repo() -> None:
    repo = _make_repo()
    service = UserService(repo)

    await service.list_(limit=10, offset=0, active=True)

    repo.list_.assert_awaited_once_with(limit=10, offset=0, active=True)
    repo.count.assert_awaited_once_with(active=True)
