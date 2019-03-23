'''Test cases for benchmark Lambda'''
import json
import unittest
from unittest.mock import (
    MagicMock,
    patch,
)
from benchmark import Benchmark
import constants as c
import custom_exceptions as custom_exc
from utils import (
    invoke_lambda,
    update_lambda_config,
)


TEST_REMAINING_TIME = 1000
COLD_START_TRUE = True


class CustomMock():
    '''Produces custom Mock objects for tests'''

    @staticmethod
    def set_new_memory():
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


class TestLambdaUtils(unittest.TestCase):
    '''Test utility functions'''

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


class TestBenchmark(unittest.TestCase):
    '''Test Benchmark class methods'''

    def setUp(self):
        self.benchmarking = Benchmark()  # Use default arguments

    def test_original_config_stringifier(self):
        '''Test stringifier of original Lambda configurations'''
        result_set = self.benchmarking.set_original(memory=1024, timeout=60000)

        self.assertTrue(result_set['memory'])
        self.assertTrue(result_set['timeout'])

        self.assertIsInstance(self.benchmarking.original_config_str, str)

        expected_str = 'memory: 1024, timeout: 60000'
        self.assertEqual(self.benchmarking.original_config_str, expected_str)

    @patch('benchmark.update_lambda_config', new_callable=CustomMock.set_new_memory)  # NOQA
    @patch('benchmark.logger')
    def test_set_new_memory(self, logger, update_lambda_config):
        '''Test setting new memory size to Lambda function'''
        test_memory_size = 512

        response, success, error = self.benchmarking.set_memory(
            new_memory=test_memory_size,
        )

        update_lambda_config.assert_called_with(
            function_name=c.DEFAULT_LAMBDA_FUNCTION,
            memory_size=test_memory_size,
            timeout=c.DEFAULT_LAMBDA_TIMEOUT,
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

        response, success, error = self.benchmarking.set_memory(
            new_memory=test_memory_size,
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
        result = self.benchmarking.check_execution_time()

        invoke_lambda.assert_called_with(
            function_name=c.DEFAULT_LAMBDA_FUNCTION,
            payload=c.DEFAULT_LAMBDA_EVENT,
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
        response = self.benchmarking.check_execution_time()

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
        response = self.benchmarking.check_execution_time()

        self.assertFalse(response['success'])
        self.assertIsNone(response['duration'])
        self.assertIsInstance(response['error'], str)
        self.assertEqual(response['error'], 'Error in Lambda response Payload (type is not a Dict)')  # NOQA

        logger.warning.assert_called()

    @patch('benchmark.invoke_lambda', new_callable=CustomMock.invoke_lambda_miss_remaining_time)  # NOQA
    @patch('benchmark.logger')
    def test_check_execution_miss_remaining_time(self, logger, invoke_lambda):
        '''Test checking execution time without remaining time in Payload'''
        response = self.benchmarking.check_execution_time()

        self.assertFalse(response['success'])
        self.assertIsNone(response['duration'])
        self.assertIsInstance(response['error'], str)
        self.assertEqual(response['error'], 'No Integer "remaining_time" in Lambda Payload')  # NOQA

        logger.warning.assert_called()


if __name__ == '__main__':
    unittest.main()
