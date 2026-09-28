import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.classifier import (
    ClassifierUnavailableError,
    RemoteClassifierAdapter,
    build_classifier,
)
from app.classifier import LocalClassifierAdapter
from app.db import Settings


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


class ClassifierAdapterTests(unittest.TestCase):
    def _adapter(self):
        return RemoteClassifierAdapter(
            Settings(
                classifier_mode="REMOTE",
                classifier_service_url="http://gpu-classifier.test/v1/classify",
                classifier_service_token="test-token",
                classifier_timeout_seconds=2,
                classifier_model="test-model-v1",
                classifier_policy_version="POLICY-TEST-v1",
            )
        )

    def test_remote_response_is_mapped_to_passbox_result(self):
        response = {
            "recommended_grade": "S",
            "confidence": 0.91,
            "reason": "개인정보가 포함되어 마스킹이 필요합니다.",
            "model_version": "gpu-model-v1",
            "status": "PROVISIONAL",
        }
        finding = SimpleNamespace(
            category="PERSONAL_ID",
            severity="HIGH",
            match_count=1,
            line_hint=3,
        )

        with patch("app.classifier.urllib_request.urlopen", return_value=FakeResponse(response)) as mocked:
            result = self._adapter().recommend("테스트 문서", [finding])

        self.assertEqual(result.recommended_grade, "S")
        self.assertEqual(result.confidence, 0.91)
        self.assertEqual(result.model_version, "gpu-model-v1")
        self.assertEqual(result.status, "PROVISIONAL")
        request = mocked.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer test-token")
        self.assertEqual(json.loads(request.data.decode("utf-8"))["policy_version"], "POLICY-TEST-v1")

    def test_transport_failure_raises_unavailable(self):
        with patch(
            "app.classifier.urllib_request.urlopen",
            side_effect=TimeoutError,
        ):
            with self.assertRaises(ClassifierUnavailableError):
                self._adapter().recommend("테스트 문서", [])

    def test_invalid_grade_raises_unavailable(self):
        with patch(
            "app.classifier.urllib_request.urlopen",
            return_value=FakeResponse({"recommended_grade": "X"}),
        ):
            with self.assertRaises(ClassifierUnavailableError):
                self._adapter().recommend("테스트 문서", [])

    def test_missing_service_url_raises_unavailable(self):
        adapter = RemoteClassifierAdapter(
            Settings(classifier_mode="REMOTE", classifier_service_url="")
        )

        with self.assertRaises(ClassifierUnavailableError):
            adapter.recommend("테스트 문서", [])


class BuildClassifierTests(unittest.TestCase):
    def test_remote_mode_selects_remote_adapter(self):
        settings = Settings(
            classifier_mode="REMOTE",
            classifier_service_url="http://gpu-classifier.test/v1/classify",
        )

        self.assertIsInstance(build_classifier(settings), RemoteClassifierAdapter)

    def test_local_rules_mode_selects_local_adapter(self):
        settings = Settings(classifier_mode="LOCAL_RULES")

        self.assertIsInstance(build_classifier(settings), LocalClassifierAdapter)


if __name__ == "__main__":
    unittest.main()
