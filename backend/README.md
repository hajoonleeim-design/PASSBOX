# PASSBOX Backend

## Local setup

1. Create a Python virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and fill in the local PostgreSQL connection and JWT secret.
3. Run `create_tables.py` to create the schema, including the S-grade outbound approval and policy tables. If the database already existed before policy management was added, run `migrate_policy.py` once.
4. Run `seed_demo_user.py` to create or reset a local `demo.user` account.
5. Start the API with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The Swagger UI is available at `http://127.0.0.1:8000/docs`.

운영 현황은 `GET /api/v1/operations/dashboard`에서 조회합니다. `ADMIN` 또는 `OPERATOR` 권한이 필요하며, 현재 로그인한 기관의 요청·Job·Gateway·승인 데이터를 기준으로 집계합니다.

Use `GATEWAY_MODE=MOCK` for local testing. Keep `OPENAI_API_KEY`, database passwords, `.env`, uploaded files, and database dumps out of source control. Each developer uses a separate local PostgreSQL database and local `storage` directory.
