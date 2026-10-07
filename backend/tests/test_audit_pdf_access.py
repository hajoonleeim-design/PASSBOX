import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.audit import generate_audit_pdf
from app.db import Base
from app.models import ClassificationDecision, Document, Request, Tenant, User


class AuditPdfOwnershipTests(unittest.TestCase):
    """A plain USER may only ever fetch the audit PDF for their own request.

    OPERATOR/SECURITY_ADMIN/ADMIN keep tenant-wide access (unchanged
    behaviour from before this test existed); only the USER-role path is
    new and needs covering here.
    """

    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _seed_request(self, *, requester_role: str):
        with self.Session() as db:
            tenant = Tenant(name="T")
            db.add(tenant); db.flush()
            owner = User(tenant_id=tenant.id, username="owner", display_name="Owner", password_hash="x", role=requester_role)
            other_user = User(tenant_id=tenant.id, username="other", display_name="Other", password_hash="x", role="USER")
            operator = User(tenant_id=tenant.id, username="op", display_name="Op", password_hash="x", role="OPERATOR")
            db.add_all([owner, other_user, operator]); db.flush()
            document = Document(tenant_id=tenant.id, uploaded_by=owner.id, original_filename="f.pdf", storage_key="f.pdf", extension=".pdf", mime_type="application/pdf", size_bytes=1, sha256="a" * 64, status="READY_FOR_PARSING")
            db.add(document); db.flush()
            request = Request(tenant_id=tenant.id, user_id=owner.id, document_id=document.id, mode="DOCUMENT", status="RECEIVED")
            db.add(request); db.flush()
            decision = ClassificationDecision(tenant_id=tenant.id, document_id=document.id, user_id=operator.id, confirmed_grade="O")
            db.add(decision); db.commit()
            return request.id, owner.id, other_user.id, operator.id, tenant.id

    def _user(self, user_id: int):
        with self.Session() as db:
            return db.get(User, user_id)

    def test_owner_can_fetch_their_own_pdf(self):
        request_id, owner_id, _other_id, _op_id, _tenant_id = self._seed_request(requester_role="USER")
        owner = self._user(owner_id)
        with patch("app.api.audit.get_session_factory", return_value=self.Session):
            response = generate_audit_pdf(request_id, owner)
        self.assertEqual(response.media_type, "application/pdf")

    def test_other_user_is_forbidden(self):
        request_id, _owner_id, other_id, _op_id, _tenant_id = self._seed_request(requester_role="USER")
        other = self._user(other_id)
        with patch("app.api.audit.get_session_factory", return_value=self.Session):
            with self.assertRaises(HTTPException) as ctx:
                generate_audit_pdf(request_id, other)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_operator_keeps_tenant_wide_access(self):
        request_id, _owner_id, _other_id, op_id, _tenant_id = self._seed_request(requester_role="USER")
        operator = self._user(op_id)
        with patch("app.api.audit.get_session_factory", return_value=self.Session):
            response = generate_audit_pdf(request_id, operator)
        self.assertEqual(response.media_type, "application/pdf")

    def test_unknown_request_is_not_found_not_forbidden(self):
        _request_id, owner_id, _other_id, _op_id, _tenant_id = self._seed_request(requester_role="USER")
        owner = self._user(owner_id)
        with patch("app.api.audit.get_session_factory", return_value=self.Session):
            with self.assertRaises(HTTPException) as ctx:
                generate_audit_pdf(999999, owner)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
