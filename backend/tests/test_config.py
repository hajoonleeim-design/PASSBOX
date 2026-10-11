import unittest

from app.db import Settings
from app.main import _parse_cors_origins, _validate_runtime_settings


class CorsConfigurationTests(unittest.TestCase):
    def test_origins_are_trimmed_deduplicated_and_empty_values_removed(self):
        origins = _parse_cors_origins(
            " http://localhost:5173, http://localhost:5173,, https://passbox.example"
        )

        self.assertEqual(
            origins,
            ["http://localhost:5173", "https://passbox.example"],
        )

    def test_wildcard_origin_is_rejected_with_credentials_enabled(self):
        with self.assertRaises(RuntimeError):
            _parse_cors_origins("https://passbox.example, *")

    def test_remote_classifier_requires_service_url(self):
        settings = Settings(classifier_mode="REMOTE", classifier_service_url="")

        with self.assertRaises(RuntimeError):
            _validate_runtime_settings(settings)

    def test_local_classifier_is_valid_without_remote_service(self):
        settings = Settings(classifier_mode="LOCAL_RULES")

        _validate_runtime_settings(settings)

    def test_job_worker_threads_must_be_positive(self):
        settings = Settings(job_worker_threads=0)

        with self.assertRaises(RuntimeError):
            _validate_runtime_settings(settings)

    def _production_settings(self, **overrides):
        base = dict(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@localhost/db",
            jwt_secret_key="a" * 32,
            data_encryption_key="k" * 48,
            clamav_mode="required",
            gateway_mode="MOCK",
            cors_allowed_origins="https://passbox.example",
        )
        base.update(overrides)
        return Settings(**base)

    def test_production_remote_classifier_requires_https_url(self):
        settings = self._production_settings(
            classifier_mode="REMOTE",
            classifier_service_url="http://gpu-classifier.internal/v1/classify",
            classifier_service_token="token",
            gateway_mode="LIVE",
            openai_api_key="key",
        )

        with self.assertRaises(RuntimeError):
            _validate_runtime_settings(settings)

    def test_production_remote_classifier_requires_token(self):
        settings = self._production_settings(
            classifier_mode="REMOTE",
            classifier_service_url="https://gpu-classifier.internal/v1/classify",
            classifier_service_token="",
            gateway_mode="LIVE",
            openai_api_key="key",
        )

        with self.assertRaises(RuntimeError):
            _validate_runtime_settings(settings)

    def test_production_remote_classifier_with_https_and_token_is_valid(self):
        settings = self._production_settings(
            classifier_mode="REMOTE",
            classifier_service_url="https://gpu-classifier.internal/v1/classify",
            classifier_service_token="token",
            gateway_mode="LIVE",
            openai_api_key="key",
        )

        _validate_runtime_settings(settings)


if __name__ == "__main__":
    unittest.main()
