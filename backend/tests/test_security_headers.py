import unittest

from starlette.responses import Response

from app.main import SECURITY_HEADERS, _apply_security_headers


class SecurityHeadersTests(unittest.TestCase):
    def test_default_security_headers_are_added(self):
        response = _apply_security_headers(Response())

        for name, value in SECURITY_HEADERS.items():
            self.assertEqual(response.headers[name], value)

    def test_existing_header_is_not_overwritten(self):
        response = Response(headers={"X-Frame-Options": "SAMEORIGIN"})

        _apply_security_headers(response)

        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")


if __name__ == "__main__":
    unittest.main()


class StrictHeaderTests(unittest.TestCase):
    def test_api_responses_get_a_deny_all_csp(self):
        from app.main import API_CONTENT_SECURITY_POLICY

        response = _apply_security_headers(Response(), "/api/v1/jobs")
        self.assertEqual(response.headers["Content-Security-Policy"], API_CONTENT_SECURITY_POLICY)
        self.assertNotIn("Strict-Transport-Security", response.headers)

    def test_hsts_only_in_production(self):
        response = _apply_security_headers(Response(), "/api/v1/jobs", production=True)
        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])

    def test_dev_swagger_page_is_not_broken_by_csp(self):
        self.assertNotIn("Content-Security-Policy", _apply_security_headers(Response(), "/docs").headers)
