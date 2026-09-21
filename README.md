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
2. Copy `backend/.env.example` to `backend/.env` and fill in local PostgreSQL and JWT settings. Keep `APP_ENV=development` locally. `JWT_ACCESS_TOKEN_MINUTES` defaults to 60, `LOGIN_RATE_LIMIT_ATTEMPTS`/`LOGIN_RATE_LIMIT_WINDOW_SECONDS` control failed-login throttling, and `CORS_ALLOWED_ORIGINS` contains the comma-separated trusted frontend origins.
3. Run `backend/create_tables.py`. For an existing database, run `backend/migrate_policy.py` once to add policy management tables.
4. Run `backend/seed_demo_user.py` to create a local user.
5. Start the API:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`GET /api/v1/health` is the liveness check. `GET /api/v1/health/ready` also verifies the database connection and returns `503` until the service is ready.

Authenticated users can change their password with `POST /api/v1/auth/password`. New passwords must be at least 12 characters long.

API responses include baseline browser security headers such as `nosniff`, `DENY` framing, a strict referrer policy, and a restricted permissions policy.

Every API response also includes `X-Request-ID`. Support requests can include this value to correlate a frontend error with server logs.

Swagger: `http://127.0.0.1:8000/docs`

Every push and pull request to `main` runs backend compilation/tests and frontend lint/build through GitHub Actions.

Use `GATEWAY_MODE=MOCK` for local testing. S-grade approval requests are handled at `/approvals` by an `APPROVER` or `SECURITY_ADMIN` user.

For production, set `APP_ENV=production`, use a strong JWT secret, HTTPS-only CORS origins, a real database, and a configured non-MOCK Gateway. The API fails fast if those requirements are missing.

Retention cleanup is preview-only by default. From `backend`, run `python cleanup_retention.py` to list expired terminal-document files, then add `--apply` only after reviewing the list. The cleanup removes stored document files while keeping database audit metadata and hashes.

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
