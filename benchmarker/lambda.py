'''AWS Lambda to benchmark performance with different memory allocations'''
import json
from typing import Dict
from benchmark import Benchmark
from utils import (
    validate_event,
)


def handler(event: Dict, context: Dict) -> Dict:
    '''Lambda handler function

    Arguments accepted in event:

    :verbose: (bool) whether to run in verbose mode with log output
    :ignore_coldstart: (bool) whether to ignore results from cold starts when
        computing Lambda performance speed
    :test_count: (int) how many tests to run with each memory allocation
    :max_threads: (int) maximum number of threads to run concurrently
    :lambda_function: (str) Lambda function to invoke and benchmark
    :lambda_event: (dict) event to provide the Lambda
    :memory_sets: (list) list of memory allocations to benchmark
        AWS Lambda accepts memory from 128 to 3008 Mb in increments of 128 Mb
    '''
    valid, error = validate_event(event=event)

    if not valid:
        return {
            'success': False,
            'error': error,
        }

    # Log event payload for debugging and security purposes
    print(json.dumps(event))

    benchmarking = Benchmark(**event)

    results = benchmarking.run().results

    return {
        'results': results,
    }


if __name__ == '__main__':
    import pprint

    pp = pprint.PrettyPrinter(indent=4)

    event = {
        'verbose': True,
        'ignore_coldstart': True,
        'test_count': 50,
        'max_threads': 10,
        'lambda_function': 'fibonacci',
        'lambda_event': {'n': 30},
        'memory_sets': [128, 256, 512, 768, 1024, 1536, 2048, 2560, 3008],
    }

    results = handler(event=event, context={})

    pp.pprint(results)
