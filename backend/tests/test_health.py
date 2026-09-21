import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.main import health_check, readiness_check


class HealthCheckTests(unittest.TestCase):
    def test_liveness_does_not_require_database(self):
        self.assertEqual(health_check()["status"], "ok")

    @patch("app.main.check_database")
    def test_readiness_reports_connected_database(self, check_database):
        self.assertEqual(
            readiness_check(),
            {
                "status": "ready",
                "service": "PASSBOX Backend API",
                "database": "connected",
            },
        )
        check_database.assert_called_once_with()

    @patch("app.main.check_database", side_effect=RuntimeError("database down"))
    def test_readiness_returns_service_unavailable_when_database_fails(
        self, _check_database
    ):
        with self.assertRaises(HTTPException) as context:
            readiness_check()

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.detail, "service is not ready")


if __name__ == "__main__":
    unittest.main()
