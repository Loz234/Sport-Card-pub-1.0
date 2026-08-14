from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.api.routes.trending import router as trending_router
from app.config import get_settings
from app.database import get_engine

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(trending_router, prefix="/api", tags=["trending"])


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "scaffolded",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database connectivity check failed.") from exc
    return {"status": "healthy"}
