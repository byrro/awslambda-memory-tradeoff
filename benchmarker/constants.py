'''Constant values for memory benchmark Lambda'''


IGNORE_COLDSTART = True
DEFAULT_TEST_COUNT = 50
DEFAULT_MAX_THREADS = 10
DEFAULT_LAMBDA_FUNCTION = 'fibonacci'
DEFAULT_LAMBDA_EVENT = {
    'n': 30,
}
DEFAULT_MEMORY_SETS = [
    128,
    256,
    512,
    768,
    1024,
    1536,
    2048,
    2560,
    3008,
]