from app import models  # noqa: F401 - registers the sensitive keyword model with SQLAlchemy
from app.db import Base, get_engine


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    print("기밀 키워드 테이블 준비 완료: sensitive_keywords")
