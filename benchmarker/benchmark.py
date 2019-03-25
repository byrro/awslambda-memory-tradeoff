'''Routine to benchmark Lambda performance with different memory allocations'''
import concurrent.futures
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
    lambda_execution_cost,
    logger,
    update_lambda_config,
)


class Benchmark():
    '''Routine to benchmark Lambda with different memory allocations'''

    def __init__(
            self,
            *,
            verbose: bool = False,
            ignore_coldstart: bool = c.IGNORE_COLDSTART,
            test_count: int = c.DEFAULT_TEST_COUNT,
            max_threads: int = c.DEFAULT_MAX_THREADS,
            lambda_function: str = c.DEFAULT_LAMBDA_FUNCTION,
            lambda_event: Dict = c.DEFAULT_LAMBDA_EVENT,
            memory_sets: List[int] = c.DEFAULT_MEMORY_SETS,
            timeout: int = c.DEFAULT_LAMBDA_TIMEOUT,
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
        self.timeout = timeout

        # Internal attributes
        self.results = {}
        self.benchmark_results = []
        self.public_errors = []
        self.original_config = {
            'memory': None,
            'timeout': None,
        }

        self.verbose_log([
            'Initialized Benchmark with the following params:'
            f'verbose: {self.verbose}, '
            f'ignore_coldstart: {self.ignore_coldstart}, '
            f'test_count: {self.test_count}, ',
            f'max_threads: {self.max_threads}, ',
            f'lambda_function: {self.lambda_function}, '
            f'lambda_event: {json.dumps(self.lambda_event)}, '
            f'memory_sets: {json.dumps(self.memory_sets)}'
        ])

    @property
    def original_config_str(self):
        config_options = []

        for key, val in self.original_config.items():
            config_options.append(f'{key}: {str(val)}')

        return ', '.join(config_options)

    def verbose_log(self, log):
        '''Print logs in verbose mode'''
        if not self.verbose:
            return None

        if type(log) is str:
            print(log)

        elif type(log) is list:
            for item in log:
                self.verbose_log(item)

    def set_original(
            self,
            *,
            memory: Union[int, None] = None,
            timeout: Union[int, None] = None,
            ) -> Dict:
        '''Set value for original Lambda configuration parameter'''
        result = {'memory': False, 'timeout': False}

        if type(memory) is int:
            self.original_config['memory'] = memory
            result['memory'] = True

        elif type(memory) is not None:
            raise custom_exc.SetOriginalConfigError(
                f'Error setting reference for memory ({memory}) original '
                'Lambda configuration'
            )

        if type(timeout) is int:
            self.original_config['timeout'] = timeout
            result['timeout'] = True

        elif type(timeout) is not None:
            raise custom_exc.SetOriginalConfigError(
                f'Error setting reference for timeout ({timeout}) original '
                'Lambda configuration'
            )

        return result

    def store_original_config(self) -> tuple:
        '''Get original Lambda configuration to restore after benchmarking'''
        self.verbose_log('Storing original Lambda configuration parameters')

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
        self.verbose_log('Restoring original Lambda configuration parameters')

        response, success, error = self.set_new_config(
            new_memory=original_config['memory'],
            new_timeout=original_config['timeout'],
        )

        return {
            'success': success,
            'error': error,
            'response': response,
        }

    def append_public_error(self, *, error):
        '''Append an error to public_errors attribute'''
        if type(error) is list:
            for err in error:
                self.append_public_error(error=err)

        else:
            self.public_errors.append(f'{type(error).__name__}: {str(error)}')

    def run(self) -> Dict[str, Dict]:
        '''Run benchmarking routine'''
        self.verbose_log('Started running benchmarking')

        # Reset results attributes
        self.results = []
        self.benchmark_results = []

        store_config_result = self.store_original_config()

        if store_config_result['error']:
            raise store_config_result['error']

        # Cannot run this in parallel because we have only one Lambda to test
        # To run parallel memory benchmarks, we'd need to deploy the same code
        # in multiple Lambdas; within each benchmark we use concurrent threads
        for memory in self.memory_sets:
            self.benchmark_results.append(self.benchmark_memory(memory=memory))

        self.results = self.process_benchmark_results(
            results=self.benchmark_results,
        )

        restore_config_result = self.restore_original_config(
            original_config=self.original_config,
        )

        if not restore_config_result['success']:
            error = custom_exc.RestoreOriginalConfigError(
                f'Cannot restore Lambda ({self.lambda_function}) original '
                f'configurations: {self.original_config_str}'
            )

            self.append_public_error(error=error)

            logger.warning(error)

        self.verbose_log('Ended running benchmarking')

        return self.results

    def benchmark_memory(self, *, memory: int) -> Dict:
        '''Benchmark a given memory size'''
        self.verbose_log(f'  START benchmarking memory: {memory}')

        result = {
            'memory': memory,
            'success': True,
            'durations': [],
            'average_duration': None,
            'errors': [],
        }

        response, success, error = self.set_new_config(
            new_memory=memory,
            new_timeout=self.timeout,
        )

        if not success:
            result['success'] = False
            result['errors'].append(str(error))

            logger.warning(error)
            logger.warning(f'Lambda API response: {str(response)}')

            return result

        time.sleep(c.SLEEP_AFTER_NEW_MEMORY_SET)

        result['durations'] = self.get_benchmark_durations()

        if len(result['durations']) == 0:
            error = custom_exc.InvokeLambdaError(
                'No durations were returned from invocations of Lambda '
                f'({self.lambda_function}) with memory {memory}'
            )

            result['success'] = False
            result['errors'].append(error)

            logger.warning(error)

            return result

        result['average_duration'] = \
            round(sum(result['durations']) / len(result['durations']))

        self.verbose_log(f'  DONE benchmarking memory: {memory}')

        return result

    def get_benchmark_durations(self) -> list:
        '''Run benchmarking of a given memory size'''
        durations = []
        runs = 0
        max_runs = self.test_count / self.max_threads + 5

        while len(durations) < self.test_count:
            pending = self.test_count - len(durations)
            threads = min(self.max_threads, pending)

            self.verbose_log(
                f'    Pending checks: {pending}, threads: {threads}')

            with concurrent.futures.ThreadPoolExecutor(threads) as executor:
                invoke_futures = [
                    executor.submit(self.get_execution_time)
                    for i in range(0, threads)
                ]

                for future in concurrent.futures.as_completed(invoke_futures):
                    invocation = future.result()

                    if invocation['success'] and not invocation['cold_start']:
                        durations.append(invocation['duration'])

                durations_count = len(durations)

                self.verbose_log(
                    f'    Durations count: {durations_count}')

            # Avoid falling in an infinite loop
            if runs >= max_runs:
                break
            else:
                runs += 1

        return durations

    def set_new_config(
            self,
            *,
            new_memory: int,
            new_timeout: int,
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

    def get_execution_time(self) -> Dict:
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

                result['duration'] = self.timeout - \
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

    def process_benchmark_results(self, *, results: Dict) -> Dict:
        '''Process benchmark results'''
        processed = {
            'ranking': {
                'cost': [],
                'duration': [],
            },
            'logs': [],
            'notes': [
                'Lambda execution costs are in US$, following pricing page '
                'as of March 25, 2019 (https://aws.amazon.com/lambda/pricing)',
                'Lambda duration times are in milliseconds',
            ]
        }

        for benchmark in results:
            if not benchmark['success']:
                processed['logs'].append({
                    'memory': benchmark['memory'],
                    'success': False,
                    'errors': [str(error) for error in benchmark['errors']],
                })
                self.append_public_error(error=benchmark['errors'])

                continue

            # Calculate cost of execution for ranking
            try:
                execution_cost = lambda_execution_cost(
                    memory=benchmark['memory'],
                    duration=benchmark['average_duration'],
                )

            except Exception as error:
                logger.warning(error)
                logger.exception(error)
                self.append_public_error(error=error)

                processed['logs'].append({
                    'memory': benchmark['memory'],
                    'success': False,
                    'errors': [str(error)],
                })

                continue

            # Populate financial performance ranking
            processed['ranking']['cost'].append({
                'memory': benchmark['memory'],
                'cost': execution_cost,
            })

            # Populate speed performance ranking
            processed['ranking']['duration'].append({
                'memory': benchmark['memory'],
                'duration': benchmark['average_duration'],
            })

            # Populate benchmark details for debugging/verification purposes
            processed['logs'].append({
                'memory': benchmark['memory'],
                'succcess': False,
                'duration': {
                    'average': benchmark['average_duration'],
                    'all_invocations': benchmark['durations'],
                },
                'execution_cost': execution_cost,
            })

        # Order rankings by best performers
        processed['ranking']['cost'] = sorted(
            processed['ranking']['cost'],
            key=lambda k: k['cost'],
        )

        processed['ranking']['duration'] = sorted(
            processed['ranking']['duration'],
            key=lambda k: k['duration'],
        )

        return processed


if __name__ == '__main__':
    pass
