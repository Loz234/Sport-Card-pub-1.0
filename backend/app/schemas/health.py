from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str
    detail: str


class HealthCheckResponse(BaseModel):
    app_name: str
    environment: str
    api: ServiceStatus
    database: ServiceStatus
    ingestion: ServiceStatus
    market_analysis: ServiceStatus
    machine_learning: ServiceStatus
    ai_explanation: ServiceStatus
