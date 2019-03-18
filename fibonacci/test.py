'''Test cases for Fibonacci calculation'''
import unittest
import fibonacci


class TestFibonacci(unittest.TestCase):
    '''Test cases for Fibonacci calculation'''

    def test_fibonacci_sequence(self):
        '''Test a known sequence of Fibonacci numbers'''
        # Source: https://en.wikipedia.org/wiki/Fibonacci_number
        known_fibonacci_sequence = {
            1: 0,
            2: 1,
            3: 1,
            4: 2,
            5: 3,
            6: 5,
            7: 8,
            8: 13,
            9: 21,
            10: 34,
            11: 55,
            12: 89,
            13: 144,
            14: 233,
            15: 377,
            16: 610,
            17: 987,
            18: 1597,
            19: 2584,
            20: 4181,
            21: 6765,
        }

        for n_th, expected_result in known_fibonacci_sequence.items():
            calculated = fibonacci.calculate(n=n_th)

            self.assertEqual(first=calculated, second=expected_result)


if __name__ == '__main__':
    unittest.main()
