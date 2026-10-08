import unittest

from app.masking import MASKING_VERSION, mask_text


class MaskingTests(unittest.TestCase):
    def test_masks_supported_personal_information(self):
        result = mask_text(
            "email test@example.com, phone 010-1234-5678, id 900101-1234567"
        )

        self.assertEqual(MASKING_VERSION, "rules-mask-v3")
        self.assertEqual(
            set(result.categories),
            {"EMAIL", "PHONE", "PERSONAL_ID"},
        )
        self.assertEqual(result.replacement_count, 3)
        self.assertNotIn("test@example.com", result.masked_text)
        self.assertNotIn("010-1234-5678", result.masked_text)
        self.assertNotIn("900101-1234567", result.masked_text)

    def test_keeps_safe_text_unchanged(self):
        result = mask_text("문서 요약을 작성해 주세요.")

        self.assertEqual(result.masked_text, "문서 요약을 작성해 주세요.")
        self.assertEqual(result.categories, ())
        self.assertEqual(result.replacement_count, 0)

    def test_masks_card_passport_and_business_registration_numbers(self):
        result = mask_text(
            "카드번호 4111-1111-1111-1111, 여권번호 M12345678, "
            "사업자등록번호 123-45-67890"
        )

        self.assertEqual(
            set(result.categories),
            {"CREDIT_CARD", "PASSPORT_KR", "BUSINESS_REG_NO"},
        )
        self.assertNotIn("4111-1111-1111-1111", result.masked_text)
        self.assertNotIn("M12345678", result.masked_text)
        self.assertNotIn("123-45-67890", result.masked_text)


if __name__ == "__main__":
    unittest.main()
