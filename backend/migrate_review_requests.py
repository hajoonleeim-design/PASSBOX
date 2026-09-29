from app import models  # noqa: F401 - registers review_requests model with SQLAlchemy
from app.db import Base, get_engine


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    print("재검토 요청 테이블 준비 완료: review_requests")
