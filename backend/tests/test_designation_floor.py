import unittest

from app.classifier import ClassificationRecommendation, apply_designation_floor, has_designation_marking


def _result(grade):
    return ClassificationRecommendation(
        recommended_grade=grade, confidence=0.9, reason="모델 판단 사유",
        model_version="test-model", status="PROVISIONAL",
    )


class DesignationMarkingTests(unittest.TestCase):
    def test_bracketed_label_in_header_counts(self):
        for text in (
            "[대외비] 2027년도 청사 보안시설 개선 계획\n본문",
            "[비밀] 해상 감시 장비 운용 지침",
            "[극비] 비상 대응 계획",
            "국가 정보 수집 활동 결과 보고 (2급 비밀)\n배포선: 3명",
            "(TOP SECRET) operations plan",
            "【대외비】 외교 협의 기초 자료",
        ):
            self.assertTrue(has_designation_marking(text), text)

    def test_standalone_label_line_in_header_counts(self):
        self.assertTrue(has_designation_marking("대외비\n2027년 예산 검토"))

    def test_page_header_label_line_deep_in_document_counts(self):
        body = "일반 문장입니다.\n" * 60 + "[대외비]\n이어지는 쪽 내용"
        self.assertTrue(has_designation_marking(body))

    def test_prose_mentions_do_not_count(self):
        for text in (
            '이 모델은 "대외비"·"극비" 같은 단어만 보고 판단하는 것이 아닌지 점검한다.',
            "대외비 문서는 외부 AI에 입력하지 않도록 교육합니다.",
            "비밀번호는 8자 이상으로 설정하세요. (비밀번호 변경 안내)",
            "정책 소개\n" + "설명 문장입니다.\n" * 40 + "문서에 [대외비] 표기가 있으면 별도 승인이 필요합니다.",
            "영업 비밀 보호 교육 자료",
            "공개 안내문입니다. 비밀은 없습니다.",
        ):
            self.assertFalse(has_designation_marking(text), text)


class DesignationFloorTests(unittest.TestCase):
    def test_raises_s_and_o_to_c(self):
        for grade in ("S", "O", None):
            result = apply_designation_floor(_result(grade), "[대외비] 계획")
            self.assertEqual(result.recommended_grade, "C")
            self.assertIn("비밀 표기", result.reason)
            self.assertIn("모델 판단 사유", result.reason)

    def test_never_lowers_and_leaves_c_untouched(self):
        original = _result("C")
        self.assertIs(apply_designation_floor(original, "[대외비] 계획"), original)

    def test_no_marking_leaves_result_untouched(self):
        for grade in ("S", "O", "C"):
            original = _result(grade)
            self.assertIs(apply_designation_floor(original, "공개 안내문입니다."), original)


if __name__ == "__main__":
    unittest.main()
