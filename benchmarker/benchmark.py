'''Routine to benchmark Lambda performance with different memory allocations'''
from concurrent.futures import (
    ThreadPoolExecutor,
)
import json
import time
from typing import (
    Dict,
    List,
    Union,
)
import constants as c
import custom_exceptions as custom_exc
from utils import (
    get_lambda_config,
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
        # Public attributes
        self.verbose = verbose
        self.ignore_coldstart = ignore_coldstart
        self.test_count = test_count
        self.max_threads = max_threads
        self.lambda_function = lambda_function
        self.lambda_event = lambda_event
        self.memory_sets = memory_sets

        # Internal attributes
        self._results = {}
        self._benchmark_results = []
        self._original_config = {
            'memory': None,
            'timeout': None,
        }

    @property
    def results(self):
        return self._results

    @property
    def original_config(self):
        return self._original_config

    @property
    def original_config_str(self):
        config_options = []

        for key, val in self.original_config.items():
            config_options.append(f'{key}: {str(val)}')

        return ', '.join(config_options)

    def set_original(
            self,
            *,
            memory: Union[int, None] = None,
            timeout: Union[int, None] = None,
            ) -> Dict:
        '''Set value for original Lambda configuration parameter'''
        result = {'memory': False, 'timeout': False}

        if type(memory) is int:
            self._original_config['memory'] = memory
            result['memory'] = True

        elif type(memory) is not None:
            raise custom_exc.SetOriginalConfigError(
                f'Error setting reference for memory ({memory}) original '
                'Lambda configuration'
            )

        if type(timeout) is int:
            self._original_config['timeout'] = timeout
            result['timeout'] = True

        elif type(timeout) is not None:
            raise custom_exc.SetOriginalConfigError(
                f'Error setting reference for timeout ({timeout}) original '
                'Lambda configuration'
            )

        return result

    def store_original_config(self) -> tuple:
        '''Get original Lambda configuration to restore after benchmarking'''
        result = {
            'memory': None,
            'timeout': None,
            'error': None,
        }

        try:
            config = get_lambda_config(
                function_name=self.lambda_function,
            )

            success = self.is_lambda_response_success(
                operation='get_lambda_config',
                response=config,
            )

            if not success:
                error = custom_exc.StoreOriginalConfigError(
                    'Invalid configuration parameters returned for Lambda '
                    f'({self.lambda_function})'
                )

                result['error'] = error

                logger.warning(error)
                logger.warning(f'Lambda API response: {str(config)}')

            else:
                self.set_original(
                    memory=config['Memory'],
                    timeout=config['Timeout'],
                )

                result['memory'] = config['Memory']
                result['timeout'] = config['Timeout']

        except Exception as exc:
            error = custom_exc.StoreOriginalConfigError(
                'Could not get original configuration for Lambda '
                f'({self.lambda_function})'
            )

            result['error'] = error

            logger.warning(error)
            logger.exception(exc)

        return result

    def restore_original_config(self, original_config: Dict) -> bool:
        '''Restore original Lambda configuration'''
        return True

    def run(self) -> Dict[str, Dict]:
        '''Run benchmarking routine'''
        self.results = {}
        self.benchmark_results = []

        store_config_result = self.store_original_config()

        if store_config_result['error']:
            raise store_config_result['error']

        for memory in self.memory_sets:
            benchmark_result = self.benchmark_memory(memory=memory)
            self.benchmark_results.append(benchmark_result)

        self.process_benchmark_results(
            benchmark_results=self.benchmark_results
        )

        restored, restore_error = self.restore_original_config(
            config=self.original_config
        )

        if not restored:
            error = custom_exc.RestoreOriginalConfigError(
                f'Cannot restore Lambda ({self.lambda_function}) original '
                f'configurations: {self.original_config_str}'
            )

            logger.warning(error)
            logger.exception(restore_error)

        return self

    def benchmark_memory(self, *, memory: int) -> Dict:
        '''Benchmark a given memory size'''
        result = {
            'memory': memory,
            'success': None,
            'durations': [],
            'errors': [],
        }

        response, success, error = self.set_memory(new_memory=memory)

        time.sleep(c.SLEEP_AFTER_NEW_MEMORY_SET)

        if not success:
            result['success'] = False
            result['errors'].append(str(error))

            logger.warning(error)
            logger.warning('Lambda API response:')
            print(json.dumps(response))

        while len(result['durations']) < self.test_count:
            with ThreadPoolExecutor(self.max_threads) as executor:
                result = executor.map(self.check_execution_time)

                if result['success'] and not result['cold_start']:
                    result['durations'].extend(result['duration'])

        return result

    def process_benchmark_results(self, *, benchmark_results) -> Dict:
        '''Process results from Lambda benchmarking'''
        pass

    def set_memory(
            self,
            *,
            new_memory: int,
            new_timeout: int = c.DEFAULT_LAMBDA_TIMEOUT
            ) -> bool:
        '''Set new memory for the Lambda'''
        response = None
        success = False
        error = None

        try:
            response = update_lambda_config(
                function_name=self.lambda_function,
                memory_size=new_memory,
                timeout=new_timeout,
            )

            success = self.is_lambda_response_success(
                operation='set_memory',
                response=response,
            )

        except Exception as exc:
            error = custom_exc.SetLambdaMemoryError(
                f'Cannot allocate new memory size ({new_memory} mb) to '
                f'function ({self.lambda_function})'
            )

            logger.warning(error)
            logger.exception(exc)

        return response, success, error

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
            if type(response.get('Payload')) is not dict:
                error = custom_exc.LambdaPayloadError(
                    'Error in Lambda response Payload (type is not a Dict)'
                )

                logger.warning(error)

                result['error'] = str(error)

            elif type(response['Payload'].get('remaining_time')) is not int:
                error = custom_exc.LambdaPayloadError(
                    'No Integer "remaining_time" in Lambda Payload'
                )

                logger.warning(error)

                result['error'] = str(error)

            else:
                result['success'] = True

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

    def is_lambda_response_success(self, *, operation, response):
        '''Validate Lambda response'''
        if type(response) is not dict:
            return False

        elif operation == 'get_lambda_config':
            if 'Memory' in response and 'Timeout' in response:
                return True

            else:
                return False

        elif response['StatusCode'] in (200, 202, 204):
            return True

        else:
            return False


if __name__ == '__main__':
    pass
