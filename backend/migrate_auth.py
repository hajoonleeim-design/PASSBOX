from sqlalchemy import text

from app.db import get_engine


if __name__ == "__main__":
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) "
                "NOT NULL DEFAULT ''"
            )
        )
    engine.dispose()
    print("인증용 users.password_hash 컬럼 준비 완료")
