# PASSBOX Backend

## Local setup

1. Create a Python virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and fill in the local PostgreSQL connection and JWT secret.
3. Run `create_tables.py` to create the schema, including the S-grade outbound approval and policy tables. If the database already existed before policy management was added, run `migrate_policy.py` once.
4. Run `seed_demo_user.py` to create or reset a local `demo.user` account. The default local role is `OPERATOR` so the full document flow can be tested; set `$env:DEMO_USER_ROLE="USER"` when you need a read-only user.
   To create a separate approval account, use `$env:DEMO_USERNAME="demo.approver"; $env:DEMO_DISPLAY_NAME="테스트 승인자"; $env:DEMO_USER_ROLE="APPROVER"` before running the same script.
5. Start the API with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The Swagger UI is available at `http://127.0.0.1:8000/docs`.

운영 현황은 `GET /api/v1/operations/dashboard`에서 조회합니다. `ADMIN` 또는 `OPERATOR` 권한이 필요하며, 현재 로그인한 기관의 요청·Job·Gateway·승인 데이터를 기준으로 집계합니다.

AI 채팅은 `POST /api/v1/chat/requests`에서 시작합니다. 실제 OpenAI 호출을 사용하려면 `.env`의 `GATEWAY_MODE=OPENAI`, `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4o-mini`를 설정한 뒤 `migrate_policy.py`를 실행하고 백엔드를 재시작합니다. 키가 없거나 잔액이 없으면 채팅 요청은 실패 상태로 기록되며, API 키는 브라우저로 전달되지 않습니다.

지원센터 콘텐츠는 `GET /api/v1/support/content`, 문의 접수는 `POST /api/v1/support/inquiries`, 문의 상태는 `GET /api/v1/support/inquiries/{inquiry_id}`에서 제공합니다. 문의 원문은 저장하지 않고 민감정보 탐지·해시·마스킹을 적용합니다.

실패한 분석 작업은 `POST /api/v1/jobs/{job_id}/retry`로 다시 접수할 수 있습니다. Gateway가 완료·차단·실패하면 해당 Job의 상태와 진행률도 함께 갱신됩니다.

문서 분석 Job은 API 프로세스에 포함된 DB 기반 Worker가 자동으로 텍스트 추출·보안 스캔·분류 추천을 처리합니다. 분류 추천이 끝나면 `CLASSIFICATION_REVIEW` 상태에서 담당자의 최종 확정을 기다립니다. 서버가 재시작되어도 DB에 남은 `QUEUED` 작업은 다시 처리됩니다.

C/S/O 최종 확정은 `OPERATOR`, `SECURITY_ADMIN`, `ADMIN` 역할만 수행할 수 있습니다. `USER` 역할은 추천 결과와 확정 결과 조회만 가능합니다.

Use `GATEWAY_MODE=MOCK` for local testing. Keep `OPENAI_API_KEY`, database passwords, `.env`, uploaded files, and database dumps out of source control. Each developer uses a separate local PostgreSQL database and local `storage` directory.
