import unittest

from main import build_parser


class CliTests(unittest.TestCase):
    def test_default_approval_mode_asks_for_medium_risk_operations(self):
        args = build_parser().parse_args([])
        self.assertEqual(args.approval_mode, "ask")
        self.assertFalse(args.auto_approve)


if __name__ == "__main__":
    unittest.main()
