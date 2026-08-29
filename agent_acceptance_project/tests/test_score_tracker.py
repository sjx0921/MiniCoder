"""Tests for the score_tracker module."""
import unittest

from score_tracker import add_score, average


class AddScoreTests(unittest.TestCase):
    def test_adds_valid_score_within_range(self):
        scores = []
        result = add_score(scores, 85)
        self.assertEqual(result, [85])

    def test_out_of_range_score_is_rejected(self):
        # BUG: add_score does not validate the 0..100 range.
        scores = []
        result = add_score(scores, 150)
        self.assertNotIn(150, result)


class AverageTests(unittest.TestCase):
    def test_average_of_empty_list_is_zero(self):
        self.assertEqual(average([]), 0)

    def test_average_returns_float_for_fractional_mean(self):
        # BUG: integer division drops the fractional part.
        self.assertEqual(average([90, 99]), 94.5)


if __name__ == "__main__":
    unittest.main()
