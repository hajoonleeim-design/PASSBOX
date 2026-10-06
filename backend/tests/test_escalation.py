import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.approvals import pending_approvals
from app.api.review_requests import CreateReviewRequest, create_review_request, list_review_requests
from app.db import Base, Settings
from app.escalation import hours_pending, is_escalated
from app.models import (
    ClassificationDecision,
    Document,
    GatewayTransmission,
    OutboundApproval,
    Tenant,
    User,
)


class EscalationHelperTests(unittest.TestCase):
    def test_hours_pending_computes_elapsed_time(self):
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        created = now - timedelta(hours=2, minutes=30)
        self.assertAlmostEqual(hours_pending(created, now=now), 2.5, places=2)

    def test_is_escalated_respects_threshold(self):
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        just_under = now - timedelta(hours=3, minutes=59)
        just_over = now - timedelta(hours=4, minutes=1)
        with patch("app.escalation.Settings") as mock_settings:
            mock_settings.return_value.escalation_hours = 4.0
            self.assertFalse(is_escalated(just_under, now=now))
            self.assertTrue(is_escalated(just_over, now=now))


class QueueEscalationFlagTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _seed_approval(self, created_at: datetime):
        with self.Session() as db:
            tenant = Tenant(name="Escalation Tenant")
            db.add(tenant)
            db.flush()
            user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash="x", role="APPROVER")
            db.add(user)
            db.flush()
            document = Document(
                tenant_id=tenant.id, uploaded_by=user.id, original_filename="f.pdf", storage_key="f.pdf",
                extension=".pdf", mime_type="application/pdf", size_bytes=1, sha256="a" * 64, status="READY",
            )
            db.add(document)
            db.flush()
            transmission = GatewayTransmission(
                tenant_id=tenant.id, document_id=document.id, user_id=user.id, provider="openai", model="gpt",
                payload_hash="b" * 64, policy_version="v1", confirmed_grade="S", policy_decision="APPROVAL_REQUIRED",
                status="WAITING_APPROVAL",
            )
            db.add(transmission)
            db.flush()
            approval = OutboundApproval(
                tenant_id=tenant.id, document_id=document.id, requested_by=user.id,
                gateway_transmission_id=transmission.id, provider="openai", model="gpt", payload_hash="b" * 64,
                masked_payload_hash="c" * 64, masked_payload="masked", masking_version="v1", status="PENDING",
                created_at=created_at,
            )
            db.add(approval)
            db.commit()
            return user.id, tenant.id

    def test_old_pending_approval_is_flagged_escalated(self):
        old = datetime.now(timezone.utc) - timedelta(hours=10)
        user_id, _tenant_id = self._seed_approval(old)
        with self.Session() as db:
            user = db.get(User, user_id)
        with patch("app.api.approvals.get_session_factory", return_value=self.Session):
            items = pending_approvals(user)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].is_escalated)
        self.assertGreaterEqual(items[0].hours_pending, 9.9)

    def test_fresh_pending_approval_is_not_escalated(self):
        recent = datetime.now(timezone.utc) - timedelta(minutes=5)
        user_id, _tenant_id = self._seed_approval(recent)
        with self.Session() as db:
            user = db.get(User, user_id)
        with patch("app.api.approvals.get_session_factory", return_value=self.Session):
            items = pending_approvals(user)
        self.assertFalse(items[0].is_escalated)


class ReviewRequestEscalationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_review_request_escalation_flag_after_threshold(self):
        with self.Session() as db:
            tenant = Tenant(name="Review Escalation Tenant")
            db.add(tenant)
            db.flush()
            user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash="x", role="USER")
            operator = User(tenant_id=tenant.id, username="op", display_name="Op", password_hash="x", role="OPERATOR")
            db.add_all([user, operator])
            db.flush()
            document = Document(
                tenant_id=tenant.id, uploaded_by=user.id, original_filename="f.hwp", storage_key="f.hwp",
                extension=".hwp", mime_type="application/x-hwp", size_bytes=1, sha256="a" * 64,
                status="CLASSIFICATION_CONFIRMED",
            )
            db.add(document)
            db.flush()
            decision = ClassificationDecision(
                tenant_id=tenant.id, document_id=document.id, user_id=operator.id, confirmed_grade="C",
            )
            db.add(decision)
            db.commit()
            document_id, user_id, operator_id = document.id, user.id, operator.id

        with self.Session() as db:
            user = db.get(User, user_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            created = create_review_request(document_id, CreateReviewRequest(reason="사유"), user)

        # 생성 시각을 과거로 되돌려 에스컬레이션 기준을 넘긴 상태를 만든다.
        from app.models import ReviewRequest
        with self.Session() as db:
            item = db.get(ReviewRequest, created.review_request_id)
            item.created_at = datetime.now(timezone.utc) - timedelta(hours=9)
            db.commit()

        with self.Session() as db:
            operator_user = db.get(User, operator_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            items = list_review_requests(operator_user)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].is_escalated)


if __name__ == "__main__":
    unittest.main()
