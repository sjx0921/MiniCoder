import unittest

from calculator import average


class CalculatorTests(unittest.TestCase):
    def test_average_returns_zero_for_empty_values(self):
        self.assertEqual(average([]), 0.0)

    def test_average_preserves_fractional_results(self):
        self.assertEqual(average([80, 81]), 80.5)

    def test_average_returns_whole_result_when_evenly_divisible(self):
        self.assertEqual(average([2, 4, 6]), 4)


if __name__ == "__main__":
    unittest.main()
