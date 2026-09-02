"""API error envelope + exception handlers (design doc §4.0, §8).

Every error response uses the frozen envelope:
    {"error": {"code": "...", "message": "...", "retryable": false, ...details}}
No tracebacks, SQL, paths, or provider payloads ever appear in a response.
"""
from __future__ import annotations

import logging

import pymysql.err
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dsa_tutor.ai.openai_provider import AIProviderError
from dsa_tutor.domain.curriculum import CurriculumError

log = logging.getLogger("dsa_tutor.api")


class ApiError(Exception):
    """Transport-level error carrying the frozen envelope semantics."""

    def __init__(self, status: int, code: str, message: str, *, retryable: bool = False, **details):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details
        super().__init__(message)

    def envelope(self) -> dict:
        payload = {"code": self.code, "message": self.message, "retryable": self.retryable}
        payload.update(self.details)
        return {"error": payload}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=exc.envelope())

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        malformed = any(e.get("type") == "json_invalid" for e in exc.errors())
        code = "MALFORMED_JSON" if malformed else "VALIDATION_ERROR"
        safe = [{"type": e.get("type"), "loc": [str(p) for p in e.get("loc", [])]}
                for e in exc.errors()[:5]]
        return JSONResponse(status_code=400, content={"error": {
            "code": code, "message": "Request body is not valid.", "retryable": False,
            "details": {"issues": safe}}})

    @app.exception_handler(AIProviderError)
    async def _ai_unavailable(request: Request, exc: AIProviderError):
        # design §8.1: reachable only with AI_PROVIDER=openai (hybrid falls back to builtin)
        return JSONResponse(status_code=503, content={"error": {
            "code": "AI_UNAVAILABLE", "message": str(exc), "retryable": True}})

    @app.exception_handler(pymysql.err.MySQLError)
    async def _storage_unavailable(request: Request, exc: pymysql.err.MySQLError):
        log.error("storage failure: %s", exc)
        return JSONResponse(status_code=503, content={"error": {
            "code": "STORAGE_UNAVAILABLE", "message": "Storage is temporarily unavailable.",
            "retryable": True}})

    @app.exception_handler(CurriculumError)
    async def _curriculum(request: Request, exc: CurriculumError):
        return JSONResponse(status_code=500, content={"error": {
            "code": "INTERNAL_ERROR", "message": "Curriculum lookup failed.", "retryable": False}})

    @app.exception_handler(RuntimeError)
    async def _runtime(request: Request, exc: RuntimeError):
        code = "CONFIG_ERROR" if "configuration invalid" in str(exc) else "INTERNAL_ERROR"
        log.error("runtime error: %s", exc)
        return JSONResponse(status_code=500, content={"error": {
            "code": code, "message": str(exc)[:300], "retryable": False}})

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.exception("unhandled API error")
        return JSONResponse(status_code=500, content={"error": {
            "code": "INTERNAL_ERROR", "message": "Unexpected server error.", "retryable": False}})
