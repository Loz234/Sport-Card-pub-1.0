# CardSignal AI

CardSignal AI is a sports card market intelligence platform scaffolded for a FastAPI backend, React frontend, PostgreSQL storage, and Railway deployment.

## Repository structure

```text
/backend              FastAPI application, domain services, ML/AI modules, backend tests
/frontend             React + TypeScript + Vite application
/tests                Repository-level integration and end-to-end test area
/.github/workflows    CI workflow definitions
```

## Backend architecture

- `backend/app/main.py` - FastAPI entry point
- `backend/app/config.py` - environment-driven settings
- `backend/app/database.py` - SQLAlchemy engine and session management
- `backend/app/models/` - ORM models
- `backend/app/schemas/` - API schemas
- `backend/app/api/` - routers and endpoints
- `backend/app/services/` - card identification and market analysis services
- `backend/app/ml/` - feature engineering and prediction interfaces
- `backend/app/ai/` - AI explanation boundary
- `backend/app/data/` - ingestion contracts and synthetic development data

## Frontend architecture

- `frontend/src/components/` - shared UI building blocks
- `frontend/src/pages/` - route-level pages
- `frontend/src/services/` - API clients
- `frontend/src/types/` - frontend type definitions
- `frontend/src/hooks/` - reusable React hooks

## Local development

Use separate templates for environment setup:

- `.env.development.example` for local development
- `.env.production.example` for production reference values

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.development.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Railway deployment

Deploy backend and frontend as separate Railway services from this monorepo.

### 1) Create Railway PostgreSQL

1. In Railway, create a new project.
2. Add a PostgreSQL service.
3. Copy the generated connection string and set it as `DATABASE_URL` on the backend service.

### 2) Deploy backend service

1. Add a new service from GitHub and select this repository.
2. Set the backend service root directory to `backend`.
3. Build with `backend/Dockerfile`.
4. Railway will inject `PORT`; the container:
   - runs `alembic upgrade head` to apply pending migrations
   - then starts Gunicorn/Uvicorn on `0.0.0.0:$PORT`
5. `alembic upgrade head` is safe to run repeatedly: only unapplied migrations execute.
6. Configure backend environment variables:
   - `DATABASE_URL` (from Railway PostgreSQL)
   - `LLM_API_KEY`
   - `FRONTEND_URL` (deployed frontend URL)
   - `ENVIRONMENT=production`
   - `RUN_DB_MIGRATIONS=true` (default; set `false` only for controlled/manual runs)
7. Optional: set `CORS_ORIGINS` as a comma-separated list for multiple frontend origins.
8. Verify health at `GET /health` (this endpoint checks database connectivity) expecting:

```json
{
  "status": "healthy"
}
```

### 3) Deploy frontend service

1. Add another Railway service from the same GitHub repository.
2. Set the frontend service root directory to `frontend`.
3. Set `VITE_API_BASE_URL` to the deployed backend URL (for example, `https://<backend>.up.railway.app`).
4. Deploy and verify frontend requests resolve against the configured backend URL.

### Security and secrets

- Never commit real credentials, API keys, or tokens to GitHub.
- Store all production secrets in Railway environment variables only.
- Use `.env.example`, `.env.development.example`, and `.env.production.example` only as templates with placeholder values.
- Synthetic development data is not auto-seeded in production deployment.

## Current scope

This scaffold intentionally avoids:

- marketplace scraping
- live marketplace API integrations
- fake production prediction endpoints

Synthetic development data is isolated under `backend/app/data/` for safe early-stage development.

## ML prediction engine (v1)

- Implementation: `backend/app/ml/predictor.py`
- Feature pipeline: point-in-time only (`as_of`) with strict no-lookahead feature/target construction
- Models:
  - Baseline momentum model
  - XGBoost regressors for 7d / 30d / 90d percentage movement
- Evaluation: time-based train/validation/test split with out-of-sample MAE, RMSE, MAPE, and directional accuracy
- Persistence/versioning: model artifacts and metadata saved under a versioned directory (`metadata.json` + `xgb_{horizon}d.json`)

### Out-of-sample performance snapshot (synthetic dataset)

Run:

```bash
cd backend
python -m pytest -q
```

Measured by `CardSignalPredictionEngine.train(...).evaluate(test_split)`:

- 7d horizon
  - XGBoost: MAE 4.952, RMSE 6.452, MAPE 200.78%, directional accuracy 0.403
  - Baseline: MAE 4.856, RMSE 6.442, MAPE 105.27%, directional accuracy 0.289
- 30d horizon
  - XGBoost: MAE 4.684, RMSE 6.125, MAPE 152.27%, directional accuracy 0.468
  - Baseline: MAE 4.717, RMSE 6.467, MAPE 205.90%, directional accuracy 0.388
- 90d horizon
  - XGBoost: MAE 5.042, RMSE 6.581, MAPE 217.30%, directional accuracy 0.418
  - Baseline: MAE 6.693, RMSE 9.332, MAPE 261.79%, directional accuracy 0.408

These are out-of-sample synthetic benchmarks and should not be treated as live-market production performance.
