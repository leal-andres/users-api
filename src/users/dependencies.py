from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db_session
from src.users.repository import UserRepository
from src.users.service import UserService


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    return UserRepository(session)


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repo)
