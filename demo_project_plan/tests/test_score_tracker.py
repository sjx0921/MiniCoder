import unittest

from score_tracker import record_score, score_summary


class ScoreTrackerTests(unittest.TestCase):
    def test_record_score_rejects_out_of_range_values(self):
        scores = []
        record_score(scores, 75)
        self.assertEqual(scores, [75])
        with self.assertRaises(ValueError):
            record_score(scores, 101)

    def test_summary_returns_precise_average(self):
        self.assertEqual(score_summary([80, 81]), {"count": 2, "average": 80.5})

    def test_empty_summary_uses_float_average(self):
        self.assertEqual(score_summary([]), {"count": 0, "average": 0.0})


if __name__ == "__main__":
    unittest.main()
