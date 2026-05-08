import os
from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_PASSWORD = quote_plus("xRgMjHolAV3vtp/N8ASQNSSG3hTVC+rJ")
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://postgres:{TEST_DB_PASSWORD}@localhost:5433/users_api_test"
)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    from src.db.base import Base
    from src.users import models  # noqa: F401  registers metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    from src.db.session import get_db_session
    from src.main import app

    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    async with factory() as cleanup:
        await cleanup.execute(text("TRUNCATE TABLE users CASCADE"))
        await cleanup.commit()

    app.dependency_overrides.clear()
