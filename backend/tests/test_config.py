import unittest

from app.main import _parse_cors_origins


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


if __name__ == "__main__":
    unittest.main()
