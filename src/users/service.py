from uuid import UUID

from src.core.logging import get_logger
from src.users.exceptions import UserAlreadyExists, UserNotFound
from src.users.models import User
from src.users.repository import UserRepository
from src.users.schemas import UserCreate, UserUpdate

log = get_logger(__name__)


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def get_by_id(self, id_: UUID) -> User:
        user = await self.repo.get_by_id(id_)
        if user is None:
            raise UserNotFound(f"User {id_} not found")
        return user

    async def list_(
        self,
        limit: int = 50,
        offset: int = 0,
        active: bool | None = None,
    ) -> tuple[list[User], int]:
        users = await self.repo.list_(limit=limit, offset=offset, active=active)
        total = await self.repo.count(active=active)
        return users, total

    async def create(self, payload: UserCreate) -> User:
        if await self.repo.get_by_username(payload.username):
            raise UserAlreadyExists(f"Username '{payload.username}' is already taken")
        if await self.repo.get_by_email(payload.email):
            raise UserAlreadyExists(f"Email '{payload.email}' is already registered")

        user = User(**payload.model_dump())
        created = await self.repo.create(user)
        log.info("user_created", user_id=str(created.id), username=created.username)
        return created

    async def update(self, id_: UUID, payload: UserUpdate) -> User:
        user = await self.get_by_id(id_)
        changes = payload.model_dump(exclude_unset=True)

        new_username = changes.get("username")
        if (
            new_username is not None
            and new_username != user.username
            and await self.repo.get_by_username(new_username)
        ):
            raise UserAlreadyExists(f"Username '{new_username}' is already taken")

        new_email = changes.get("email")
        if (
            new_email is not None
            and new_email != user.email
            and await self.repo.get_by_email(new_email)
        ):
            raise UserAlreadyExists(f"Email '{new_email}' is already registered")

        for field, value in changes.items():
            setattr(user, field, value)

        updated = await self.repo.update(user)
        log.info("user_updated", user_id=str(updated.id), changes=list(changes.keys()))
        return updated

    async def activate(self, id_: UUID) -> User:
        user = await self.get_by_id(id_)
        if user.active:
            return user
        user.active = True
        updated = await self.repo.update(user)
        log.info("user_activated", user_id=str(updated.id))
        return updated

    async def deactivate(self, id_: UUID) -> User:
        user = await self.get_by_id(id_)
        if not user.active:
            return user
        user.active = False
        updated = await self.repo.update(user)
        log.info("user_deactivated", user_id=str(updated.id))
        return updated

    async def delete(self, id_: UUID) -> None:
        user = await self.get_by_id(id_)
        await self.repo.delete(user)
        log.info("user_deleted", user_id=str(id_))
