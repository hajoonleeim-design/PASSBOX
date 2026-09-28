import unittest

from app.security_scan import scan_text


class SecurityScanTests(unittest.TestCase):
    def _categories(self, text: str) -> set[str]:
        return {finding.category for finding in scan_text(text)}

    def test_luhn_valid_card_number_is_detected(self):
        categories = self._categories("결제 카드번호 4111-1111-1111-1111 확인 요청")

        self.assertIn("CREDIT_CARD", categories)

    def test_luhn_invalid_digits_are_not_flagged_as_card(self):
        categories = self._categories("문의 코드 4111-1111-1111-1112 확인 요청")

        self.assertNotIn("CREDIT_CARD", categories)

    def test_korean_passport_number_is_detected(self):
        categories = self._categories("여권번호 M12345678 제출 바랍니다.")

        self.assertIn("PASSPORT_KR", categories)

    def test_business_registration_number_is_detected(self):
        categories = self._categories("사업자등록번호 123-45-67890 확인")

        self.assertIn("BUSINESS_REG_NO", categories)

    def test_google_and_slack_keys_are_detected_as_api_key(self):
        categories = self._categories(
            "google=AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q "
            "slack=xoxb-1234567890-abcdefghij"
        )

        self.assertIn("API_KEY", categories)

    def test_anthropic_style_key_is_still_detected_as_api_key(self):
        categories = self._categories(
            "key=sk-ant-api03-abcdEFGH12345678901234567890"
        )

        self.assertIn("API_KEY", categories)


if __name__ == "__main__":
    unittest.main()
