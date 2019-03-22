'''Routine to benchmark Lambda performance with different memory allocations'''
from concurrent.futures import (
    ThreadPoolExecutor,
)
import json
import time
from typing import (
    Dict,
    List
)
import constants as c
import custom_exceptions as custom_exc
from utils import (
    invoke_lambda,
    logger,
    update_lambda_config,
)


class Benchmark():
    '''Routine to benchmark Lambda with different memory allocations'''

    def __init__(
            self,
            *,
            verbose: bool = True,
            ignore_coldstart: bool = c.IGNORE_COLDSTART,
            test_count: int = c.DEFAULT_TEST_COUNT,
            max_threads: int = c.DEFAULT_MAX_THREADS,
            lambda_function: str = c.DEFAULT_LAMBDA_FUNCTION,
            lambda_event: Dict = c.DEFAULT_LAMBDA_EVENT,
            memory_sets: List[int] = c.DEFAULT_MEMORY_SETS,
            **kwargs,
            ):
        self.verbose = verbose
        self.ignore_coldstart = ignore_coldstart
        self.test_count = test_count
        self.max_threads = max_threads
        self.lambda_function = lambda_function
        self.lambda_event = lambda_event
        self.memory_sets = memory_sets

        self.results = {
            memory: {'average': None, 'invocations': [], 'errors': []}
            for memory in self.memory_sets
        }

        self.original_config = {
            'timeout': None,
            'memory': None,
        }

        self.store_initial_config()

    def store_initial_config(self) -> Dict:
        '''Get original Lambda configuration to restore after benchmarking'''
        pass

    def run(self) -> Dict[str, Dict]:
        '''Run benchmarking routine'''
        for memory in self.memory_sets:
            benchmark_results = self.benchmark_memory(memory=memory)

            average, invocations, errors = self.process_results(
                results=benchmark_results,
            )

            self.results['average'] = average
            self.results['invocations'] = invocations
            self.results['errors'] = errors

        return self

    def benchmark_memory(self, *, memory: int) -> Dict:
        '''Benchmark a given memory size'''
        result = {
            'memory': memory,
            'success': None,
            'execution_times': [],
            'errors': [],
        }

        response, memory_set_success = self.set_memory(new_memory=memory)

        time.sleep(c.SLEEP_AFTER_NEW_MEMORY_SET)

        if not memory_set_success:
            result['success'] = False

            error = custom_exc.SetLambdaMemoryError(
                f'Cannot allocate new memory size ({memory} mb) to function '
                f'({self.lambda_function}).'
            )

            result['errors'].append(str(error))

            logger.warning(error)
            logger.warning('Lambda API response:')
            print(json.dumps(response))

        while len(result['execution_times']) < self.test_count:
            with ThreadPoolExecutor(self.max_threads) as executor:
                sub_results = executor.map(self.check_execution_time)

                result['execution_times'].extend(
                    [r for r in sub_results if not r['cold_start']])

        return result

    def populate_results(self, *, results) -> Dict:
        '''Process results from Lambda benchmarking'''
        pass

    def set_memory(
            self,
            *,
            new_memory: int,
            new_timeout: int = c.DEFAULT_LAMBDA_TIMEOUT
            ) -> bool:
        '''Set new memory for the Lambda'''
        response = update_lambda_config(
            function_name=self.lambda_function,
            memory_size=new_memory,
            timeout=new_timeout,
        )

        return response, self.is_lambda_response_success(
            operation='set_memory',
            response=response,
        )

    def is_lambda_response_success(self, *, operation, response):
        '''Validate Lambda response'''
        if response['StatusCode'] in (200, 202, 204):
            return True

        else:
            return False

    def check_execution_time(self) -> Dict:
        '''Invoke the Lambda function and check execution time'''
        result = {
            'success': False,
            'error': None,
            'duration': None,
            'cold_start': False,
        }

        try:
            response = invoke_lambda(
                function_name=self.lambda_function,
                payload=self.lambda_event,
                invocation_type='RequestResponse',
                log_type='None',
            )

            # Check whether payload has expected info
            if type(response.get('Payload')) is not dict or \
                    type(response['Payload'].get('remaining_time')) is not int:

                error = custom_exc.LambdaPayloadError(
                    'Error in Lambda response Payload (type is not a Dict)'
                )

                logger.warning(error)

                result['error'] = str(error)

            else:
                result['success'] = 200

                result['duration'] = c.DEFAULT_LAMBDA_TIMEOUT - \
                    response['Payload']['remaining_time']

                result['cold_start'] = \
                    response['Payload'].get('cold_start', False)

        except Exception as exc:
            error = custom_exc.InvokeLambdaError(
                f'Could not invoke Lambda ({self.lambda_function}) to check '
                f'the execution time - Exception: {type(exc).__name__}'
            )

            logger.warning(error)
            logger.exception(exc)

            result['error'] = str(error)

        return result


if __name__ == '__main__':
    pass
