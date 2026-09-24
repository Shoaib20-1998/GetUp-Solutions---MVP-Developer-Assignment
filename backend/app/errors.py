"""One error shape for every failure, so the frontend has a single error path.

    {"error": {"code": "...", "message": "...", "details": [...]}}
"""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

_CODE_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "PAYLOAD_TOO_LARGE",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
}


def envelope(
    code: str, message: str, details: list[dict[str, str]] | None = None
) -> dict:
    body: dict[str, object] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return {"error": body}


def _field_path(loc: tuple) -> str:
    # Drop the "body" / "query" prefix so the client sees the field name.
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) or "_root"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": _field_path(err["loc"]), "issue": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=envelope(
                "VALIDATION_ERROR", "Request validation failed", details
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _CODE_BY_STATUS.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope(code, str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(HTTPException)
    async def _fastapi_http(_: Request, exc: HTTPException) -> JSONResponse:
        return await _http(_, exc)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the cause; never leak it to the caller.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=envelope("INTERNAL_ERROR", "An unexpected error occurred"),
        )
