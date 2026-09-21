from datetime import datetime, timezone
import unittest
from unittest.mock import patch

import jwt

from app.security import create_access_token, decode_access_token


class JwtSecurityTests(unittest.TestCase):
    def test_access_token_uses_configured_expiration(self):
        settings = type(
            "Settings",
            (),
            {"jwt_secret_key": "test-secret-012345678901234567890123", "jwt_access_token_minutes": 15},
        )()

        with patch("app.security.Settings", return_value=settings):
            token = create_access_token(7, 3, "OPERATOR")
            payload = decode_access_token(token)

        self.assertEqual(payload["sub"], "7")
        self.assertEqual(payload["tenant_id"], 3)
        self.assertEqual(payload["role"], "OPERATOR")
        self.assertGreater(payload["exp"], datetime.now(timezone.utc).timestamp() + 14 * 60)

    def test_non_positive_expiration_is_rejected(self):
        settings = type(
            "Settings",
            (),
            {"jwt_secret_key": "test-secret-012345678901234567890123", "jwt_access_token_minutes": 0},
        )()

        with patch("app.security.Settings", return_value=settings):
            with self.assertRaises(RuntimeError):
                create_access_token(7, 3, "OPERATOR")

    def test_expired_token_is_rejected(self):
        token = jwt.encode(
            {
                "sub": "7",
                "tenant_id": 3,
                "role": "OPERATOR",
                "exp": datetime.now(timezone.utc).timestamp() - 1,
            },
            "test-secret-012345678901234567890123",
            algorithm="HS256",
        )
        settings = type(
            "Settings",
            (),
            {"jwt_secret_key": "test-secret-012345678901234567890123", "jwt_access_token_minutes": 60},
        )()

        with patch("app.security.Settings", return_value=settings):
            with self.assertRaises(ValueError):
                decode_access_token(token)


if __name__ == "__main__":
    unittest.main()
