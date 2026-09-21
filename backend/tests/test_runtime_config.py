import unittest

from app.db import Settings
from app.main import _validate_runtime_settings


class RuntimeConfigurationTests(unittest.TestCase):
    def production_settings(self, **overrides):
        values = {
            "app_env": "production",
            "database_url": "postgresql+psycopg://user:password@db/passbox",
            "jwt_secret_key": "x" * 64,
            "gateway_mode": "OPENAI",
            "openai_api_key": "sk-test-key",
            "cors_allowed_origins": "https://passbox.example",
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


if __name__ == "__main__":
    unittest.main()
