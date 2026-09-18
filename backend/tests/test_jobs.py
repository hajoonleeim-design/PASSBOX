import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.jobs import _reset_failed_job


class JobRetryTests(unittest.TestCase):
    def test_failed_job_is_reset_to_received_queue(self):
        job = SimpleNamespace(
            status="FAILED",
            progress=100,
            error_message="Gateway 호출에 실패했습니다.",
            updated_at=None,
        )
        request = SimpleNamespace(status="FAILED")

        _reset_failed_job(job, request)

        self.assertEqual(job.status, "QUEUED")
        self.assertEqual(job.progress, 0)
        self.assertIsNone(job.error_message)
        self.assertEqual(request.status, "RECEIVED")
        self.assertIsNotNone(job.updated_at)

    def test_non_failed_job_cannot_be_retried(self):
        job = SimpleNamespace(status="COMPLETED")
        request = SimpleNamespace(status="COMPLETED")

        with self.assertRaises(HTTPException) as context:
            _reset_failed_job(job, request)

        self.assertEqual(context.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
