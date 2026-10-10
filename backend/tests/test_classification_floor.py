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


class ConfidentialCeilingTests(unittest.TestCase):
    def test_model_only_c_is_lowered_to_s(self):
        from app.classifier import apply_confidential_ceiling

        result = apply_confidential_ceiling(_result("C"), [], "DNS 스푸핑 실습 보고서입니다.")
        self.assertEqual(result.recommended_grade, "S")
        self.assertIn("낮췄습니다", result.reason)

    def test_personal_data_alone_is_s_not_c_per_n2sf_item_6(self):
        from app.classifier import apply_confidential_ceiling

        for category in ("PERSONAL_ID", "PASSPORT_KR", "CREDIT_CARD", "SECRET", "API_KEY"):
            result = apply_confidential_ceiling(_result("C"), [_finding(category, "HIGH")], "x")
            self.assertEqual(result.recommended_grade, "S", category)
            self.assertIn("표 2-8", result.reason)

    def test_c_stays_with_keyword_or_marker(self):
        from app.classifier import apply_confidential_ceiling

        self.assertEqual(apply_confidential_ceiling(_result("C"), [_finding("CONFIDENTIAL_KEYWORD", "MEDIUM")], "x").recommended_grade, "C")
        for text in ("(대외비) 내부 계획", "2급 비밀 군사 문서", "TOP SECRET", "TOP  SECRET".replace("  ", "")):
            self.assertEqual(apply_confidential_ceiling(_result("C"), [], text).recommended_grade, "C", text)

    def test_medium_finding_alone_does_not_keep_c(self):
        from app.classifier import apply_confidential_ceiling

        self.assertEqual(apply_confidential_ceiling(_result("C"), [_finding("PHONE", "MEDIUM")], "x").recommended_grade, "S")

    def test_s_and_o_are_never_changed(self):
        from app.classifier import apply_confidential_ceiling

        for grade in ("S", "O", None):
            self.assertEqual(apply_confidential_ceiling(_result(grade), [], "x").recommended_grade, grade)


class SourceDocumentAccessTests(unittest.TestCase):
    """A confirming OPERATOR/SECURITY_ADMIN/ADMIN must be able to open the original
    document before confirming its grade -- before this, the recommendation reason
    was the only thing shown and the file itself was not reachable at this stage."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.db import Base

        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.storage_root = Path(self.tmpdir.name)
        (self.storage_root / "doc.txt").write_text("원본 내용", encoding="utf-8")

    def tearDown(self):
        self.engine.dispose()
        self.tmpdir.cleanup()

    def _seed(self, *, role: str):
        from app.models import Document, Tenant, User

        with self.Session() as db:
            tenant = Tenant(name="T")
            db.add(tenant); db.flush()
            user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash="x", role=role)
            db.add(user); db.flush()
            document = Document(tenant_id=tenant.id, uploaded_by=999, original_filename="doc.txt", storage_key="doc.txt", extension=".txt", mime_type="text/plain", size_bytes=10, sha256="a" * 64, status="READY_FOR_CLASSIFICATION")
            db.add(document); db.commit()
            return document.id, user.id

    def test_operator_can_download_before_confirming(self):
        from unittest.mock import patch
        from app.api.classifications import download_source_document
        from app.db import Settings
        from app.models import User

        document_id, user_id = self._seed(role="OPERATOR")
        with self.Session() as db:
            user = db.get(User, user_id)
        with patch("app.api.classifications.get_session_factory", return_value=self.Session), \
             patch("app.api.classifications.Settings", return_value=Settings(storage_root=str(self.storage_root))):
            response = download_source_document(document_id, user)
        self.assertEqual(response.path.name, "doc.txt")

    def test_plain_user_is_forbidden(self):
        from app.api.auth import require_roles
        from fastapi import HTTPException

        _document_id, user_id = self._seed(role="USER")
        with self.Session() as db:
            from app.models import User
            user = db.get(User, user_id)
        with self.assertRaises(HTTPException) as ctx:
            require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")(current_user=user)
        self.assertEqual(ctx.exception.status_code, 403)
