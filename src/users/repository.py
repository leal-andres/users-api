from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: UUID) -> User | None:
        return await self.session.get(User, id_)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_(
        self,
        limit: int = 50,
        offset: int = 0,
        active: bool | None = None,
    ) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        if active is not None:
            stmt = stmt.where(User.active == active)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, active: bool | None = None) -> int:
        stmt = select(func.count()).select_from(User)
        if active is not None:
            stmt = stmt.where(User.active == active)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def create(self, instance: User) -> User:
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: User) -> User:
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: User) -> None:
        await self.session.delete(instance)
        await self.session.flush()
