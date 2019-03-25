'''Test cases for benchmark Lambda'''
import json
from random import randint
import threading
import unittest
from unittest.mock import (
    call,
    MagicMock,
    patch,
)
from benchmark import Benchmark
import constants as c
import custom_exceptions as custom_exc
from lambda_function import handler as lambda_handler
from utils import (
    get_lambda_config,
    invoke_lambda,
    lambda_execution_cost,
    update_lambda_config,
    validate_event,
)


TEST_REMAINING_TIME = 1000
COLD_START_TRUE = True
LAMBDA_STATE = iter([])
LAMBDA_REMAINING_TIME = iter([])


class CustomMock():
    '''Produces custom Mock objects for tests'''

    @staticmethod
    def get_lambda_config():
        '''Mock get_lambda_config utility function'''
        mock_response = {
            'FunctionName': c.DEFAULT_LAMBDA_FUNCTION,
            'Timeout': c.DEFAULT_LAMBDA_TIMEOUT,
            'Memory': c.DEFAULT_MEMORY_SETS[0],
        }
        return MagicMock(return_value=mock_response)

    @staticmethod
    def get_lambda_config_fail():
        '''Mock failure in the get_lambda_config'''
        return MagicMock(side_effect=KeyError('foobar'))

    @staticmethod
    def update_lambda_config():
        '''Mock response from setting new memory'''
        response = {
            'StatusCode': 200,
            'foo': 'bar',
        }
        return MagicMock(return_value=response)

    @staticmethod
    def update_lambda_config_fail():
        '''Mock update_lambda_config with Lambda API failure'''
        return MagicMock(side_effect=KeyError('foobar'))

    @staticmethod
    def invoke_lambda_cold_start():
        '''Mock response from invoke_lambda'''
        response = {
            'StatusCode': 200,
            'Payload': {
                'remaining_time': TEST_REMAINING_TIME,
                'cold_start': COLD_START_TRUE,
            },
        }
        return MagicMock(return_value=response)

    @staticmethod
    def invoke_lambda_fail():
        '''Mock invoke_lambda function raising an exception'''
        return MagicMock(side_effect=KeyError('foobar'))

    @staticmethod
    def invoke_lambda_payload_error():
        '''Mock invoke_lambda function with Payload error'''
        response = {
            'Payload': False,
        }
        return MagicMock(return_value=response)

    @staticmethod
    def invoke_lambda_miss_remaining_time():
        '''Mock invoke_lambda function without "remaining_time" in Payload'''
        response = {
            'Payload': {},
        }
        return MagicMock(return_value=response)

    @staticmethod
    def invoke_lambda_get_durations(*args, **kwargs):
        '''Mock response from invoke_lambda for time checks'''
        # Iterator is not atomic, need the thread lock because this object will
        # be called by multiple threads concurrently
        with threading.Lock():
            global LAMBDA_REMAINING_TIME
            global LAMBDA_STATE

            remaining_time = next(LAMBDA_REMAINING_TIME)
            cold_start = next(LAMBDA_STATE)

        mock_response = {
            'Payload': {
                'remaining_time': remaining_time,
                'cold_start': cold_start,
            }
        }

        return mock_response

    @staticmethod
    def benchmark_fail_regular(*args, **kwargs):
        '''Mock Benchmark class with Python exception'''
        return MagicMock(side_effect=KeyError('foobar'))

    @staticmethod
    def benchmark_fail_custom(*args, **kwargs):
        '''Mock Benchmark class with Custom exception'''
        return MagicMock(
            side_effect=custom_exc.CustomBenchmarkException('custom_foobar'))


class TestLambdaUtils(unittest.TestCase):
    '''Test utility functions'''

    def test_validate_event(self):
        '''Test validation of Lambda event payload'''
        args1 = None
        args2 = {'foo': 'bar'}
        args3 = {'verbose': None, 'ignore_coldstart': None, 'test_count': None,
                 'max_threads': None, 'lambda_function': None,
                 'lambda_event': None, 'memory_sets': None}

        valid1, error1 = validate_event(event=args1)
        valid2, error2 = validate_event(event=args2)
        valid3, error3 = validate_event(event=args3)

        self.assertFalse(valid1)
        self.assertIsNotNone(error1)

        self.assertFalse(valid2)
        self.assertIsNotNone(error2)

        self.assertTrue(valid3)
        self.assertIsNone(error3)

    @patch('utils.boto3')
    def test_update_function_memory(self, boto3):
        '''Test function that allocate new memory value for Lambda'''
        test_memory_size = 512

        update_lambda_config(
            function_name=c.DEFAULT_LAMBDA_FUNCTION,
            memory_size=test_memory_size,
        )

        boto3.session.Session.assert_called()

        client = boto3.session.Session().client
        client.assert_called_with('lambda')

        aws_lambda = client()
        aws_lambda.update_function_configuration.assert_called_with(
            FunctionName=c.DEFAULT_LAMBDA_FUNCTION,
            MemorySize=test_memory_size,
        )

    @patch('utils.boto3')
    def test_invoke_lambda(self, boto3):
        '''Test invocation of a Lambda function'''
        invocation_type = 'RequestResponse'
        log_type = 'None'

        invoke_lambda(
            function_name=c.DEFAULT_LAMBDA_FUNCTION,
            payload=c.DEFAULT_LAMBDA_EVENT,
            invocation_type=invocation_type,
            log_type=log_type,
        )

        boto3.session.Session.assert_called()

        client = boto3.session.Session().client
        client.assert_called_with('lambda')

        aws_lambda = client()
        aws_lambda.invoke.assert_called_with(
            FunctionName=c.DEFAULT_LAMBDA_FUNCTION,
            InvocationType=invocation_type,
            LogType=log_type,
            Payload=json.dumps(c.DEFAULT_LAMBDA_EVENT),
        )

    @patch('utils.boto3')
    def test_get_lambda_config(self, boto3):
        '''Test getting Lambda configuration'''
        get_lambda_config(
            function_name=c.DEFAULT_LAMBDA_FUNCTION,
        )

        boto3.session.Session.assert_called()

        client = boto3.session.Session().client
        client.assert_called_with('lambda')

        aws_lambda = client()
        aws_lambda.get_function_configuration.assert_called_with(
            FunctionName=c.DEFAULT_LAMBDA_FUNCTION,
        )

    def test_lambda_execution_cost(self):
        '''Test calculation of Lambda execution cost'''
        test_sets = [
            {
                'memory': 512,
                'duration': 98342,
                'expected_cost': round(0.000820656, 6),
            },
            {
                'memory': 1600,
                'duration': 536873,
                'expected_cost': round(0.013986245, 6),
            },
            {
                'memory': 3008,
                'duration': 49856,
                'expected_cost': round(0.002443603, 6),
            },
        ]

        for test in test_sets:
            cost = lambda_execution_cost(
                memory=test['memory'],
                duration=test['duration'],
            )

            self.assertEqual(cost, test['expected_cost'])


class TestBenchmark(unittest.TestCase):
    '''Test Benchmark class methods'''

    def setUp(self):
        self.params = {
            'verbose': False,
            'ignore_coldstart': True,
            'test_count': c.DEFAULT_TEST_COUNT,
            'max_threads': c.DEFAULT_MAX_THREADS,
            'lambda_function': c.DEFAULT_LAMBDA_FUNCTION,
            'lambda_event': c.DEFAULT_LAMBDA_EVENT,
            'memory_sets': c.DEFAULT_MEMORY_SETS,
            'timeout': c.DEFAULT_LAMBDA_TIMEOUT,
        }

        self.benchmarking = Benchmark(**self.params)  # Use default arguments

    def test_original_config_stringifier(self):
        '''Test stringifier of original Lambda configurations'''
        result_set = self.benchmarking.set_original(memory=1024, timeout=60000)

        self.assertTrue(result_set['memory'])
        self.assertTrue(result_set['timeout'])

        self.assertIsInstance(self.benchmarking.original_config_str, str)

        expected_str = 'memory: 1024, timeout: 60000'
        self.assertEqual(self.benchmarking.original_config_str, expected_str)

    @patch('benchmark.get_lambda_config', new_callable=CustomMock.get_lambda_config)  # NOQA
    @patch('benchmark.logger')
    def test_store_original_config(self, logger, get_lambda_config):
        '''Test storing original Lambda configuration parameters'''
        result = self.benchmarking.store_original_config()

        get_lambda_config.assert_called_with(
            function_name=self.params['lambda_function'],
        )

        self.assertIsNone(result['error'])
        self.assertEqual(
            self.benchmarking.original_config['memory'],
            c.DEFAULT_MEMORY_SETS[0],
        )
        self.assertEqual(
            self.benchmarking.original_config['timeout'],
            self.params['timeout'],
        )

        logger.warning.assert_not_called()
        logger.exception.assert_not_called()

    @patch('benchmark.get_lambda_config', new_callable=CustomMock.get_lambda_config_fail)  # NOQA
    @patch('benchmark.logger')
    def test_store_original_config_fail(self, logger, get_lambda_config):
        '''Test storing original configuration when get_lambda_config fails'''
        result = self.benchmarking.store_original_config()

        self.assertIsNotNone(result['error'])
        self.assertIsNone(result['memory'])
        self.assertIsNone(result['timeout'])

        logger.warning.assert_called()
        logger.exception.assert_called()

    @patch('benchmark.update_lambda_config', new_callable=CustomMock.update_lambda_config)  # NOQA
    @patch('benchmark.logger')
    def test_restore_original_config(self, logger, update_lambda_config):
        '''Test restoring original Lambda configurations'''
        memory = 512
        timeout = 3000

        result = self.benchmarking.restore_original_config(
            original_config={
                'memory': memory,
                'timeout': timeout,
            }
        )

        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

        update_lambda_config.assert_called_with(
            function_name=self.params['lambda_function'],
            memory_size=memory,
            timeout=timeout,
        )

        logger.warning.assert_not_called()
        logger.exception.assert_not_called()

    @patch('benchmark.update_lambda_config', new_callable=CustomMock.update_lambda_config_fail)  # NOQA
    @patch('benchmark.logger')
    def test_restore_original_config_fail(self, logger, update_lambda_config):
        '''Test restoring original Lambda config when Lambda API fails'''
        memory = 512
        timeout = 3000

        result = self.benchmarking.restore_original_config(
            original_config={
                'memory': memory,
                'timeout': timeout,
            }
        )

        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])

        logger.warning.assert_called()
        logger.exception.assert_called()

    @patch('benchmark.update_lambda_config', new_callable=CustomMock.update_lambda_config)  # NOQA
    @patch('benchmark.logger')
    def test_set_new_memory(self, logger, update_lambda_config):
        '''Test setting new memory size to Lambda function'''
        test_memory_size = 512

        response, success, error = self.benchmarking.set_new_config(
            new_memory=test_memory_size,
            new_timeout=self.params['timeout'],
        )

        update_lambda_config.assert_called_with(
            function_name=self.params['lambda_function'],
            memory_size=test_memory_size,
            timeout=self.params['timeout'],
        )

        self.assertIsInstance(response, dict)
        self.assertIn('foo', response)
        self.assertEqual(response['foo'], 'bar')
        self.assertTrue(success)
        self.assertIsNone(error)

        logger.assert_not_called()

    @patch('benchmark.update_lambda_config', new_callable=CustomMock.update_lambda_config_fail)  # NOQA
    @patch('benchmark.logger')
    def test_set_new_memory_fail(self, logger, update_lambda_config):
        '''Test setting new memory size when Lambda API fails'''
        test_memory_size = 512

        response, success, error = self.benchmarking.set_new_config(
            new_memory=test_memory_size,
            new_timeout=self.params['timeout'],
        )

        self.assertIsNone(response)
        self.assertFalse(success)
        self.assertIsNotNone(error)
        self.assertIsInstance(error, custom_exc.SetLambdaMemoryError)

        logger.warning.assert_called_with(error)
        logger.exception.assert_called()

    def test_check_lambda_response(self):
        '''Test code that checks whether a Lambda request was successful'''
        check_success = self.benchmarking.is_lambda_response_success(
            operation='',
            response={
                'StatusCode': 200,
            },
        )

        check_fail = self.benchmarking.is_lambda_response_success(
            operation='',
            response={
                'StatusCode': 500,
            },
        )

        self.assertTrue(check_success)
        self.assertFalse(check_fail)

    @patch('benchmark.invoke_lambda', new_callable=CustomMock.invoke_lambda_cold_start)  # NOQA
    @patch('benchmark.logger')
    def test_check_execution_time(self, logger, invoke_lambda):
        '''Test invocation of a Lambda function to check execution time'''
        result = self.benchmarking.get_execution_time()

        invoke_lambda.assert_called_with(
            function_name=self.params['lambda_function'],
            payload=self.params['lambda_event'],
            invocation_type='RequestResponse',
            log_type='None',
        )

        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])
        self.assertEqual(result['duration'], c.DEFAULT_LAMBDA_TIMEOUT - TEST_REMAINING_TIME)  # NOQA
        self.assertEqual(result['cold_start'], COLD_START_TRUE)

        logger.warning.assert_not_called()

    @patch('benchmark.invoke_lambda', new_callable=CustomMock.invoke_lambda_fail)  # NOQA
    @patch('benchmark.logger')
    def test_check_execution_fail(self, logger, invoke_lambda):
        '''Test checking execution time when an exception is raised'''
        response = self.benchmarking.get_execution_time()

        self.assertFalse(response['success'])
        self.assertIsNone(response['duration'])
        self.assertIsInstance(response['error'], str)
        self.assertIn('KeyError', response['error'])

        logger.warning.assert_called()
        logger.exception.assert_called()

    @patch('benchmark.invoke_lambda', new_callable=CustomMock.invoke_lambda_payload_error)  # NOQA
    @patch('benchmark.logger')
    def test_check_execution_payload_error(self, logger, invoke_lambda):
        '''Test checking execution time when payload contains an error'''
        response = self.benchmarking.get_execution_time()

        self.assertFalse(response['success'])
        self.assertIsNone(response['duration'])
        self.assertIsInstance(response['error'], str)
        self.assertEqual(response['error'], 'Error in Lambda response Payload (type is not a Dict)')  # NOQA

        logger.warning.assert_called()

    @patch('benchmark.invoke_lambda', new_callable=CustomMock.invoke_lambda_miss_remaining_time)  # NOQA
    @patch('benchmark.logger')
    def test_check_execution_miss_remaining_time(self, logger, invoke_lambda):
        '''Test checking execution time without remaining time in Payload'''
        response = self.benchmarking.get_execution_time()

        self.assertFalse(response['success'])
        self.assertIsNone(response['duration'])
        self.assertIsInstance(response['error'], str)
        self.assertEqual(response['error'], 'No Integer "remaining_time" in Lambda Payload')  # NOQA

        logger.warning.assert_called()

    @patch('benchmark.invoke_lambda', new=CustomMock.invoke_lambda_get_durations)  # NOQA
    def test_get_benchmark_durations(self):
        '''Test running benchmark routine for a given memory size'''
        lambda_states = reset_lambda_states(
            max_threads=self.params['max_threads'],
            test_count=self.params['test_count'],
        )

        remaining_times = reset_lambda_remaining_time(
            invocations=len(lambda_states),
            timeout=self.params['timeout'],
        )

        self.assertTrue(len(lambda_states) == len(remaining_times))

        durations = self.benchmarking.get_benchmark_durations()

        self.assertEqual(len(durations), self.params['test_count'])

        # Check if all durations match remainingtimes provided
        for duration in durations:
            remaining_time = self.params['timeout'] - duration
            self.assertIn(remaining_time, remaining_times)

    @patch('benchmark.logger')
    def test_process_benchmark_results(self, logger):
        '''Test processing of benchmark results'''
        benchmark_results = [
            {
                'memory': 128,
                'success': True,
                'errors': [],
                'average_duration': 900000,
                'durations': [900000, 900000, 900000, 900000, 900000],
            },
            {
                'memory': 512,
                'success': True,
                'errors': [],
                'average_duration': 217850,
                'durations': [185905, 256053, 215803, 260124, 171366],
            },
            {
                'memory': 1024,
                'success': False,
                'errors': [KeyError('foobar')],
                'average_duration': 147595,
                'durations': [36306, 195390, 230686, 66158, 209433],
            },
            {
                'memory': 1025,  # Invalid Lambda memory on purpose
                'success': True,
                'errors': [],
                'average_duration': 147595,
                'durations': [36306, 195390, 230686, 66158, 209433],
            },
            {
                'memory': 1536,
                'success': True,
                'errors': [],
                'average_duration': 190921,
                'durations': [297430, 75243, 100955, 181280, 299699],
            },
            {
                'memory': 3008,
                'success': True,
                'errors': [],
                'average_duration': 9280,
                'durations': [20913, 11826, 9909, 1170, 2581],
            },
        ]

        expected_costs = {
            128: round(0.001872, 6),
            512: round(0.001817, 6),
            1536: round(0.004777, 6),
            3008: round(0.000455, 6),
        }

        results = self.benchmarking.process_benchmark_results(
            results=benchmark_results,
        )

        # Check cost ranking
        self.assertEqual(results['ranking']['cost'][0]['memory'], 3008)
        self.assertEqual(results['ranking']['cost'][1]['memory'], 512)
        self.assertEqual(results['ranking']['cost'][2]['memory'], 128)
        self.assertEqual(results['ranking']['cost'][3]['memory'], 1536)

        # Check speed ranking
        self.assertEqual(results['ranking']['duration'][0]['memory'], 3008)
        self.assertEqual(results['ranking']['duration'][1]['memory'], 1536)
        self.assertEqual(results['ranking']['duration'][2]['memory'], 512)
        self.assertEqual(results['ranking']['duration'][3]['memory'], 128)

        for log in results['logs']:
            if log['memory'] == 1024 or log['memory'] == 1025:
                self.assertFalse(log['success'])
                self.assertTrue(len(log['errors']) > 0)

            else:
                expected_cost = expected_costs[log['memory']]
                self.assertEqual(log['execution_cost'], expected_cost)

        logger.warning.assert_called()
        logger.exception.assert_called()


class TestLambdaHandler(unittest.TestCase):
    '''Test Lambda handler entire cycle'''

    def setUp(self):
        self.params = {
            'verbose': False,
            'ignore_coldstart': True,
            'test_count': c.DEFAULT_TEST_COUNT,
            'max_threads': c.DEFAULT_MAX_THREADS,
            'lambda_function': c.DEFAULT_LAMBDA_FUNCTION,
            'lambda_event': c.DEFAULT_LAMBDA_EVENT,
            'memory_sets': c.DEFAULT_MEMORY_SETS,
            'timeout': c.DEFAULT_LAMBDA_TIMEOUT,
        }

        self.lambda_states = reset_lambda_states(
            max_threads=self.params['max_threads'],
            test_count=self.params['test_count'],
        )

        self.remaining_times = reset_lambda_remaining_time(
            invocations=len(self.lambda_states),
            timeout=self.params['timeout'],
        )

        self.benchmarking = Benchmark(**self.params)  # Use default arguments

    @patch('lambda_function.print_payload')
    def test_invalid_event(self, print_payload):
        '''Test Lambda handler with an invalid event'''
        invalid_event = {'foo': 'bar'}

        response = lambda_handler(event=invalid_event, context={})

        print_payload.assert_has_calls([
            call(payload_type='event', payload_obj=invalid_event),
            call(payload_type='response', payload_obj=response),
        ])

        self.assertEqual(response['status'], 400)
        self.assertEqual(len(response['results']), 0)
        self.assertEqual(len(response['errors']), 1)
        self.assertIn('Invalid event key', response['errors'][0])

    @patch('lambda_function.Benchmark', new_callable=CustomMock.benchmark_fail_regular)  # NOQA
    @patch('lambda_function.logger')
    @patch('lambda_function.print_payload')
    def test_benchmark_fail_regular(self, print_payload, logger, Benchmark):
        '''Test full processing cycle'''
        response = lambda_handler(event=self.params, context={})

        Benchmark.assert_called()

        logger.error.assert_called()
        logger.exception.assert_called()

        self.assertEqual(response['status'], 500)
        self.assertTrue(len(response['results']) == 0)
        self.assertTrue(len(response['errors']) > 0)
        self.assertIn('Sorry there was an internal error', response['errors'])

    @patch('lambda_function.Benchmark', new_callable=CustomMock.benchmark_fail_custom)  # NOQA
    @patch('lambda_function.logger')
    @patch('lambda_function.print_payload')
    def test_benchmark_fail_custom(self, print_payload, logger, Benchmark):
        '''Test full processing cycle'''
        response = lambda_handler(event=self.params, context={})

        Benchmark.assert_called()

        logger.error.assert_not_called()
        logger.exception.assert_not_called()

        self.assertEqual(response['status'], 500)
        self.assertTrue(len(response['results']) == 0)
        self.assertTrue(len(response['errors']) > 0)
        self.assertIn(
            'CustomBenchmarkException: custom_foobar', response['errors'])

    @patch('benchmark.get_lambda_config', new_callable=CustomMock.get_lambda_config)  # NOQA
    @patch('benchmark.update_lambda_config', new_callable=CustomMock.update_lambda_config)  # NOQA
    @patch('benchmark.invoke_lambda', new_callable=CustomMock.invoke_lambda_get_durations)  # NOQA
    @patch('benchmark.logger')
    @patch('lambda_function.logger')
    def test_full_cycle(
            self,
            handler_logger,
            benchmark_logger,
            invoke_lambda,
            update_lambda_config,
            get_lambda_config,
            ):
        '''Test full Lambda handler execution cycle'''
        pass


def reset_lambda_states(*, max_threads: int, test_count: int) -> list:
    global LAMBDA_STATE

    lambda_states = [True for i in range(0, max_threads)] + \
        [False for i in range(0, test_count)]

    LAMBDA_STATE = iter(lambda_states)

    return lambda_states


def reset_lambda_remaining_time(*, invocations: int, timeout: int) -> list:
    '''Reset Lambda remaining times'''
    global LAMBDA_REMAINING_TIME

    remaining_time = [randint(1, timeout) for i in range(0, invocations)]

    LAMBDA_REMAINING_TIME = iter(remaining_time)

    return remaining_time


if __name__ == '__main__':
    unittest.main()
