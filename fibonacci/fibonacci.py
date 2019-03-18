'''Calculate the n-th Fibonacci number'''


def calculate(*, n: int) -> int:
    '''Calculate the n-th Fibonacci number'''
    if type(n) is not int or n == 0:
        raise TypeError('n must be an integer greater than 0 (zero)')

    if n == 1:
        return 0

    if n == 2:
        return 1

    return calculate(n=n-1) + calculate(n=n-2)
