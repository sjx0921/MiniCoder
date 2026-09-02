import unittest

from text_utils import normalize_text


class TextUtilsTests(unittest.TestCase):
    def test_normalize_text_preserves_none(self):
        self.assertIsNone(normalize_text(None))

    def test_normalize_text_trims_outer_whitespace(self):
        self.assertEqual(normalize_text("  hello  "), "hello")

    def test_normalize_text_collapses_internal_whitespace(self):
        self.assertEqual(normalize_text("  hello\t\nworld   again "), "hello world again")


if __name__ == "__main__":
    unittest.main()
