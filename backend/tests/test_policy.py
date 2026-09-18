import unittest

from app.policy import check_outbound_policy


class PolicyTests(unittest.TestCase):
    def test_c_grade_is_blocked(self):
        decision = check_outbound_policy(
            confirmed_grade="C",
            provider="openai",
            model="gpt-4o-mini",
        )

        self.assertEqual(decision.decision, "BLOCKED")
        self.assertFalse(decision.can_transmit)

    def test_s_grade_requires_approval(self):
        decision = check_outbound_policy(
            confirmed_grade="S",
            provider="openai",
            model="gpt-4o-mini",
        )

        self.assertEqual(decision.decision, "APPROVAL_REQUIRED")
        self.assertTrue(decision.masking_required)
        self.assertFalse(decision.can_transmit)

    def test_o_grade_is_allowed_for_supported_provider(self):
        decision = check_outbound_policy(
            confirmed_grade="O",
            provider="openai",
            model="gpt-4o-mini",
        )

        self.assertEqual(decision.decision, "ALLOWED")
        self.assertTrue(decision.can_transmit)

    def test_unknown_provider_is_blocked(self):
        decision = check_outbound_policy(
            confirmed_grade="O",
            provider="unknown-provider",
            model="test-model",
        )

        self.assertEqual(decision.decision, "BLOCKED")
        self.assertFalse(decision.can_transmit)


if __name__ == "__main__":
    unittest.main()
