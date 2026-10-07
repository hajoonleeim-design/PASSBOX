import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.access import document_access_clause
from app.api.chat import _get_chat
from app.api.jobs import get_job, list_jobs
from app.db import Base
from app.models import ChatRequest, Document, DocumentText, Job, Request, Tenant, User


class OwnershipAccessTests(unittest.TestCase):
    """A plain USER must not see another user's documents, jobs, or AI chats in the
    same tenant -- not by listing, not by full-text search, not by guessing IDs.
    Reviewer/admin roles keep tenant-wide access."""

    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            tenant = Tenant(name="T")
            db.add(tenant); db.flush()
            self.alice = User(tenant_id=tenant.id, username="alice", display_name="A", password_hash="x", role="USER")
            self.bob = User(tenant_id=tenant.id, username="bob", display_name="B", password_hash="x", role="USER")
            self.admin = User(tenant_id=tenant.id, username="adm", display_name="Adm", password_hash="x", role="ADMIN")
            db.add_all([self.alice, self.bob, self.admin]); db.flush()
            self.bob_job_id, self.bob_doc_id = self._seed_job(db, tenant.id, self.bob, "bob_salary.pdf", "연봉 협상 내역")
            self.alice_job_id, _ = self._seed_job(db, tenant.id, self.alice, "alice_memo.pdf", "회의 메모")
            chat = ChatRequest(tenant_id=tenant.id, user_id=self.bob.id, model="test-model", policy_version="v1", prompt_hash="h" * 64)
            db.add(chat); db.flush()
            self.bob_chat_id = chat.id
            db.commit()

    def tearDown(self):
        self.engine.dispose()

    @staticmethod
    def _seed_job(db, tenant_id, owner, filename, body):
        document = Document(tenant_id=tenant_id, uploaded_by=owner.id, original_filename=filename, storage_key=filename, extension=".pdf", mime_type="application/pdf", size_bytes=1, sha256="a" * 64, status="READY_FOR_PARSING")
        db.add(document); db.flush()
        db.add(DocumentText(tenant_id=tenant_id, document_id=document.id, extracted_text=body, extractor="test", status="EXTRACTED"))
        request = Request(tenant_id=tenant_id, user_id=owner.id, document_id=document.id, mode="DOCUMENT", status="RECEIVED")
        db.add(request); db.flush()
        job = Job(request_id=request.id, status="COMPLETED", progress=100)
        db.add(job); db.flush()
        return job.id, document.id

    def _list(self, user, q=None):
        with patch("app.api.jobs.get_session_factory", return_value=self.Session):
            return {row.file_name for row in list_jobs(limit=30, q=q, current_user=user)}

    def test_user_lists_only_own_jobs(self):
        self.assertEqual(self._list(self.alice), {"alice_memo.pdf"})

    def test_user_cannot_full_text_search_other_users_documents(self):
        self.assertEqual(self._list(self.alice, q="연봉"), set())

    def test_admin_keeps_tenant_wide_listing(self):
        self.assertEqual(self._list(self.admin), {"alice_memo.pdf", "bob_salary.pdf"})

    def test_user_cannot_open_other_users_job_by_id(self):
        with patch("app.api.jobs.get_session_factory", return_value=self.Session):
            with self.assertRaises(HTTPException) as ctx:
                get_job(self.bob_job_id, self.alice)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_user_can_open_own_job(self):
        with patch("app.api.jobs.get_session_factory", return_value=self.Session):
            self.assertEqual(get_job(self.alice_job_id, self.alice).file_name, "alice_memo.pdf")

    def test_document_lookup_is_owner_scoped_for_user(self):
        with self.Session() as db:
            as_alice = db.scalar(select(Document).where(Document.id == self.bob_doc_id, document_access_clause(self.alice)))
            as_admin = db.scalar(select(Document).where(Document.id == self.bob_doc_id, document_access_clause(self.admin)))
        self.assertIsNone(as_alice)
        self.assertIsNotNone(as_admin)

    def test_user_cannot_read_other_users_chat(self):
        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                _get_chat(db, str(self.bob_chat_id), self.alice)
            self.assertEqual(ctx.exception.status_code, 404)
            self.assertEqual(_get_chat(db, str(self.bob_chat_id), self.bob).id, self.bob_chat_id)


class SupportInquiryOwnershipTests(OwnershipAccessTests):
    def test_user_cannot_read_other_users_inquiry(self):
        from app.api.support import get_inquiry
        from app.models import SupportInquiry

        with self.Session() as db:
            inquiry = SupportInquiry(tenant_id=self.bob.tenant_id, user_id=self.bob.id, category="INQUIRY", subject="s", content_hash="h" * 64, masked_content="m")
            db.add(inquiry); db.commit()
            inquiry_id = f"INQ-20260101-{inquiry.id:04d}"
        with patch("app.api.support.get_session_factory", return_value=self.Session):
            with self.assertRaises(HTTPException) as ctx:
                get_inquiry(inquiry_id, self.alice)
            self.assertEqual(ctx.exception.status_code, 404)
            self.assertIsNotNone(get_inquiry(inquiry_id, self.bob))
            self.assertIsNotNone(get_inquiry(inquiry_id, self.admin))


if __name__ == "__main__":
    unittest.main()
