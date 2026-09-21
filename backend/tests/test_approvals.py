import unittest

from app.api.approvals import _allowed_approval_roles


class ApprovalPolicyRoleTests(unittest.TestCase):
    def test_policy_roles_are_used_with_security_admin_override(self):
        roles = _allowed_approval_roles({"approver_roles": ["ADMIN"]})

        self.assertEqual(roles, {"ADMIN", "SECURITY_ADMIN"})

    def test_invalid_or_empty_policy_roles_use_safe_defaults(self):
        roles = _allowed_approval_roles({"approver_roles": ["USER", ""]})

        self.assertEqual(roles, {"APPROVER", "ADMIN", "SECURITY_ADMIN"})


if __name__ == "__main__":
    unittest.main()
