from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class LanguageDetectionError(AppException):
    pass


class TranslationError(AppException):
    pass


class RetrievalError(AppException):
    pass


class AnswerGenerationError(AppException):
    pass


async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"AppException at {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message, "detail": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception at {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error. Please try again.",
            "detail": "Internal server error. Please try again.",
        },
    )