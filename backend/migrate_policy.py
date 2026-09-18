from app import models  # noqa: F401 - registers policy models with SQLAlchemy
from app.db import Base, get_engine


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    print("정책·채팅 관리 테이블 준비 완료: security_policies, security_policy_histories, chat_requests")
