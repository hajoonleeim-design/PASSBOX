import unittest
from types import SimpleNamespace

from app.api.decisions import _grade_copy, _status_for


class DecisionMappingTests(unittest.TestCase):
    def test_grade_copy_has_safe_descriptions(self):
        self.assertEqual(_grade_copy("C")[0], "기밀")
        self.assertIn("차단", _grade_copy("C")[1])
        self.assertEqual(_grade_copy("S")[0], "민감")
        self.assertEqual(_grade_copy("O")[0], "공개")

    def test_c_grade_is_blocked_without_transmission(self):
        self.assertEqual(_status_for("C", None, None), "BLOCKED")

    def test_pending_approval_is_waiting(self):
        transmission = SimpleNamespace(status="WAITING_APPROVAL", policy_decision="APPROVAL_REQUIRED")
        approval = SimpleNamespace(status="PENDING")
        self.assertEqual(_status_for("S", transmission, approval), "WAITING_APPROVAL")

    def test_completed_approved_transmission_is_approved(self):
        transmission = SimpleNamespace(status="COMPLETED", policy_decision="APPROVED")
        approval = SimpleNamespace(status="APPROVED")
        self.assertEqual(_status_for("S", transmission, approval), "APPROVED")


if __name__ == "__main__":
    unittest.main()
