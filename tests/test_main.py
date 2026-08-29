import unittest

from main import build_parser


class CliTests(unittest.TestCase):
    def test_default_approval_mode_asks_for_medium_risk_operations(self):
        args = build_parser().parse_args([])
        self.assertEqual(args.approval_mode, "ask")
        self.assertFalse(args.auto_approve)

    def test_auto_approve_conflicts_with_explicit_approval_mode(self):
        args = build_parser().parse_args(["--auto-approve", "--approval-mode", "strict"])
        from main import create_agent
        with self.assertRaises(SystemExit):
            create_agent(args)


if __name__ == "__main__":
    unittest.main()
