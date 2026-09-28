import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.gateway import (
    GatewayConfigurationError,
    LocalMockGateway,
    MultiProviderGateway,
    build_gateway,
)


def _settings(**overrides):
    base = dict(gateway_mode="MOCK", openai_api_key="", anthropic_api_key="")
    base.update(overrides)
    return SimpleNamespace(**base)


class GatewayConfigurationTests(unittest.TestCase):
    def test_mock_mode_is_local_and_does_not_echo_prompt(self):
        with patch("app.gateway.Settings", return_value=_settings(gateway_mode="MOCK")):
            gateway = build_gateway()

        self.assertIsInstance(gateway, LocalMockGateway)
        response = gateway.send(
            provider="openai",
            model="gpt-4o-mini",
            prompt="password: should never be echoed",
        )
        self.assertNotIn("password", response.content)

    def test_live_mode_without_any_key_configures_no_provider(self):
        with patch("app.gateway.Settings", return_value=_settings(gateway_mode="LIVE")):
            gateway = build_gateway()

        self.assertIsInstance(gateway, MultiProviderGateway)
        with self.assertRaises(GatewayConfigurationError):
            gateway.send(provider="openai", model="gpt-4o-mini", prompt="hello")
        with self.assertRaises(GatewayConfigurationError):
            gateway.send(provider="anthropic", model="claude-sonnet-5", prompt="hello")

    def test_live_mode_rejects_unknown_provider(self):
        with patch("app.gateway.Settings", return_value=_settings(gateway_mode="LIVE")):
            gateway = build_gateway()

        with self.assertRaisesRegex(GatewayConfigurationError, "지원하지 않는 provider"):
            gateway.send(provider="gemini", model="gemini-pro", prompt="hello")

    def test_live_mode_builds_only_the_configured_providers(self):
        with patch(
            "app.gateway.Settings",
            return_value=_settings(gateway_mode="LIVE", openai_api_key="sk-test-key"),
        ):
            gateway = build_gateway()

        self.assertIn("openai", gateway._adapters)
        self.assertNotIn("anthropic", gateway._adapters)

    def test_unknown_mode_fails_closed(self):
        with patch(
            "app.gateway.Settings",
            return_value=_settings(gateway_mode="OPENAI"),
        ):
            with self.assertRaises(GatewayConfigurationError):
                build_gateway()


if __name__ == "__main__":
    unittest.main()
