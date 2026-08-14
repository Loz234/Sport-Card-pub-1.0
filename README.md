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

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Railway deployment notes

- Deploy backend and frontend as separate Railway services from this monorepo.
- Use `backend/Dockerfile` for the API service.
- Set environment variables from `.env.example` in Railway without committing real secrets.
- Point the frontend `VITE_API_BASE_URL` variable to the deployed backend URL.

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
