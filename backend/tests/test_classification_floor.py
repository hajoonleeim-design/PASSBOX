import unittest
from types import SimpleNamespace

from app.classifier import ClassificationRecommendation, apply_findings_floor


def _finding(category, severity):
    return SimpleNamespace(category=category, severity=severity, match_count=1, line_hint=None)


def _result(grade, reason="모델 판단 사유"):
    return ClassificationRecommendation(
        recommended_grade=grade,
        confidence=0.99,
        reason=reason,
        model_version="test-model",
        status="PROVISIONAL",
    )


class FindingsFloorTests(unittest.TestCase):
    def test_o_recommendation_is_raised_to_s_when_phone_detected(self):
        result = apply_findings_floor(_result("O"), [_finding("PHONE", "MEDIUM")])

        self.assertEqual(result.recommended_grade, "S")
        self.assertIn("PHONE", result.reason)
        self.assertIn("자동 보정", result.reason)

    def test_none_recommendation_is_raised_to_s_when_high_severity_detected(self):
        result = apply_findings_floor(_result(None), [_finding("PERSONAL_ID", "HIGH")])

        self.assertEqual(result.recommended_grade, "S")

    def test_c_recommendation_is_left_untouched(self):
        original = _result("C", "모델이 기밀로 판단했습니다.")
        result = apply_findings_floor(original, [_finding("PHONE", "MEDIUM")])

        self.assertEqual(result.recommended_grade, "C")
        self.assertEqual(result.reason, "모델이 기밀로 판단했습니다.")

    def test_s_recommendation_is_left_untouched(self):
        original = _result("S", "모델이 민감으로 판단했습니다.")
        result = apply_findings_floor(original, [_finding("EMAIL", "MEDIUM")])

        self.assertEqual(result.recommended_grade, "S")
        self.assertEqual(result.reason, "모델이 민감으로 판단했습니다.")

    def test_o_recommendation_is_untouched_when_no_findings(self):
        original = _result("O", "모델이 공개로 판단했습니다.")
        result = apply_findings_floor(original, [])

        self.assertEqual(result.recommended_grade, "O")
        self.assertEqual(result.reason, "모델이 공개로 판단했습니다.")

    def test_low_severity_findings_do_not_trigger_the_floor(self):
        original = _result("O", "모델이 공개로 판단했습니다.")
        result = apply_findings_floor(original, [_finding("SOMETHING", "LOW")])

        self.assertEqual(result.recommended_grade, "O")
        self.assertEqual(result.reason, "모델이 공개로 판단했습니다.")

    def test_multiple_categories_are_listed_sorted(self):
        original = _result("O", "모델이 공개로 판단했습니다.")
        result = apply_findings_floor(
            original, [_finding("PHONE", "MEDIUM"), _finding("EMAIL", "MEDIUM")]
        )

        self.assertIn("EMAIL, PHONE", result.reason)


if __name__ == "__main__":
    unittest.main()
