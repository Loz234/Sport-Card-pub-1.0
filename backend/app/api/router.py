from fastapi import APIRouter

from app.api.routes.cards import router as cards_router
from app.api.routes.health import router as health_router
from app.api.routes.rankings import router as rankings_router
from app.api.routes.trending import router as trending_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(cards_router, tags=["cards"])
api_router.include_router(rankings_router, tags=["rankings"])
api_router.include_router(trending_router, tags=["trending"])
