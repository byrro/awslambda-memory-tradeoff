'''Lambda Fibonacci code'''
from typing import (
    Dict,
)
import fibonacci
import constants as c


first_run = True


def handler(event: Dict, context: Dict) -> Dict:
    '''Lambda handler function'''
    global first_run

    cold_start = True if first_run else False

    first_run = False

    n = event.get('n', c.DEFAULT_FIBONACCI_N)

    n_th = fibonacci.calculate(n=n)

    return {
        'cold_start': cold_start,
        'n_th': n_th,
    }


if __name__ == '__main__':
    event = {
        'n': 30,
    }

    response = handler(event=event, context={})

    print(response)
