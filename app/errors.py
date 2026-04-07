from __future__ import annotations

import logging

from sanic import Sanic, json
from sanic.exceptions import SanicException


class ApiError(Exception):
    def __init__(self, status: int, message: str, details: object | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def register_error_handlers(app: Sanic) -> None:
    logger = logging.getLogger(__name__)

    @app.exception(ApiError)
    async def handle_api_error(request, exc: ApiError):
        payload = {"error": exc.message}
        if exc.details is not None:
            payload["details"] = exc.details
        return json(payload, status=exc.status)

    @app.exception(SanicException)
    async def handle_sanic_error(request, exc: SanicException):
        return json({"error": str(exc)}, status=exc.status_code)

    @app.exception(Exception)
    async def handle_unexpected_error(request, exc: Exception):
        logger.exception("Unhandled exception", exc_info=exc)
        return json({"error": "Internal server error"}, status=500)

