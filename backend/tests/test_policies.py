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
