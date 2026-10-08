from app import models  # noqa: F401 - registers token revocation models with SQLAlchemy
from app.db import Base, get_engine


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    print("토큰 무효화 테이블 준비 완료: revoked_tokens, token_cutoffs")
