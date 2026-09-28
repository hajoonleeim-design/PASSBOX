from app import models  # noqa: F401 - registers the audit log model with SQLAlchemy
from app.db import Base, get_engine


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    print("감사 로그 해시 체인 테이블 준비 완료: audit_log_entries")
