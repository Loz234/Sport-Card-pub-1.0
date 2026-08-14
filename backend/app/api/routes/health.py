from fastapi import APIRouter

from app.config import get_settings
from app.schemas.health import HealthCheckResponse, ServiceStatus

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
def health_check() -> HealthCheckResponse:
    settings = get_settings()
    return HealthCheckResponse(
        app_name=settings.app_name,
        environment=settings.app_env,
        api=ServiceStatus(status="ok", detail="FastAPI application is configured."),
        database=ServiceStatus(status="pending", detail="PostgreSQL connection is configured but migrations are not yet applied."),
        ingestion=ServiceStatus(status="pending", detail="Data ingestion layer is scaffolded with synthetic development inputs only."),
        market_analysis=ServiceStatus(status="pending", detail="Market analysis service boundaries are defined but no live analytics run yet."),
        machine_learning=ServiceStatus(status="pending", detail="ML module interfaces exist but no trained model is shipped in the scaffold."),
        ai_explanation=ServiceStatus(
            status="ok",
            detail="AI market analyst service is active with provider abstraction; external LLM provider can be configured.",
        ),
    )
