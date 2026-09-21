import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.approvals import _allowed_approval_roles
from app.api.approvals import retry_approved_request, retryable_approvals
from app.db import Base
from app.gateway import GatewayConfigurationError
from app.models import (
    Document,
    GatewayTransmission,
    Job,
    OutboundApproval,
    Request,
    Tenant,
    User,
)


class ApprovalPolicyRoleTests(unittest.TestCase):
    def test_policy_roles_are_used_with_security_admin_override(self):
        roles = _allowed_approval_roles({"approver_roles": ["ADMIN"]})

        self.assertEqual(roles, {"ADMIN", "SECURITY_ADMIN"})

    def test_invalid_or_empty_policy_roles_use_safe_defaults(self):
        roles = _allowed_approval_roles({"approver_roles": ["USER", ""]})

        self.assertEqual(roles, {"APPROVER", "ADMIN", "SECURITY_ADMIN"})


class ApprovalRetryTests(unittest.TestCase):
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

    def _seed_failed_approval(self):
        with self.Session() as db:
            tenant = Tenant(name="Retry Tenant")
            db.add(tenant)
            db.flush()
            user = User(
                tenant_id=tenant.id,
                username="retry.approver",
                display_name="Retry Approver",
                password_hash="unused",
                role="APPROVER",
            )
            db.add(user)
            db.flush()
            document = Document(
                tenant_id=tenant.id,
                uploaded_by=user.id,
                original_filename="safe.pdf",
                storage_key="safe.pdf",
                extension=".pdf",
                mime_type="application/pdf",
                size_bytes=10,
                sha256="a" * 64,
                status="READY_FOR_PARSING",
            )
            db.add(document)
            db.flush()
            request = Request(
                tenant_id=tenant.id,
                user_id=user.id,
                document_id=document.id,
                mode="DOCUMENT",
                status="FAILED",
            )
            db.add(request)
            db.flush()
            job = Job(
                request_id=request.id,
                status="FAILED",
                progress=100,
                error_message="Gateway request failed.",
            )
            db.add(job)
            transmission = GatewayTransmission(
                tenant_id=tenant.id,
                document_id=document.id,
                user_id=user.id,
                provider="openai",
                model="gpt-4o-mini",
                payload_hash="b" * 64,
                policy_version="LOCAL-TEMPLATE-v1",
                confirmed_grade="S",
                policy_decision="APPROVED",
                status="FAILED",
                error_message="Gateway request failed.",
            )
            db.add(transmission)
            db.flush()
            approval = OutboundApproval(
                tenant_id=tenant.id,
                document_id=document.id,
                requested_by=user.id,
                gateway_transmission_id=transmission.id,
                provider="openai",
                model="gpt-4o-mini",
                payload_hash="b" * 64,
                masked_payload_hash="c" * 64,
                masked_payload="masked payload only",
                masking_version="rules-mask-v1",
                masking_categories="EMAIL",
                status="APPROVED",
                decided_by=user.id,
            )
            db.add(approval)
            db.commit()
            return approval.id, user.id, tenant.id

    def test_retry_reuses_masked_payload_and_completes(self):
        approval_id, user_id, tenant_id = self._seed_failed_approval()

        class FakeGateway:
            def __init__(self):
                self.prompt = None

            def send(self, **kwargs):
                self.prompt = kwargs["prompt"]
                return type("GatewayResponse", (), {"content": "safe response"})()

        fake_gateway = FakeGateway()
        with self.Session() as db:
            user = db.get(User, user_id)
        with (
            patch("app.api.approvals.get_session_factory", return_value=self.Session),
            patch("app.api.approvals.gateway", fake_gateway),
        ):
            response = retry_approved_request(approval_id, user)

        self.assertEqual(response.transmission_status, "COMPLETED")
        self.assertEqual(response.post_inspection_status, "PASSED")
        self.assertEqual(fake_gateway.prompt, "masked payload only")
        with self.Session() as db:
            transmission = db.scalar(select(GatewayTransmission))
            job = db.scalar(select(Job))
            request = db.scalar(select(Request))
            self.assertEqual(transmission.status, "COMPLETED")
            self.assertEqual(job.status, "COMPLETED")
            self.assertEqual(request.status, "COMPLETED")

    def test_retryable_list_contains_only_failed_transmissions(self):
        _approval_id, user_id, _tenant_id = self._seed_failed_approval()

        with self.Session() as db:
            user = db.get(User, user_id)
        with patch(
            "app.api.approvals.get_session_factory", return_value=self.Session
        ):
            items = retryable_approvals(user)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].status, "APPROVED")
        self.assertEqual(items[0].transmission_status, "FAILED")

    def test_retry_failure_keeps_approval_and_records_failed_attempt(self):
        approval_id, user_id, _tenant_id = self._seed_failed_approval()

        class FailingGateway:
            def send(self, **_kwargs):
                raise GatewayConfigurationError("Gateway is not configured")

        with self.Session() as db:
            user = db.get(User, user_id)
        with (
            patch("app.api.approvals.get_session_factory", return_value=self.Session),
            patch("app.api.approvals.gateway", FailingGateway()),
        ):
            with self.assertRaises(HTTPException) as context:
                retry_approved_request(approval_id, user)

        self.assertEqual(context.exception.status_code, 503)
        with self.Session() as db:
            approval = db.scalar(select(OutboundApproval))
            transmission = db.scalar(select(GatewayTransmission))
            job = db.scalar(select(Job))
            self.assertEqual(approval.status, "APPROVED")
            self.assertEqual(transmission.status, "FAILED")
            self.assertEqual(job.status, "FAILED")


if __name__ == "__main__":
    unittest.main()
