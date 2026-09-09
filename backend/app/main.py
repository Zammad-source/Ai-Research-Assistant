from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.core.logging_config import setup_logging
from app.core.limiter import limiter
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)
from app.routes import research, translator, voice, frontend_api

setup_logging()
settings = get_settings()

app = FastAPI(title="Urdu Research Assistant API", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)
app.include_router(translator.router)
app.include_router(voice.router)
app.include_router(frontend_api.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.environment}