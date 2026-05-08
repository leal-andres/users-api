from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code: int = 500
    title: str = "Internal Server Error"
    type_: str = "about:blank"

    def __init__(self, detail: str | None = None, **extras: Any) -> None:
        self.detail = detail or self.title
        self.extras = extras
        super().__init__(self.detail)


def _problem_response(
    status_code: int,
    type_: str,
    title: str,
    detail: str,
    instance: str,
    **extras: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    body.update(extras)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return _problem_response(
            status_code=exc.status_code,
            type_=exc.type_,
            title=exc.title,
            detail=exc.detail,
            instance=str(request.url),
            **exc.extras,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _problem_response(
            status_code=422,
            type_="https://api.example.com/errors/validation",
            title="Validation failed",
            detail="One or more fields failed validation",
            instance=str(request.url),
            errors=exc.errors(),
        )
