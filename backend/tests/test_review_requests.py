import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.review_requests import (
    CreateReviewRequest,
    DecideReviewRequest,
    create_review_request,
    decide_review_request,
    list_review_requests,
)
from app.db import Base
from app.models import (
    AuditLogEntry,
    ClassificationDecision,
    Document,
    Job,
    Request,
    ReviewRequest,
    Tenant,
    User,
)


class ReviewRequestTests(unittest.TestCase):
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

    def _seed_blocked_document(self):
        with self.Session() as db:
            tenant = Tenant(name="Review Tenant")
            db.add(tenant)
            db.flush()
            user = User(
                tenant_id=tenant.id,
                username="user.one",
                display_name="User One",
                password_hash="unused",
                role="USER",
            )
            operator = User(
                tenant_id=tenant.id,
                username="operator.one",
                display_name="Operator One",
                password_hash="unused",
                role="OPERATOR",
            )
            db.add_all([user, operator])
            db.flush()
            document = Document(
                tenant_id=tenant.id,
                uploaded_by=user.id,
                original_filename="blocked.hwp",
                storage_key="blocked.hwp",
                extension=".hwp",
                mime_type="application/x-hwp",
                size_bytes=10,
                sha256="a" * 64,
                status="CLASSIFICATION_CONFIRMED",
            )
            db.add(document)
            db.flush()
            decision = ClassificationDecision(
                tenant_id=tenant.id,
                document_id=document.id,
                user_id=operator.id,
                confirmed_grade="C",
            )
            db.add(decision)
            request = Request(
                tenant_id=tenant.id,
                user_id=user.id,
                document_id=document.id,
                mode="DOCUMENT",
                status="COMPLETED",
            )
            db.add(request)
            db.flush()
            job = Job(request_id=request.id, status="COMPLETED", progress=100)
            db.add(job)
            db.commit()
            return document.id, user.id, operator.id, tenant.id

    def test_create_review_request_succeeds_for_c_grade_document(self):
        document_id, user_id, _operator_id, tenant_id = self._seed_blocked_document()
        with self.Session() as db:
            user = db.get(User, user_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            response = create_review_request(
                document_id,
                CreateReviewRequest(reason="이건 공개 문서인데 잘못 막힌 것 같습니다.", flag_for_retraining=True),
                user,
            )

        self.assertEqual(response.status, "PENDING")
        self.assertEqual(response.original_grade, "C")
        self.assertTrue(response.flag_for_retraining)
        with self.Session() as db:
            entries = list(db.scalars(select(AuditLogEntry).where(AuditLogEntry.tenant_id == tenant_id)))
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].event_type, "REVIEW_REQUEST_CREATED")

    def test_create_review_request_rejects_non_c_grade(self):
        document_id, user_id, _operator_id, _tenant_id = self._seed_blocked_document()
        with self.Session() as db:
            decision = db.scalar(select(ClassificationDecision))
            decision.confirmed_grade = "O"
            db.commit()
            user = db.get(User, user_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            with self.assertRaises(HTTPException) as context:
                create_review_request(document_id, CreateReviewRequest(reason="사유"), user)
        self.assertEqual(context.exception.status_code, 409)

    def test_create_review_request_rejects_duplicate_pending(self):
        document_id, user_id, _operator_id, _tenant_id = self._seed_blocked_document()
        with self.Session() as db:
            user = db.get(User, user_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            create_review_request(document_id, CreateReviewRequest(reason="사유1"), user)
            with self.assertRaises(HTTPException) as context:
                create_review_request(document_id, CreateReviewRequest(reason="사유2"), user)
        self.assertEqual(context.exception.status_code, 409)

    def test_list_review_requests_returns_only_pending(self):
        document_id, user_id, operator_id, _tenant_id = self._seed_blocked_document()
        with self.Session() as db:
            user = db.get(User, user_id)
            operator = db.get(User, operator_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            created = create_review_request(document_id, CreateReviewRequest(reason="사유"), user)
            items = list_review_requests(operator)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].review_request_id, created.review_request_id)

    def test_approve_creates_new_decision_and_completes_job(self):
        document_id, user_id, operator_id, tenant_id = self._seed_blocked_document()
        with self.Session() as db:
            user = db.get(User, user_id)
            operator = db.get(User, operator_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            created = create_review_request(document_id, CreateReviewRequest(reason="사유"), user)
            response = decide_review_request(
                created.review_request_id,
                DecideReviewRequest(action="approve", comment="확인했습니다", new_grade="O"),
                operator,
            )

        self.assertEqual(response.status, "APPROVED")
        self.assertEqual(response.resolved_grade, "O")
        with self.Session() as db:
            decisions = list(
                db.scalars(
                    select(ClassificationDecision)
                    .where(ClassificationDecision.document_id == document_id)
                    .order_by(ClassificationDecision.created_at)
                )
            )
            self.assertEqual(len(decisions), 2)
            self.assertEqual(decisions[-1].confirmed_grade, "O")
            job = db.scalar(select(Job))
            self.assertEqual(job.status, "COMPLETED")
            entries = list(
                db.scalars(
                    select(AuditLogEntry)
                    .where(AuditLogEntry.tenant_id == tenant_id, AuditLogEntry.event_type == "REVIEW_REQUEST_DECIDED")
                )
            )
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].payload["decision"], "APPROVED")

    def test_reject_leaves_original_decision_untouched(self):
        document_id, user_id, operator_id, _tenant_id = self._seed_blocked_document()
        with self.Session() as db:
            user = db.get(User, user_id)
            operator = db.get(User, operator_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            created = create_review_request(document_id, CreateReviewRequest(reason="사유"), user)
            response = decide_review_request(
                created.review_request_id,
                DecideReviewRequest(action="reject", comment="원 판정이 맞습니다"),
                operator,
            )

        self.assertEqual(response.status, "REJECTED")
        self.assertIsNone(response.resolved_grade)
        with self.Session() as db:
            decisions = list(
                db.scalars(select(ClassificationDecision).where(ClassificationDecision.document_id == document_id))
            )
            self.assertEqual(len(decisions), 1)
            self.assertEqual(decisions[0].confirmed_grade, "C")

    def test_decide_twice_raises_conflict(self):
        document_id, user_id, operator_id, _tenant_id = self._seed_blocked_document()
        with self.Session() as db:
            user = db.get(User, user_id)
            operator = db.get(User, operator_id)
        with patch("app.api.review_requests.get_session_factory", return_value=self.Session):
            created = create_review_request(document_id, CreateReviewRequest(reason="사유"), user)
            decide_review_request(
                created.review_request_id,
                DecideReviewRequest(action="reject", comment="반려"),
                operator,
            )
            with self.assertRaises(HTTPException) as context:
                decide_review_request(
                    created.review_request_id,
                    DecideReviewRequest(action="approve", new_grade="O"),
                    operator,
                )
        self.assertEqual(context.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
