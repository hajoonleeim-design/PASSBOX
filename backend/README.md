# PASSBOX Backend

## Local setup

1. Create a Python virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and fill in the local PostgreSQL connection and JWT secret.
3. Run `create_tables.py` to create the schema, including the S-grade outbound approval table.
4. Run `seed_demo_user.py` to create or reset a local `demo.user` account.
5. Start the API with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The Swagger UI is available at `http://127.0.0.1:8000/docs`.

Use `GATEWAY_MODE=MOCK` for local testing. Keep `OPENAI_API_KEY`, database passwords, `.env`, uploaded files, and database dumps out of source control. Each developer uses a separate local PostgreSQL database and local `storage` directory.
