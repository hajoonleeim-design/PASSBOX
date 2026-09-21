from getpass import getpass
import os

from sqlalchemy import select

from app.db import get_session_factory
from app.models import Tenant, User
from app.security import hash_password


if __name__ == "__main__":
    password = getpass("테스트 사용자 비밀번호를 입력하세요: ")
    if not password:
        raise SystemExit("비밀번호가 비어 있습니다.")

    demo_role = os.getenv("DEMO_USER_ROLE", "OPERATOR").strip().upper()
    allowed_roles = {"USER", "OPERATOR", "APPROVER", "SECURITY_ADMIN", "ADMIN"}
    if demo_role not in allowed_roles:
        raise SystemExit(f"지원하지 않는 DEMO_USER_ROLE입니다: {demo_role}")

    session_factory = get_session_factory()
    with session_factory() as db:
        tenant = db.scalar(
            select(Tenant).where(Tenant.name == "PASSBOX 테스트 기관")
        )
        if tenant is None:
            tenant = Tenant(name="PASSBOX 테스트 기관")
            db.add(tenant)
            db.flush()

        user = db.scalar(
            select(User).where(
                User.tenant_id == tenant.id,
                User.username == "demo.user",
            )
        )
        if user is None:
            user = User(
                tenant_id=tenant.id,
                username="demo.user",
                display_name="테스트 사용자",
                password_hash=hash_password(password),
                role=demo_role,
            )
            db.add(user)
        else:
            user.password_hash = hash_password(password)
            user.status = "ACTIVE"
            user.role = demo_role

        db.commit()
        print(f"테스트 기관 ID: {tenant.id}")
        print("테스트 사용자: demo.user")
        print(f"테스트 사용자 역할: {demo_role}")
        print("테스트 사용자 등록 완료")
