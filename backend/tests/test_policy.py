import unittest
from types import SimpleNamespace

from app.api.gateway import _apply_prompt_policy
from app.policy import PolicyConfiguration, check_outbound_policy


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

    def test_database_policy_can_disable_a_model(self):
        policy = PolicyConfiguration(
            version="POLICY-v2",
            cso_rules=({"grade": "O", "enabled": True},),
            approval_policy={"o_grade_requires_approval": False},
            model_allowlist=({"provider": "openai", "model_id": "approved-model", "enabled": True},),
        )
        decision = check_outbound_policy(
            confirmed_grade="O",
            provider="openai",
            model="gpt-4o-mini",
            policy=policy,
        )

        self.assertEqual(decision.decision, "BLOCKED")
        self.assertFalse(decision.can_transmit)

    def test_database_policy_can_require_o_grade_approval(self):
        policy = PolicyConfiguration(
            version="POLICY-v2",
            cso_rules=({"grade": "O", "enabled": True},),
            approval_policy={"o_grade_requires_approval": True},
            model_allowlist=({"provider": "openai", "model_id": "gpt-4o-mini", "enabled": True},),
        )
        decision = check_outbound_policy(
            confirmed_grade="O",
            provider="openai",
            model="gpt-4o-mini",
            policy=policy,
        )

        self.assertEqual(decision.decision, "APPROVAL_REQUIRED")
        self.assertFalse(decision.can_transmit)

    def test_o_grade_is_blocked_when_payload_contains_sensitive_finding(self):
        base_decision = check_outbound_policy(
            confirmed_grade="O",
            provider="openai",
            model="gpt-4o-mini",
        )
        decision = _apply_prompt_policy(
            confirmed_grade="O",
            prompt_findings=[SimpleNamespace(category="EMAIL")],
            policy_decision=base_decision,
        )

        self.assertEqual(decision.decision, "PROMPT_BLOCKED")
        self.assertFalse(decision.can_transmit)

    def test_s_grade_can_continue_to_approval_for_maskable_finding(self):
        base_decision = check_outbound_policy(
            confirmed_grade="S",
            provider="openai",
            model="gpt-4o-mini",
        )
        decision = _apply_prompt_policy(
            confirmed_grade="S",
            prompt_findings=[SimpleNamespace(category="EMAIL")],
            policy_decision=base_decision,
        )

        self.assertEqual(decision.decision, "APPROVAL_REQUIRED")
        self.assertTrue(decision.masking_required)

    def test_s_grade_is_blocked_for_hard_secret_finding(self):
        base_decision = check_outbound_policy(
            confirmed_grade="S",
            provider="openai",
            model="gpt-4o-mini",
        )
        decision = _apply_prompt_policy(
            confirmed_grade="S",
            prompt_findings=[SimpleNamespace(category="API_KEY")],
            policy_decision=base_decision,
        )

        self.assertEqual(decision.decision, "PROMPT_BLOCKED")
        self.assertFalse(decision.can_transmit)


if __name__ == "__main__":
    unittest.main()
