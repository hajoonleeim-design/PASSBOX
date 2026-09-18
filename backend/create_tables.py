from app.db import Base, get_engine
from app import models  # noqa: F401 - registers the models with SQLAlchemy


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    print("PASSBOX 기본 테이블 생성 완료: tenants, users")
