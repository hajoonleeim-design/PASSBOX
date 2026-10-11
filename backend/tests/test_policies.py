import unittest

from app.api.policies import _next_version


class PolicyVersionTests(unittest.TestCase):
    def test_increments_local_template_version(self):
        self.assertEqual(_next_version("LOCAL-TEMPLATE-v1"), "LOCAL-TEMPLATE-v2")

    def test_increments_numeric_suffix(self):
        self.assertEqual(_next_version("POLICY-v1.3"), "POLICY-v1.4")

    def test_adds_suffix_when_version_has_no_number(self):
        self.assertEqual(_next_version("POLICY"), "POLICY-2")


if __name__ == "__main__":
    unittest.main()


class BuiltinDetectionPatternTests(unittest.TestCase):
    """The admin screen's detection-rule list used to be two hard-coded rows whose
    on/off switch the scanner never read. It must mirror the scanner exactly."""

    def test_admin_list_matches_every_scanner_rule(self):
        from app.api.policies import BUILTIN_DETECTION_PATTERNS
        from app.security_scan import _RULES

        listed = {p["pattern_id"].removeprefix("builtin-").upper() for p in BUILTIN_DETECTION_PATTERNS}
        self.assertEqual(listed, {rule.category for rule in _RULES})
        self.assertTrue(all(p["enabled"] for p in BUILTIN_DETECTION_PATTERNS))
        self.assertTrue(all(p["description"] for p in BUILTIN_DETECTION_PATTERNS))


class FirstVisitPolicyHistoryTests(unittest.TestCase):
    """기관의 첫 방문에서는 정책 조회와 이력 조회가 동시에 오므로 이력은 빈 목록이어야 한다."""

    def setUp(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.db import Base
        from app.models import Tenant, User

        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            tenant = Tenant(name="First Visit Tenant")
            db.add(tenant)
            db.flush()
            self.admin = User(
                tenant_id=tenant.id, username="policy.admin", display_name="관리자",
                password_hash="x", role="ADMIN",
            )
            db.add(self.admin)
            db.commit()
            db.refresh(self.admin)

    def test_history_of_uncreated_current_policy_is_empty_not_404(self):
        from unittest.mock import patch

        from fastapi import HTTPException

        from app.api.policies import get_policy_history

        with patch("app.api.policies.get_session_factory", return_value=self.Session):
            self.assertEqual(get_policy_history("mock-current", self.admin), [])
            with self.assertRaises(HTTPException) as caught:
                get_policy_history("999", self.admin)
        self.assertEqual(caught.exception.status_code, 404)
