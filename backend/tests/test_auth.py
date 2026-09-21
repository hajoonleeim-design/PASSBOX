import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.auth import PasswordChangeRequest, require_roles


class RoleGuardTests(unittest.TestCase):
    def test_allowed_role_passes_guard(self):
        guard = require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")

        user = guard(SimpleNamespace(role="OPERATOR"))

        self.assertEqual(user.role, "OPERATOR")

    def test_user_role_is_rejected_by_classification_guard(self):
        guard = require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")

        with self.assertRaises(HTTPException) as context:
            guard(SimpleNamespace(role="USER"))

        self.assertEqual(context.exception.status_code, 403)


class PasswordChangeRequestTests(unittest.TestCase):
    def test_new_password_requires_at_least_twelve_characters(self):
        with self.assertRaises(ValueError):
            PasswordChangeRequest(current_password="old-password", new_password="short")

    def test_valid_password_change_request_is_accepted(self):
        payload = PasswordChangeRequest(
            current_password="old-password",
            new_password="new-password-123",
        )

        self.assertEqual(payload.new_password, "new-password-123")


if __name__ == "__main__":
    unittest.main()
