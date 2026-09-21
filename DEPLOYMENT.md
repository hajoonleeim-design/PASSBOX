# PASSBOX 운영·배포 체크리스트

이 문서는 PASSBOX를 로컬에서 확인하고, 팀 공유 환경으로 옮길 때 필요한 순서를 정리한 문서입니다.

## 1. 로컬 실행

### 백엔드

```powershell
cd "C:\Users\user\Desktop\Projects\N2SF with AI\backend"
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe create_tables.py
.\.venv\Scripts\python.exe seed_demo_user.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

로컬 테스트는 `APP_ENV=development`, `GATEWAY_MODE=MOCK`으로 실행할 수 있습니다. PostgreSQL이 실행 중이어야 하며, 시드 스크립트가 요구하는 테스트 비밀번호는 저장소에 기록하지 않습니다.

### 프론트엔드

```powershell
cd "C:\Users\user\Desktop\Projects\N2SF with AI\frontend\PASSBOX-ver.0.1"
npm ci
Copy-Item .env.example .env.local
notepad .env.local
npm run dev
```

`.env.local`에는 다음처럼 백엔드 주소를 설정합니다.

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Swagger는 `http://127.0.0.1:8000/docs`, 프론트는 Vite가 출력한 주소에서 확인합니다.

## 2. 배포 전 필수 설정

운영 백엔드는 시작할 때 아래 조건을 검사합니다. 하나라도 빠지면 의도적으로 시작하지 않습니다.

- `APP_ENV=production`
- 실제 PostgreSQL `DATABASE_URL`
- 32자 이상의 새 `JWT_SECRET_KEY`
- `GATEWAY_MODE=MOCK`이 아닌 실제 Gateway 설정
- `GATEWAY_MODE=OPENAI`인 경우 `OPENAI_API_KEY`와 모델 설정
- `CORS_ALLOWED_ORIGINS`에 실제 프론트엔드의 HTTPS 주소만 등록
- 운영용 `STORAGE_ROOT`와 파일 권한

API 키, JWT 비밀키, DB 비밀번호, `.env` 파일은 GitHub에 올리지 않습니다. GitHub Actions에는 현재 비밀값이 필요 없는 컴파일·테스트·프론트 빌드만 등록되어 있습니다.

## 3. 배포 후 점검

```powershell
Invoke-RestMethod https://<api-domain>/api/v1/health
Invoke-RestMethod https://<api-domain>/api/v1/health/ready
```

`health`는 프로세스 생존 확인용이고, `health/ready`는 DB 연결까지 확인합니다. 장애 문의에는 응답 헤더의 `X-Request-ID`를 함께 전달합니다.

다음 흐름을 한 번 점검합니다.

1. 로그인 및 로그아웃
2. `/account`에서 비밀번호 변경
3. 문서 업로드 → 검사 → 추출 → 스캔
4. C/S/O 추천 및 확정
5. S등급 승인 → Gateway 전송
6. 감사 PDF 다운로드
7. 관리자 정책 저장 및 운영 대시보드 확인

## 4. 보존 기간 정리

정리 대상부터 먼저 확인하고, 결과를 검토한 후에만 삭제를 적용합니다.

```powershell
cd backend
.\.venv\Scripts\python.exe cleanup_retention.py
.\.venv\Scripts\python.exe cleanup_retention.py --apply
```

정리 작업은 만료된 종료 문서의 저장 파일만 제거하고 DB의 감사 메타데이터와 해시는 보존합니다.

## 5. 팀 공유 순서

팀원은 저장소를 clone한 뒤 각자 `backend/.env`, `frontend/PASSBOX-ver.0.1/.env.local`, PostgreSQL, 가상환경과 `node_modules`를 별도로 준비합니다. 로컬 DB와 업로드 파일은 자동으로 공유되지 않습니다. 공유해야 하는 것은 GitHub의 코드와 이 문서에 적힌 환경 변수 이름이며, 비밀값은 안전한 별도 채널이나 Secret Manager로 전달합니다.

## 6. 아직 외부에서 결정해야 하는 항목

저장소 내부 구현은 완료되어 있지만 아래 항목은 실제 운영 주체가 선택하고 발급해야 합니다.

- SSO/조직 계정 제공자와 도메인
- 실제 LLM Gateway와 OpenAI 결제·사용량 정책
- 운영 PostgreSQL, 파일 저장소, 백업 및 모니터링 인프라
- HTTPS 인증서와 배포 플랫폼

이 값들은 프로젝트 코드에 임의로 넣지 않는 것이 맞습니다. 선택이 끝나면 해당 환경 변수를 배포 환경에 주입하고, production 시작 검사와 위 점검 순서를 다시 실행합니다.
