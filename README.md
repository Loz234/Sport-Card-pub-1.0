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
