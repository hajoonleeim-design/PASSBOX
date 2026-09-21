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
