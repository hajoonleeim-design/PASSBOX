import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.audit import get_audit
from app.db import Base
from app.models import Document, Job, Request, Tenant, User


class PendingClassificationAuditTests(unittest.TestCase):
    """A document that has not reached a final C/S/O decision yet used to 404 the
    whole audit record, which is why some documents "worked" in the audit screen
    and others didn't -- it tracked whether classification had happened, not
    whether the request existed. It should instead return the events that did
    happen so far."""

    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _seed(self, *, job_status: str):
        with self.Session() as db:
            tenant = Tenant(name="T")
            db.add(tenant); db.flush()
            operator = User(tenant_id=tenant.id, username="op", display_name="Op", password_hash="x", role="OPERATOR")
            db.add(operator); db.flush()
            document = Document(tenant_id=tenant.id, uploaded_by=operator.id, original_filename="f.pdf", storage_key="f.pdf", extension=".pdf", mime_type="application/pdf", size_bytes=1, sha256="a" * 64, status="READY_FOR_CLASSIFICATION")
            db.add(document); db.flush()
            request = Request(tenant_id=tenant.id, user_id=operator.id, document_id=document.id, mode="DOCUMENT", status="RECEIVED")
            db.add(request); db.flush()
            job = Job(request_id=request.id, status=job_status, progress=50)
            db.add(job); db.commit()
            return request.id, operator.id

    def test_unclassified_document_returns_events_instead_of_404(self):
        request_id, operator_id = self._seed(job_status="CLASSIFICATION_REVIEW")
        with self.Session() as db:
            operator = db.get(User, operator_id)
        with patch("app.api.audit.get_session_factory", return_value=self.Session):
            record = get_audit(request_id, operator)
        self.assertEqual(record.grade, "PENDING")
        event_types = {event.event_type for event in record.events}
        self.assertIn("REQUEST_CREATED", event_types)
        self.assertIn("ANALYSIS_STARTED", event_types)
        self.assertNotIn("DECISION_CREATED", event_types)

    def test_scan_blocked_document_shows_blocked_event(self):
        request_id, operator_id = self._seed(job_status="BLOCKED")
        with self.Session() as db:
            operator = db.get(User, operator_id)
        with patch("app.api.audit.get_session_factory", return_value=self.Session):
            record = get_audit(request_id, operator)
        self.assertEqual(record.current_status, "BLOCKED")
        self.assertIn("ANALYSIS_BLOCKED", {event.event_type for event in record.events})

    def test_unknown_request_still_404s(self):
        _request_id, operator_id = self._seed(job_status="CLASSIFICATION_REVIEW")
        with self.Session() as db:
            operator = db.get(User, operator_id)
        with patch("app.api.audit.get_session_factory", return_value=self.Session):
            with self.assertRaises(HTTPException) as ctx:
                get_audit(999999, operator)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
