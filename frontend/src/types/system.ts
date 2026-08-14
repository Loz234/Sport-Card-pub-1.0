export interface ServiceStatus {
  status: string
  detail: string
}

export interface HealthResponse {
  app_name: string
  environment: string
  api: ServiceStatus
  database: ServiceStatus
  ingestion: ServiceStatus
  market_analysis: ServiceStatus
  machine_learning: ServiceStatus
  ai_explanation: ServiceStatus
}
