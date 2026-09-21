# PASSBOX

PASSBOX is a document security pipeline that classifies documents as C/S/O, checks outbound policy, masks sensitive data, and routes approved requests through an LLM Gateway.

## Repository layout

```text
frontend/PASSBOX-ver.0.1/   React + Vite frontend
backend/                    FastAPI + PostgreSQL backend
```

## Local development

### Backend

1. Create `backend/.venv` and install `backend/requirements.txt`.
2. Copy `backend/.env.example` to `backend/.env` and fill in local PostgreSQL and JWT settings. `JWT_ACCESS_TOKEN_MINUTES` defaults to 60.
3. Run `backend/create_tables.py`. For an existing database, run `backend/migrate_policy.py` once to add policy management tables.
4. Run `backend/seed_demo_user.py` to create a local user.
5. Start the API:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger: `http://127.0.0.1:8000/docs`

Use `GATEWAY_MODE=MOCK` for local testing. S-grade approval requests are handled at `/approvals` by an `APPROVER` or `SECURITY_ADMIN` user.

### Frontend

1. Install dependencies in `frontend/PASSBOX-ver.0.1`.
2. Copy `.env.example` to `.env.local`.
3. Set `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`.
4. Start Vite:

```powershell
cd frontend\PASSBOX-ver.0.1
npm install
npm run dev
```

## What is not shared

Do not commit API keys, database passwords, JWT secrets, `.env` files, uploaded documents, database dumps, `storage`, virtual environments, or `node_modules`. Each teammate creates their own local environment and database.
