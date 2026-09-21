import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.auth import require_roles


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


if __name__ == "__main__":
    unittest.main()
