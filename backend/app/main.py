from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.trending import router as trending_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
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
