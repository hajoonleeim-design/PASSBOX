# PASSBOX Docker 구성 (설치형 배포 1차)

> **상태: 작성만 했고 아직 실제 Docker 환경에서 실행해 보지 않았습니다.**
> 아래 "검증 체크리스트"를 한 번 통과한 뒤에만 발표 자료에 "컨테이너 배포 구현"이라고 쓰세요.
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
- [ ] `docker compose build` 가 5개 중 3개 이미지(backend, classifier, frontend) 모두 성공
- [ ] `docker compose ps` 에서 db, clamav, classifier, backend 가 healthy/running
- [ ] `curl http://localhost:8080/api/v1/health` 가 200
- [ ] 브라우저에서 로그인 → 문서 업로드 → 분석 → 등급 추천까지 진행
- [ ] 업로드한 문서가 분류 서비스(`docker compose logs classifier`)에서 처리됨(REMOTE 동작)
- [ ] EICAR 시험 파일이 ClamAV 에서 차단됨
- [ ] `docker compose down` 후 `up` 해도 데이터가 남아 있음(볼륨)

검증일 / 환경 / 결과: (여기에 기록)

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
