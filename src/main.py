from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.exceptions import register_exception_handlers
from src.core.logging import configure_logging, get_logger
from src.db.session import dispose_engine
from src.health.router import router as health_router
from src.users.router import router as users_router

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("application_starting")
    yield
    await dispose_engine()
    log.info("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        return response

    register_exception_handlers(app)

    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(users_router)

    return app


app = create_app()
