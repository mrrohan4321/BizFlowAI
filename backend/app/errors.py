"""Consistent error shape: {"error": {"code": "...", "message": "..."}}. No stack traces leak."""
import logging

import psycopg2
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("bizflow")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details


def _body(code: str, message: str, details=None) -> dict:
    err = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"error": err}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body("invalid_request", "Request validation failed.", details), status_code=422)

    @app.exception_handler(psycopg2.Error)
    async def _db(_: Request, exc: psycopg2.Error):
        log.error("database error: %s", type(exc).__name__)  # no SQL/params (may hold financial data)
        return JSONResponse(_body("database_error", "A database error occurred."), status_code=500)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        log.error("unhandled error: %s", type(exc).__name__)
        return JSONResponse(_body("internal_error", "Something went wrong."), status_code=500)
