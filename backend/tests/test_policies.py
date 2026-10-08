import unittest

from app.api.policies import _next_version


class PolicyVersionTests(unittest.TestCase):
    def test_increments_local_template_version(self):
        self.assertEqual(_next_version("LOCAL-TEMPLATE-v1"), "LOCAL-TEMPLATE-v2")

    def test_increments_numeric_suffix(self):
        self.assertEqual(_next_version("POLICY-v1.3"), "POLICY-v1.4")

    def test_adds_suffix_when_version_has_no_number(self):
        self.assertEqual(_next_version("POLICY"), "POLICY-2")


if __name__ == "__main__":
    unittest.main()


class BuiltinDetectionPatternTests(unittest.TestCase):
    """The admin screen's detection-rule list used to be two hard-coded rows whose
    on/off switch the scanner never read. It must mirror the scanner exactly."""

    def test_admin_list_matches_every_scanner_rule(self):
        from app.api.policies import BUILTIN_DETECTION_PATTERNS
        from app.security_scan import _RULES

        listed = {p["pattern_id"].removeprefix("builtin-").upper() for p in BUILTIN_DETECTION_PATTERNS}
        self.assertEqual(listed, {rule.category for rule in _RULES})
        self.assertTrue(all(p["enabled"] for p in BUILTIN_DETECTION_PATTERNS))
        self.assertTrue(all(p["description"] for p in BUILTIN_DETECTION_PATTERNS))
