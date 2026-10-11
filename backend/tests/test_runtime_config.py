import unittest

from app.db import Settings
from app.main import _validate_runtime_settings


class RuntimeConfigurationTests(unittest.TestCase):
    def production_settings(self, **overrides):
        values = {
            "app_env": "production",
            "database_url": "postgresql+psycopg://user:password@db/passbox",
            "jwt_secret_key": "x" * 64,
            "data_encryption_key": "k" * 48,
            "clamav_mode": "required",
            "gateway_mode": "LIVE",
            "openai_api_key": "sk-test-key",
            "cors_allowed_origins": "https://passbox.example",
            # Pinned so a developer's local .env (e.g. REMOTE over http) can't leak in.
            "classifier_mode": "LOCAL_RULES",
        }
        values.update(overrides)
        return Settings(**values)

    def test_valid_production_configuration_passes(self):
        _validate_runtime_settings(self.production_settings())

    def test_production_rejects_mock_gateway(self):
        with self.assertRaisesRegex(RuntimeError, "MOCK"):
            _validate_runtime_settings(
                self.production_settings(gateway_mode="MOCK")
            )

    def test_production_rejects_insecure_cors_origin(self):
        with self.assertRaisesRegex(RuntimeError, "HTTPS"):
            _validate_runtime_settings(
                self.production_settings(cors_allowed_origins="http://localhost:5173")
            )

    def test_development_keeps_local_defaults(self):
        _validate_runtime_settings(Settings(app_env="development"))

    def test_gateway_mode_must_be_mock_or_live(self):
        with self.assertRaisesRegex(RuntimeError, "GATEWAY_MODE"):
            _validate_runtime_settings(Settings(gateway_mode="OPENAI"))

    def test_production_live_gateway_requires_at_least_one_provider_key(self):
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY, ANTHROPIC_API_KEY or GEMINI_API_KEY"):
            _validate_runtime_settings(
                self.production_settings(openai_api_key="", anthropic_api_key="", gemini_api_key="")
            )

    def test_production_live_gateway_accepts_anthropic_key_alone(self):
        _validate_runtime_settings(
            self.production_settings(openai_api_key="", anthropic_api_key="sk-ant-test")
        )



class PlaintextClassifierWarningTests(unittest.TestCase):
    def test_warns_for_http_to_another_host_but_not_loopback(self):
        from app.main import _warn_if_plaintext_off_host

        with self.assertLogs("passbox.config", level="WARNING"):
            _warn_if_plaintext_off_host("http://10.10.70.50:8100")
        with self.assertNoLogs("passbox.config", level="WARNING"):
            _warn_if_plaintext_off_host("http://127.0.0.1:8100")
            _warn_if_plaintext_off_host("https://classifier.internal")


if __name__ == "__main__":
    unittest.main()


class EncryptionKeyRequirementTests(unittest.TestCase):
    def test_production_requires_a_data_encryption_key(self):
        settings = RuntimeConfigurationTests().production_settings(data_encryption_key="")
        with self.assertRaisesRegex(RuntimeError, "DATA_ENCRYPTION_KEY"):
            _validate_runtime_settings(settings)
