import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import PasswordChangeRequest, change_password, get_current_user, logout
from app.db import Base
from app.models import Tenant, User
from app.security import create_access_token, hash_password


class TokenRevocationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            tenant = Tenant(name="T")
            db.add(tenant); db.flush()
            user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash=hash_password("old-password-123"), role="USER")
            db.add(user); db.commit()
            self.user_id, self.tenant_id = user.id, tenant.id
        self.patcher = patch("app.api.auth.get_session_factory", return_value=self.Session)
        self.patcher.start()
        self.env = patch.dict("os.environ", {"JWT_SECRET_KEY": "x" * 64})
        self.env.start()

    def tearDown(self):
        self.patcher.stop()
        self.env.stop()
        self.engine.dispose()

    def _creds(self, token):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    def _token(self):
        return create_access_token(self.user_id, self.tenant_id, "USER")

    def test_logged_out_token_is_rejected_but_new_login_works(self):
        token = self._token()
        user = get_current_user(self._creds(token))
        logout(self._creds(token), user)
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(self._creds(token))
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(get_current_user(self._creds(self._token())).id, self.user_id)

    def test_password_change_kills_tokens_issued_before_it(self):
        stolen = self._token()
        time.sleep(1.1)
        user = get_current_user(self._creds(stolen))
        change_password(PasswordChangeRequest(current_password="old-password-123", new_password="new-password-456"), user)
        with self.assertRaises(HTTPException):
            get_current_user(self._creds(stolen))
        self.assertEqual(get_current_user(self._creds(self._token())).id, self.user_id)


if __name__ == "__main__":
    unittest.main()


class LoginAuditTests(TokenRevocationTests):
    def test_failed_and_successful_logins_are_chained(self):
        from types import SimpleNamespace

        from sqlalchemy import select

        from app.api.auth import LoginRequest, login
        from app.models import AuditLogEntry
        from app.rate_limit import login_rate_limiter

        request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.9"))
        login_rate_limiter.reset(f"203.0.113.9:{self.tenant_id}:u")
        with self.assertRaises(HTTPException):
            login(LoginRequest(tenant_id=self.tenant_id, username="u", password="wrong-password"), request)
        login(LoginRequest(tenant_id=self.tenant_id, username="u", password="old-password-123"), request)
        with self.Session() as db:
            events = [e.event_type for e in db.scalars(select(AuditLogEntry).order_by(AuditLogEntry.sequence))]
            failed = db.scalars(select(AuditLogEntry).where(AuditLogEntry.event_type == "LOGIN_FAILED")).one()
        self.assertEqual(events, ["LOGIN_FAILED", "LOGIN_SUCCEEDED"])
        self.assertEqual(failed.payload["client_ip"], "203.0.113.9")
        self.assertNotIn("wrong-password", str(failed.payload))


class AccountLockoutTests(TokenRevocationTests):
    def test_account_locks_after_repeated_failures_even_across_ips(self):
        from types import SimpleNamespace

        from app.api.auth import ACCOUNT_LOCK_FAILURES, LoginRequest, login

        for attempt in range(ACCOUNT_LOCK_FAILURES):
            request = SimpleNamespace(client=SimpleNamespace(host=f"198.51.100.{attempt}"))
            with self.assertRaises(HTTPException) as ctx:
                login(LoginRequest(tenant_id=self.tenant_id, username="u", password="wrong"), request)
            self.assertEqual(ctx.exception.status_code, 401)
        request = SimpleNamespace(client=SimpleNamespace(host="198.51.100.250"))
        with self.assertRaises(HTTPException) as ctx:
            login(LoginRequest(tenant_id=self.tenant_id, username="u", password="old-password-123"), request)
        self.assertEqual(ctx.exception.status_code, 429)
