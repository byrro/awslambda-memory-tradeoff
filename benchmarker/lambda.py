'''AWS Lambda to benchmark performance with different memory allocations'''
from typing import Dict
from benchmark import Benchmark
import constants as c


def handler(event: Dict, context: Dict) -> Dict:
    '''Lambda handler function

    Arguments expected in event:

    :ignore_coldstart: (bool) whether to ignore results from cold starts when
        computing Lambda performance speed
    :test_count: (int) how many tests to run with each memory allocation
    :max_threads: (int) maximum number of threads to run concurrently
    :lambda_function: (str) Lambda function to invoke and benchmark
    :lambda_event: (dict) event to provide the Lambda
    :memory_sets: (list) list of memory allocations to benchmark
        AWS Lambda accepts memory from 128 to 3008 Mb in increments of 128 Mb
    '''
    benchmarking = Benchmark(**event)

    benchmarking.run()

    return {
        'results': benchmarking.results,
    }


if __name__ == '__main__':
    event = {
        'max_threads': 10,
        'lambda_function': 'fibonacci',
        'lambda_event': {
            'n': 30,
        },
        'fibonacci_nth': 30,
        'memory_sets': [
            128,
            256,
            512,
            768,
            1024,
            1536,
            2048,
            2560,
            3008,
        ],
    }
