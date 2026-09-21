import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.gateway import (
    GatewayConfigurationError,
    LocalMockGateway,
    UnconfiguredOpenAIGateway,
    build_gateway,
)


class GatewayConfigurationTests(unittest.TestCase):
    def test_mock_mode_is_local_and_does_not_echo_prompt(self):
        with patch(
            "app.gateway.Settings",
            return_value=SimpleNamespace(gateway_mode="MOCK", openai_api_key=""),
        ):
            gateway = build_gateway()

        self.assertIsInstance(gateway, LocalMockGateway)
        response = gateway.send(
            provider="openai",
            model="gpt-4o-mini",
            prompt="password: should never be echoed",
        )
        self.assertNotIn("password", response.content)

    def test_openai_without_key_is_explicitly_unconfigured(self):
        with patch(
            "app.gateway.Settings",
            return_value=SimpleNamespace(gateway_mode="OPENAI", openai_api_key=""),
        ):
            gateway = build_gateway()

        self.assertIsInstance(gateway, UnconfiguredOpenAIGateway)
        with self.assertRaises(GatewayConfigurationError):
            gateway.send(provider="openai", model="gpt-4o-mini", prompt="hello")

    def test_unknown_mode_fails_closed(self):
        with patch(
            "app.gateway.Settings",
            return_value=SimpleNamespace(gateway_mode="OPNEAI", openai_api_key=""),
        ):
            with self.assertRaises(GatewayConfigurationError):
                build_gateway()


if __name__ == "__main__":
    unittest.main()
