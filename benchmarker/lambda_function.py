'''AWS Lambda to benchmark performance with different memory allocations'''
from typing import Dict
from benchmark import Benchmark
import custom_exceptions as custom_exc
from utils import (
    logger,
    print_payload,
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
    try:
        # Log event payload for debugging and security purposes
        print_payload(payload_type='event', payload_obj=event)

        valid, error = validate_event(event=event)

        if not valid:
            response = {
                'status': 400,
                'results': [],
                'errors': [error],
            }

        else:
            benchmarking = Benchmark(**event)

            results = benchmarking.run()

            response = {
                'status': 200,
                'results': results,
                'errors': benchmarking.public_errors,
            }

    except Exception as error:
        if isinstance(error, custom_exc.CustomBenchmarkException):
            response = {
                'status': 500,
                'results': [],
                'errors': [
                    f'{type(error).__name__}: {str(error)}',
                ],
            }

        else:
            logger.error(error)
            logger.exception(error)

            response = {
                'status': 500,
                'results': [],
                'errors': [
                    'Sorry there was an internal error',
                ]
            }

    # Log response object for debugging and security purposes
    print_payload(payload_type='response', payload_obj=response)

    return response


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
