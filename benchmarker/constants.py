'''Constant values for memory benchmark Lambda'''


VALID_EVENT_ARGS = [
    'verbose',
    'ignore_coldstart',
    'test_count',
    'max_threads',
    'lambda_function',
    'lambda_event',
    'memory_sets',
]
IGNORE_COLDSTART = True
DEFAULT_TEST_COUNT = 6
DEFAULT_MAX_THREADS = 2
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
DEFAULT_LAMBDA_TIMEOUT = 300000
SLEEP_AFTER_NEW_MEMORY_SET = 2
