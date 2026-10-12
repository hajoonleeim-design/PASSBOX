# PASSBOX Docker 구성 (설치형 배포 1차)

> **상태: 2026-10-12에 실제 Docker 환경(우분투 24.04 VM)에서 빌드·기동·점검을 통과했습니다.**
> 검증 환경과 결과는 아래 "검증 기록"에 있습니다. 운영 서버에 그대로 올린 것은 아니고, TLS·production 전환은 아직 남아 있습니다("알려진 한계").
> 이 구성은 `feat/docker-compose` 브랜치에만 있고, 기존 실행 방식(venv + uvicorn + Vite)은 그대로입니다.

## 무엇이 뜨나
| 서비스 | 역할 | 밖으로 열림 |
|---|---|---|
| frontend (nginx) | 화면 + `/api` 를 백엔드로 전달 | **8080** |
| backend (FastAPI) | 업로드·탐지·승인·감사·게이트웨이 | 아니오 |
| classifier | KLUE-RoBERTa C/S/O 분류 | 아니오 |
| clamav | 백신 검사(clamd) | 아니오 |
| db (PostgreSQL 16) | 데이터 | 아니오 |

기관 서버 한 대에서 `docker compose up` 으로 전체가 올라가고, 외부에는 8080 포트 하나만 열립니다.

## 준비물
- Docker + Docker Compose v2 (예: 우분투 VM 에 설치)
- 분류 모델 폴더 `classifier-service/model_out/` (git 에 없음, 약 440MB. 현재 v5)
- 처음 한 번은 인터넷 필요: ClamAV 바이러스 정의, easyocr 문자 인식 모델, PyTorch(CPU) 내려받기

## 실행
```bash
cp docker.env.example .env
# .env 를 열어 POSTGRES_PASSWORD, JWT_SECRET_KEY, DATA_ENCRYPTION_KEY(32자 이상), CLASSIFIER_TOKEN 을 채운다
docker compose up -d --build
docker compose ps                      # 모두 healthy / running 이면 성공 (clamav 는 몇 분 걸림)
docker compose exec -it backend python seed_demo_user.py   # 시연용 계정 생성(비밀번호 입력)
```
접속: `http://서버주소:8080`

외부 AI는 기본이 `GATEWAY_MODE=MOCK`(호출 없음)입니다. 실제 호출은 `.env` 에서 `LIVE` 로 바꾸고 쓸 서비스 키만 넣으세요
(예: 무료 Gemini 키만. OpenAI·Anthropic 은 비워 두면 호출 자체가 불가능합니다).

## 검증 체크리스트 (결과를 아래에 적어 두세요)
- [x] `docker compose build` 가 5개 중 3개 이미지(backend, classifier, frontend) 모두 성공
- [x] `docker compose ps` 에서 db, clamav, classifier, backend 가 healthy/running
- [x] `curl http://localhost:8080/api/v1/health` 가 200
- [x] 브라우저에서 로그인 → 문서 업로드 → 분석 → 등급 추천까지 진행
- [x] 업로드한 문서가 분류 서비스(`docker compose logs classifier`)에서 처리됨(REMOTE 동작)
- [x] EICAR 시험 파일이 ClamAV 에서 차단됨
- [x] `docker compose down` 후 `up` 해도 데이터가 남아 있음(볼륨)

검증일 / 환경 / 결과: 아래 "검증 기록"

## 검증 기록 (2026-10-12)
- **환경**: VMware Workstation 17.5.2 위의 Ubuntu 24.04.5 서버 VM(CPU 4, 메모리 8GB, 디스크 40GB, NAT). Docker 29.1.3, Compose 2.40.3. 모델은 v5(`classifier-service/model_out`)를 호스트 폴더로 읽기 전용 연결.
- **빌드**: 이미지 3개 모두 성공(backend 2.66GB, classifier 1.74GB, frontend nginx). 처음 받을 때 PyTorch(CPU) 때문에 약 25분. 첫 시도에서 Docker 저장소 접속 `TLS handshake timeout`이 한 번 났고(일시적 네트워크), 같은 명령을 다시 실행하자 이어서 성공.
- **기동**: db·clamav·backend `healthy`, classifier·frontend 실행. 호스트에는 8080 하나만 열림.
- **브라우저와 같은 경로(8080 → nginx → /api)로 확인한 항목, 10/10 통과**
  1. 화면 응답(HTTP 200), 2. `/api/v1/health`, 3. `/health/ready`(DB 연결), 4. 데모 계정 로그인 3종, 5. 문서 업로드, 6. 검사와 ClamAV 통과, 7. 분석 작업 생성, 8. 분류기 컨테이너가 S로 추천(`klue-roberta-base-model_out`, 확신도 1.0, 첫 요청 3초), 9. EICAR 차단(HTTP 422), 10. 관리자 정책 첫 접속(조회와 이력 모두 200).
- **백신 컨테이너가 실제로 잡았음을 확인**: 감사 기록의 엔진이 `clamav`이고, clamd 로그에 `instream(...): Eicar-Test-Signature FOUND`가 남음(백엔드의 자체 EICAR 안전장치가 아님).
- **데이터 보존**: `docker compose down` 후 `up -d`(볼륨 유지)하자 재로그인과 기존 문서의 추천 결과가 그대로 남음. 볼륨 3개(`db_data`, `clamav_db`, `storage`).
- **확인하지 못한 것**: 브라우저 화면 조작(사람이 눌러 보기), 외부 AI 호출(MOCK 모드라 호출 없음), 승인·감사 PDF 같은 나머지 화면, 폐쇄망 설치(이미지 오프라인 이전), HTTPS, production 모드, 동시 부하.

### 처음 설치할 때 알아 둘 점
- 새 DB는 비어 있어서 **계정을 먼저 만들어야** 로그인됩니다. `seed_demo_user.py`는 비밀번호를 직접 입력받으므로 `docker compose exec -it backend python seed_demo_user.py`로 실행하세요(기관 이름은 "PASSBOX 테스트 기관", 기관 ID 1).
- ClamAV는 처음 기동할 때 바이러스 정의를 내려받느라 몇 분 걸립니다. 그동안 backend는 `healthy`가 되지 않습니다(의도된 동작).

### 추가 확인 (2026-10-12): 장애 시 동작, 백업·복구, 컨테이너 보호
- **백신(ClamAV)을 멈추고 검사 요청**: HTTP 503 "악성코드 검사 서버에 연결할 수 없습니다. 잠시 후 다시 검사해 주세요." 문서는 통과하지 못하고(검사 불가 상태에서 무검사 통과 없음), 백신 복구 후 같은 문서 재검사는 200.
- **분류기를 멈추고 분석 요청**: 작업이 FAILED가 되고 사용자 메시지 "분류 서버에 연결하지 못했습니다. 잠시 후 다시 시도해주세요."가 표시됨. 추천은 만들어지지 않았고(HTTP 404), 분류기 복구 후 재시도(`/jobs/{id}/retry`)로 정상 추천(O)이 생성됨.
- **DB 백업·복구**: `pg_dump`로 백업(약 80KB)한 뒤 **별도 시험 DB**에 복원해 행 수를 비교함(users 4=4, documents 4=4, audit_log_entries 11=11, classification_recommendations 2=2). 시험 DB는 삭제했고 원본 DB는 건드리지 않음. 해시체인 검증을 복구본에서 다시 돌려 보지는 않았음.
- **외부에 열린 포트**: 호스트에 게시되는 포트는 frontend 8080 하나. db(5432), backend(8000), classifier(8100), clamav(3310)는 컨테이너 내부 네트워크에서만 접근됨.
- **이미지에 비밀값 없음**: 이미지 안에 `.env`가 없고(`.dockerignore`), 이미지 이력에서 비밀값 키워드 0건. 비밀값은 VM의 `.env`(권한 600)로만 주입됨(환경변수 방식, Docker secrets·KMS 아님).
- **적용하지 않은 통제 (사실대로)**: HTTPS/TLS(nginx는 80번만 사용, 443 설정 없음), 비루트 실행(backend·classifier 모두 root), 읽기 전용 루트 파일시스템, `no-new-privileges`. 이 구성은 VM 1대의 다중 컨테이너이며 고가용성·다중 서버 확장을 검증한 것이 아님.
- **남은 위험**: `DATA_ENCRYPTION_KEY`를 잃으면 암호화된 본문·질문·답변을 읽을 수 없음. 키는 VM의 `.env`에만 있고 별도 보관·복구 절차는 없음. DB 중단, 외부 AI 무응답 시 동작은 이번에 시험하지 않음.

## Docker 없이 미리 확인한 것 (2026-10-11, Windows 개발 PC)
컨테이너 안에서 일어나는 일 중 Docker 없이도 재현할 수 있는 부분을 깨끗한 체크아웃(`feat/docker-compose`)에서 실제로 돌려 봤습니다.
- [x] 프런트: `npm ci` 후 `VITE_API_BASE_URL=/api/v1 npm run build` 성공(`tsc -b` 포함). 상대 주소 `/api/v1`이 번들에 들어감
- [x] 백엔드: 빈 DB에서 `create_tables.py`가 22개 테이블을 모두 생성하고, 컴포즈와 같은 환경변수로 서버가 떠서 `/api/v1/health`(컴포즈 헬스체크)와 `/health/ready`가 200
- [x] 로그인 → 업로드 → 검사(`/inspect`)까지 빈 DB에서 정상(이 PC에는 ClamAV 데몬이 이미 떠 있어 백신 단계는 통과)
- [ ] **미확인**: 이미지 빌드(Dockerfile 3개), 컨테이너 간 네트워크, nginx `/api` 전달, ClamAV 컨테이너 헬스체크, 분류기 컨테이너의 모델 마운트

## 알려진 한계 (솔직히)
- `APP_ENV=development` 로 띄웁니다. production 모드는 분류기 주소가 HTTPS 여야 하고(내부 http 불가), 기관 도메인 HTTPS 종단이 필요합니다. 실제 설치 시 앞단에 TLS(nginx/로드밸런서)를 두고 production 으로 전환하는 작업이 남아 있습니다.
- 이미지가 큽니다(PyTorch). 폐쇄망 설치는 이미지를 미리 만들어 `docker save/load` 로 옮겨야 합니다.
- 모델 파일은 이미지에 포함하지 않고 호스트 폴더를 읽기 전용으로 연결합니다.
- DB 마이그레이션 스크립트(`migrate_*.py`)는 기존 DB 용입니다. 새 DB 는 시작 시 `create_tables.py` 가 전체 테이블을 만듭니다.
