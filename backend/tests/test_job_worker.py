import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.jobs import _to_response
from app.job_worker import _set_job_state


class FakeSession:
    def __init__(self):
        self.commit_count = 0
        self.refresh_count = 0

    def commit(self):
        self.commit_count += 1

    def refresh(self, _value):
        self.refresh_count += 1


class JobWorkerTests(unittest.TestCase):
    def test_set_job_state_updates_job_and_request(self):
        db = FakeSession()
        job = SimpleNamespace(status="QUEUED", progress=0, error_message=None)
        request = SimpleNamespace(status="RECEIVED")

        changed = _set_job_state(
            db,
            job,
            request,
            status="PARSING",
            progress=30,
        )

        self.assertTrue(changed)
        self.assertEqual(job.status, "PARSING")
        self.assertEqual(job.progress, 30)
        self.assertIsNone(job.error_message)
        self.assertEqual(request.status, "PARSING")
        self.assertEqual(db.commit_count, 1)
        self.assertEqual(db.refresh_count, 1)

    def test_set_job_state_does_not_resurrect_cancelled_job(self):
        db = FakeSession()
        job = SimpleNamespace(status="CANCELLED", progress=100, error_message=None)
        request = SimpleNamespace(status="CANCELLED")

        changed = _set_job_state(
            db,
            job,
            request,
            status="PARSING",
            progress=30,
        )

        self.assertFalse(changed)
        self.assertEqual(job.status, "CANCELLED")
        self.assertEqual(request.status, "CANCELLED")
        self.assertEqual(db.commit_count, 0)

    def test_job_response_exposes_classification_review_step(self):
        timestamp = datetime.now(timezone.utc)
        response = _to_response(
            SimpleNamespace(
                id=12,
                status="CLASSIFICATION_REVIEW",
                progress=85,
                error_message=None,
                created_at=timestamp,
                updated_at=timestamp,
            ),
            SimpleNamespace(id=24),
            SimpleNamespace(
                id=7,
                original_filename="test.pdf",
                extension=".pdf",
                size_bytes=123,
            ),
        )

        self.assertEqual(response.status, "CLASSIFICATION_REVIEW")
        self.assertEqual(response.current_step, "분류 검토")
        self.assertTrue(response.can_cancel)


if __name__ == "__main__":
    unittest.main()
