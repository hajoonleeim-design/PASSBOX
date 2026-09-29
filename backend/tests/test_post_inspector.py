import unittest

from app.post_inspector import inspect_response


class PostInspectorTests(unittest.TestCase):
    def test_clean_response_passes(self):
        result = inspect_response("문의하신 정책 요약은 다음과 같습니다.")

        self.assertEqual(result.status, "PASSED")
        self.assertEqual(result.categories, [])

    def test_response_with_pii_is_blocked(self):
        result = inspect_response("담당자 연락처는 010-1234-5678 입니다.")

        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("PHONE", result.categories)

    def test_response_with_suspicious_link_is_blocked(self):
        result = inspect_response("자세한 내용은 https://bit.ly/3xAmPle 에서 확인하세요.")

        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("SUSPICIOUS_URL", result.categories)

    def test_response_with_ordinary_link_passes(self):
        result = inspect_response("공식 문서는 https://github.com/passbox/docs 를 참고하세요.")

        self.assertEqual(result.status, "PASSED")
        self.assertEqual(result.categories, [])


if __name__ == "__main__":
    unittest.main()
