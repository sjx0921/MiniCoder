"""Tests for the text_utils module."""
import unittest

from text_utils import normalize_text


class NormalizeTextTests(unittest.TestCase):
    def test_strips_outer_whitespace(self):
        self.assertEqual(normalize_text("  hello  "), "hello")

    def test_collapses_consecutive_inner_spaces(self):
        # BUG: consecutive inner spaces are not merged into a single space.
        self.assertEqual(normalize_text("a   b    c"), "a b c")

    def test_null_input_returns_none(self):
        self.assertIsNone(normalize_text(None))


if __name__ == "__main__":
    unittest.main()
