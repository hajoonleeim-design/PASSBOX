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
    base = dict(gateway_mode="MOCK", openai_api_key="", anthropic_api_key="", gemini_api_key="")
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
            gateway.send(provider="mistral", model="mistral-small", prompt="hello")

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


class GeminiGatewayTests(unittest.TestCase):
    def _gateway(self, handler):
        import httpx

        from app.gateway import GeminiGateway

        return GeminiGateway("test-secret-key", transport=httpx.MockTransport(handler))

    def test_sends_prompt_and_returns_text_with_key_in_header_not_url(self):
        import httpx

        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["key"] = request.headers.get("x-goog-api-key")
            import json

            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "안녕하세요 "}, {"text": "반갑습니다"}]}}]})

        reply = self._gateway(handler).send(model="gemini-3.5-flash-lite", prompt="인사해줘")
        self.assertEqual(reply.content, "안녕하세요 반갑습니다")
        self.assertEqual(seen["key"], "test-secret-key")
        self.assertNotIn("test-secret-key", seen["url"])
        self.assertIn("gemini-3.5-flash-lite:generateContent", seen["url"])
        self.assertEqual(seen["body"]["contents"][0]["parts"][0]["text"], "인사해줘")

    def test_errors_never_leak_the_api_key(self):
        import httpx

        for response in (httpx.Response(403, json={"error": {"message": "bad key test-secret-key"}}),
                         httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}),
                         httpx.Response(200, json={"candidates": []})):
            with self.assertRaises(RuntimeError) as ctx:
                self._gateway(lambda request, r=response: r).send(model="m", prompt="p")
            self.assertNotIn("test-secret-key", str(ctx.exception))

    def test_live_mode_registers_gemini_when_key_present(self):
        with patch("app.gateway.Settings", return_value=_settings(gateway_mode="LIVE", gemini_api_key="k")):
            gateway = build_gateway()
        self.assertIn("gemini", gateway._adapters)
        self.assertNotIn("openai", gateway._adapters)
