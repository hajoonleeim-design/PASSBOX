from contextlib import asynccontextmanager
import logging
import re
import threading
from pathlib import Path
from urllib.parse import quote, urlparse
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.api.auth import router as auth_router
from app.api.approvals import router as approvals_router
from app.api.documents import router as documents_router
from app.api.jobs import router as jobs_router
from app.api.extraction import router as extraction_router
from app.api.scans import router as scans_router
from app.api.classifications import router as classifications_router
from app.api.outbound import router as outbound_router
from app.api.gateway import router as gateway_router
from app.api.decisions import router as decisions_router
from app.api.audit import router as audit_router
from app.api.policies import router as policies_router
from app.api.sensitive_keywords import router as sensitive_keywords_router
from app.api.operations import router as operations_router
from app.api.chat import router as chat_router
from app.api.support import router as support_router
from app.api.review_requests import router as review_requests_router
from app.api.siem import router as siem_router
from app.db import Settings, check_database, get_session_factory
from app.job_worker import start_worker, stop_worker
from app.retention import cleanup_storage


def _parse_cors_origins(value: str) -> list[str]:
    origins = list(dict.fromkeys(origin.strip() for origin in value.split(",") if origin.strip()))
    if "*" in origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS cannot contain '*'")
    return origins


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _warn_if_plaintext_off_host(url: str) -> None:
    """Document text is sent to the classifier. Plain http on loopback never leaves the
    machine, but plain http to another host puts it on the network unencrypted.
    Production already refuses http; outside production we warn instead of failing
    so a separate GPU box can still be used during development."""
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() == "http" and (parsed.hostname or "") not in _LOOPBACK_HOSTS:
        logging.getLogger("passbox.config").warning(
            "CLASSIFIER_SERVICE_URL uses plain http to %s: document text will cross the "
            "network unencrypted. Use https:// for any non-local classifier.",
            parsed.hostname,
        )


def _validate_runtime_settings(settings: Settings) -> None:
    environment = settings.app_env.strip().lower()
    if environment not in {"development", "test", "production"}:
        raise RuntimeError("APP_ENV must be development, test, or production")
    if settings.jwt_access_token_minutes <= 0:
        raise RuntimeError("JWT_ACCESS_TOKEN_MINUTES must be positive")
    if settings.login_rate_limit_attempts <= 0:
        raise RuntimeError("LOGIN_RATE_LIMIT_ATTEMPTS must be positive")
    if settings.login_rate_limit_window_seconds <= 0:
        raise RuntimeError("LOGIN_RATE_LIMIT_WINDOW_SECONDS must be positive")
    classifier_mode = settings.classifier_mode.strip().upper()
    if classifier_mode not in {"LOCAL_RULES", "REMOTE"}:
        raise RuntimeError("CLASSIFIER_MODE must be LOCAL_RULES or REMOTE")
    if settings.classifier_timeout_seconds <= 0:
        raise RuntimeError("CLASSIFIER_TIMEOUT_SECONDS must be positive")
    if classifier_mode == "REMOTE" and not settings.classifier_service_url.strip():
        raise RuntimeError("CLASSIFIER_SERVICE_URL is required when CLASSIFIER_MODE=REMOTE")
    if classifier_mode == "REMOTE":
        _warn_if_plaintext_off_host(settings.classifier_service_url)
    if settings.job_worker_threads <= 0:
        raise RuntimeError("JOB_WORKER_THREADS must be positive")
    gateway_mode = settings.gateway_mode.strip().upper()
    if gateway_mode not in {"MOCK", "LIVE"}:
        raise RuntimeError("GATEWAY_MODE must be MOCK or LIVE")

    if environment != "production":
        return

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required in production")
    if (
        len(settings.jwt_secret_key.strip()) < 32
        or settings.jwt_secret_key.strip() == "CHANGE_ME_TO_A_LONG_RANDOM_VALUE"
    ):
        raise RuntimeError("JWT_SECRET_KEY must be a strong production secret")
    if gateway_mode == "MOCK":
        raise RuntimeError("GATEWAY_MODE=MOCK is not allowed in production")
    if gateway_mode == "LIVE" and not (
        settings.openai_api_key.strip() or settings.anthropic_api_key.strip()
    ):
        raise RuntimeError(
            "OPENAI_API_KEY or ANTHROPIC_API_KEY is required when GATEWAY_MODE=LIVE"
        )
    if classifier_mode == "REMOTE":
        if not settings.classifier_service_url.strip().lower().startswith("https://"):
            raise RuntimeError("CLASSIFIER_SERVICE_URL must use HTTPS in production")
        if not settings.classifier_service_token.strip():
            raise RuntimeError(
                "CLASSIFIER_SERVICE_TOKEN is required in production when CLASSIFIER_MODE=REMOTE"
            )

    origins = _parse_cors_origins(settings.cors_allowed_origins)
    if not origins or any(not origin.lower().startswith("https://") for origin in origins):
        raise RuntimeError("production CORS_ALLOWED_ORIGINS must contain HTTPS origins only")


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


# API responses are JSON/PDF and never need to run script or be framed.
API_CONTENT_SECURITY_POLICY = "default-src 'none'; frame-ancestors 'none'"
HSTS_HEADER_VALUE = "max-age=31536000; includeSubDomains"


def _apply_security_headers(response, path: str = "", production: bool = False):
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    # The dev-only Swagger page loads its UI from a CDN, so it can't use the strict policy.
    if path != "/docs":
        response.headers.setdefault("Content-Security-Policy", API_CONTENT_SECURITY_POLICY)
    if production:
        response.headers.setdefault("Strict-Transport-Security", HSTS_HEADER_VALUE)
    return response


def _resolve_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


_IS_PRODUCTION = Settings().app_env.strip().lower() == "production"


_RETENTION_INTERVAL_SECONDS = 24 * 60 * 60
_retention_stop = threading.Event()


def _retention_loop() -> None:
    """Apply the retention policy once a day. Production only: in development it would
    silently delete demo documents; run cleanup_retention.py by hand there instead."""
    log = logging.getLogger("passbox.retention")
    delay = 60  # let startup finish, then once a day
    while not _retention_stop.wait(delay):
        delay = _RETENTION_INTERVAL_SECONDS
        try:
            summary = cleanup_storage(get_session_factory(), storage_root=Path(Settings().storage_root), apply=True)
            log.info("retention cleanup: %s files deleted, %s texts purged", summary["deleted_count"], summary["purged_text_count"])
        except Exception:
            log.exception("retention cleanup failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_worker()
    retention_thread = None
    if _IS_PRODUCTION:
        _retention_stop.clear()
        retention_thread = threading.Thread(target=_retention_loop, name="retention-cleanup", daemon=True)
        retention_thread.start()
    try:
        yield
    finally:
        _retention_stop.set()
        stop_worker()


app = FastAPI(
    title="PASSBOX Backend API",
    description=(
        "문서를 C(기밀)/S(민감)/O(공개)로 분류하고, 민감정보를 마스킹한 뒤 "
        "정책에 맞는 요청만 LLM Gateway로 내보내는 PASSBOX 백엔드 API입니다.\n\n"
        "### 인증 방법\n"
        "이 API는 거의 모든 엔드포인트에 로그인 토큰이 필요합니다 (자물쇠 아이콘이 있는 항목).\n"
        "1. **`POST /api/v1/auth/login`**을 Try it out으로 호출해 로그인합니다.\n"
        "2. 응답의 `access_token` 값을 복사합니다 (따옴표 제외, `Bearer ` 접두어 없이 토큰 문자열만).\n"
        "3. 이 페이지 위쪽의 **Authorize** 버튼을 눌러 `Value` 칸에 붙여넣고 Authorize를 누릅니다.\n"
        "4. 이후 모든 요청에 토큰이 자동으로 첨부됩니다. 토큰이 없으면 보호된 엔드포인트는 `401 Not authenticated`를 반환합니다."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    # In production the full API map is not handed to anonymous visitors.
    openapi_url=None if _IS_PRODUCTION else "/openapi.json",
)

_SWAGGER_FAVICON = "data:image/svg+xml," + quote(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<path d='M16 2 4 7v9c0 8 5 12.5 12 14 7-1.5 12-6 12-14V7z' fill='#1c2333'/>"
    "<path d='M16 6 8 9.5v6.5c0 6 3.6 9.5 8 10.6 4.4-1.1 8-4.6 8-10.6V9.5z' fill='#c9673c'/>"
    "<path d='M12 16.5l2.7 2.7L20.5 13' stroke='#f5f2ea' stroke-width='2.2' "
    "fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>"
)

_ENV_BADGE = {
    "development": ("DEVELOPMENT", "#a85a1e", "#f7e8cd"),
    "test": ("TEST", "#3a5a8a", "#dde7f4"),
    "production": ("PRODUCTION", "#a8281e", "#f6e0dc"),
}


def _swagger_custom_markup(environment: str) -> tuple[str, str]:
    label, fg, bg = _ENV_BADGE.get(environment, (environment.upper() or "UNKNOWN", "#3a5a8a", "#dde7f4"))

    css = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap">
<style>
  :root {
    --pb-bg: #f5f2ea;
    --pb-surface: #ffffff;
    --pb-surface-2: #faf8f2;
    --pb-border: #ddd6c4;
    --pb-ink: #232016;
    --pb-ink-dim: #6b6656;
    --pb-accent: #a8501e;
    --pb-accent-dim: #f1e2da;
    --pb-grade-c: #a8281e;
    --pb-grade-s: #a87a1e;
    --pb-grade-o: #2c6b45;
  }
  html { background: var(--pb-bg); }
  body {
    background: var(--pb-bg) !important;
    font-family: 'Noto Sans KR', 'Segoe UI', sans-serif;
  }
  .pb-stripe {
    height: 5px;
    width: 100%;
    background: linear-gradient(90deg,
      var(--pb-grade-c) 0%, var(--pb-grade-c) 33.3%,
      var(--pb-grade-s) 33.3%, var(--pb-grade-s) 66.6%,
      var(--pb-grade-o) 66.6%, var(--pb-grade-o) 100%);
  }
  .pb-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    padding: 22px 34px;
    background: radial-gradient(1100px 260px at 12% -40%, rgba(168,80,30,0.08), transparent),
                var(--pb-surface);
    border-bottom: 1px solid var(--pb-border);
  }
  .pb-wordmark {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 26px;
    letter-spacing: 0.02em;
    color: var(--pb-ink);
  }
  .pb-wordmark span { color: var(--pb-accent); }
  .pb-tagline {
    font-size: 13px;
    color: var(--pb-ink-dim);
    margin-top: 3px;
    letter-spacing: 0.01em;
  }
  .pb-env-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 6px 14px;
    border-radius: 100px;
    border: 1px solid currentColor;
    color: __ENV_FG__;
    background: __ENV_BG__;
  }
  .pb-auth-hint {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--pb-accent);
    background: var(--pb-accent-dim);
    border: 1px dashed var(--pb-accent);
    border-radius: 8px;
    padding: 9px 14px;
    margin: 18px 34px 0;
    display: inline-block;
  }

  .swagger-ui, .swagger-ui .scheme-container { background: transparent; }
  .swagger-ui .scheme-container {
    box-shadow: none;
    border-bottom: 1px solid var(--pb-border);
    padding: 18px 0;
  }
  .swagger-ui .info { margin: 24px 0; }
  .swagger-ui .info .title, .swagger-ui .info h1, .swagger-ui .info h2, .swagger-ui .info h3 {
    color: var(--pb-ink);
    font-family: 'JetBrains Mono', monospace;
  }
  .swagger-ui .info p, .swagger-ui .info li, .swagger-ui .markdown p, .swagger-ui .renderedMarkdown p {
    color: var(--pb-ink-dim);
  }
  .swagger-ui .info a, .swagger-ui .renderedMarkdown a { color: var(--pb-accent); }
  .swagger-ui .info code, .swagger-ui .renderedMarkdown code {
    background: var(--pb-surface-2);
    color: var(--pb-accent);
    border-radius: 4px;
  }

  .swagger-ui .btn.authorize {
    color: var(--pb-accent);
    border-color: var(--pb-accent);
    background: var(--pb-accent-dim);
    font-weight: 700;
    padding: 8px 18px;
    box-shadow: 0 0 0 3px rgba(168,80,30,0.10);
  }
  .swagger-ui .btn.authorize svg { fill: var(--pb-accent); }
  .swagger-ui .btn.execute { background: var(--pb-accent); border-color: var(--pb-accent); color: #f5f2ea; font-weight: 700; }
  .swagger-ui .btn.cancel { border-color: #e0645a; color: #e0645a; }
  .swagger-ui .btn { border-radius: 7px; }

  .swagger-ui .opblock-tag {
    color: var(--pb-ink);
    border-bottom-color: var(--pb-border);
    font-family: 'JetBrains Mono', monospace;
  }
  .swagger-ui .opblock-tag:hover { background: var(--pb-surface); }
  .swagger-ui .opblock-tag small { color: var(--pb-ink-dim); }

  .swagger-ui .opblock {
    background: var(--pb-surface);
    border-radius: 9px;
    border-width: 0 0 0 4px;
    box-shadow: 0 1px 3px rgba(35,32,22,0.08);
  }
  .swagger-ui .opblock .opblock-summary { border-color: var(--pb-border); }
  .swagger-ui .opblock .opblock-summary-path, .swagger-ui .opblock .opblock-summary-path__deprecated { color: var(--pb-ink); }
  .swagger-ui .opblock .opblock-summary-description { color: var(--pb-ink-dim); }
  .swagger-ui .opblock.opblock-get { border-color: #5a9ce0; background: rgba(90,156,224,0.06); }
  .swagger-ui .opblock.opblock-get .opblock-summary-method { background: #5a9ce0; }
  .swagger-ui .opblock.opblock-post { border-color: var(--pb-grade-o); background: rgba(90,196,138,0.06); }
  .swagger-ui .opblock.opblock-post .opblock-summary-method { background: var(--pb-grade-o); color: #f5f2ea; }
  .swagger-ui .opblock.opblock-put { border-color: var(--pb-grade-s); background: rgba(224,178,90,0.06); }
  .swagger-ui .opblock.opblock-put .opblock-summary-method { background: var(--pb-grade-s); color: #f5f2ea; }
  .swagger-ui .opblock.opblock-delete { border-color: var(--pb-grade-c); background: rgba(224,100,90,0.06); }
  .swagger-ui .opblock.opblock-delete .opblock-summary-method { background: var(--pb-grade-c); }
  .swagger-ui .opblock .opblock-summary-method { border-radius: 5px; font-family: 'JetBrains Mono', monospace; }
  .swagger-ui .opblock-body { background: var(--pb-surface-2); }
  .swagger-ui .opblock-description-wrapper, .swagger-ui .opblock-external-docs-wrapper, .swagger-ui .opblock-title_normal {
    color: var(--pb-ink-dim);
  }
  .swagger-ui .opblock-section-header { background: var(--pb-surface-2); box-shadow: none; border-bottom: 1px solid var(--pb-border); }
  .swagger-ui .opblock-section-header h4, .swagger-ui .opblock-section-header label { color: var(--pb-ink); }

  .swagger-ui table thead tr td, .swagger-ui table thead tr th { color: var(--pb-ink-dim); border-color: var(--pb-border); }
  .swagger-ui .parameters-col_description, .swagger-ui .response-col_description { color: var(--pb-ink-dim); }
  .swagger-ui .parameter__name { color: var(--pb-ink); }
  .swagger-ui .parameter__type, .swagger-ui .parameter__deprecated, .swagger-ui .parameter__in { color: var(--pb-ink-dim); }
  .swagger-ui .tab li button.tablinks { color: var(--pb-ink-dim); }
  .swagger-ui .responses-inner h4, .swagger-ui .responses-inner h5 { color: var(--pb-ink); }
  .swagger-ui .response-col_status { color: var(--pb-ink); font-family: 'JetBrains Mono', monospace; }

  .swagger-ui input[type=text], .swagger-ui input[type=password], .swagger-ui textarea, .swagger-ui select {
    background: var(--pb-bg);
    color: var(--pb-ink);
    border: 1px solid var(--pb-border);
    border-radius: 6px;
  }
  .swagger-ui input:focus, .swagger-ui textarea:focus, .swagger-ui select:focus {
    border-color: var(--pb-accent);
    outline: none;
  }
  .swagger-ui .highlight-code, .swagger-ui .microlight { background: #0a0c10 !important; border-radius: 7px; }
  .swagger-ui section.models { border-color: var(--pb-border); background: var(--pb-surface); }
  .swagger-ui section.models .model-container { background: var(--pb-surface-2); }
  .swagger-ui .model, .swagger-ui .model-title { color: var(--pb-ink-dim); }
  .swagger-ui .model-box { background: var(--pb-surface-2); }

  .swagger-ui .dialog-ux .modal-ux { background: var(--pb-surface); border-color: var(--pb-border); }
  .swagger-ui .dialog-ux .modal-ux-header h3 { color: var(--pb-ink); }
  .swagger-ui .dialog-ux .modal-ux-content p, .swagger-ui .dialog-ux .modal-ux-content label { color: var(--pb-ink-dim); }

  .swagger-ui ::-webkit-scrollbar { width: 10px; height: 10px; }
  .swagger-ui ::-webkit-scrollbar-thumb { background: var(--pb-border); border-radius: 6px; }
  .swagger-ui .wrapper { max-width: 1180px; }
</style>
"""
    css = css.replace("__ENV_FG__", fg).replace("__ENV_BG__", bg)

    body = """
<div class="pb-stripe"></div>
<header class="pb-hero">
  <div>
    <div class="pb-wordmark">PASS<span>BOX</span></div>
    <div class="pb-tagline">C / S / O 문서 보안 파이프라인 &middot; LLM Gateway 통제</div>
  </div>
  <span class="pb-env-badge">__ENV_LABEL__</span>
</header>
<div class="pb-auth-hint">🔒 보호된 엔드포인트를 쓰려면: /auth/login 실행 → access_token 복사 → 위 "Authorize" 버튼에 붙여넣기</div>
"""
    body = body.replace("__ENV_LABEL__", label)

    return css, body


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui_html() -> HTMLResponse:
    if _IS_PRODUCTION:
        raise HTTPException(status_code=404, detail="Not Found")
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - Docs",
        swagger_favicon_url=_SWAGGER_FAVICON,
        swagger_ui_parameters={
            "docExpansion": "list",
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
            "filter": True,
            "syntaxHighlight.theme": "nord",
            "persistAuthorization": True,
        },
    )
    css, body = _swagger_custom_markup(Settings().app_env.strip().lower())
    html = response.body.decode("utf-8")
    html = html.replace("</head>", css + "</head>")
    html = html.replace('<div id="swagger-ui">', body + '<div id="swagger-ui">')
    return HTMLResponse(html)

settings = Settings()
_validate_runtime_settings(settings)
cors_origins = _parse_cors_origins(settings.cors_allowed_origins)

# 로컬 프론트엔드 개발용 CORS 설정입니다.
# 운영 배포 시에는 실제 프론트엔드 주소만 남겨야 합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    return _apply_security_headers(response, request.url.path, _IS_PRODUCTION)


@app.middleware("http")
async def request_id_middleware(request, call_next):
    request_id = _resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response

app.include_router(auth_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(extraction_router, prefix="/api/v1")
app.include_router(scans_router, prefix="/api/v1")
app.include_router(classifications_router, prefix="/api/v1")
app.include_router(outbound_router, prefix="/api/v1")
app.include_router(gateway_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
app.include_router(sensitive_keywords_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(support_router, prefix="/api/v1")
app.include_router(review_requests_router, prefix="/api/v1")
app.include_router(siem_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "PASSBOX Backend API",
    }


@app.get("/api/v1/health/ready")
def readiness_check():
    try:
        check_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="service is not ready",
        ) from exc

    return {
        "status": "ready",
        "service": "PASSBOX Backend API",
        "database": "connected",
    }


@app.get("/api/v1/db-check")
def database_check():
    try:
        check_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="database connection failed",
        ) from exc

    return {
        "status": "ok",
        "database": "connected",
    }
