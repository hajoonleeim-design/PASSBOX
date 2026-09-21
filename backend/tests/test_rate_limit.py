import unittest

from app.rate_limit import LoginRateLimiter


class LoginRateLimiterTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.limiter = LoginRateLimiter(lambda: self.now)

    def test_allows_configured_attempts_then_returns_retry_after(self):
        for _ in range(3):
            self.assertIsNone(
                self.limiter.retry_after_seconds(
                    "client",
                    max_attempts=3,
                    window_seconds=60,
                )
            )
            self.limiter.record_failure(
                "client",
                max_attempts=3,
                window_seconds=60,
            )

        self.assertEqual(
            self.limiter.retry_after_seconds(
                "client",
                max_attempts=3,
                window_seconds=60,
            ),
            60,
        )

    def test_expired_failures_are_removed(self):
        self.limiter.record_failure(
            "client",
            max_attempts=1,
            window_seconds=60,
        )
        self.assertIsNotNone(
            self.limiter.retry_after_seconds(
                "client",
                max_attempts=1,
                window_seconds=60,
            )
        )

        self.now = 160.1
        self.assertIsNone(
            self.limiter.retry_after_seconds(
                "client",
                max_attempts=1,
                window_seconds=60,
            )
        )

    def test_success_reset_clears_failures(self):
        self.limiter.record_failure(
            "client",
            max_attempts=1,
            window_seconds=60,
        )
        self.limiter.reset("client")

        self.assertIsNone(
            self.limiter.retry_after_seconds(
                "client",
                max_attempts=1,
                window_seconds=60,
            )
        )


if __name__ == "__main__":
    unittest.main()
