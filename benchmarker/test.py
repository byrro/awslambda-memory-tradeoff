'''Test cases for benchmark Lambda'''
import json
import unittest
from unittest.mock import (
    MagicMock,
    patch,
)
from utils import (
    invoke_lambda,
    update_lambda_config,
)
from benchmark import Benchmark
import constants as c


class CustomMock():
    '''Produces custom Mock objects for tests'''

    @staticmethod
    def invoke_lambda_fail():
        '''Mock invoke_lambda function raising an exception'''
        mock = MagicMock(side_effect=KeyError('foobar'))
        return mock


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

    @patch('utils.boto3')
    def test_check_execution_time(self, boto3):
        '''Test invocation of a Lambda function to check execution time'''
        self.benchmarking.check_execution_time()

        boto3.session.Session.assert_called()

        client = boto3.session.Session().client
        client.assert_called_with('lambda')

        aws_lambda = client()
        aws_lambda.invoke.assert_called_with(
            FunctionName=c.DEFAULT_LAMBDA_FUNCTION,
            InvocationType='RequestResponse',
            LogType='None',
            Payload=json.dumps(c.DEFAULT_LAMBDA_EVENT),
        )

    @patch('utils.boto3')
    def test_set_new_memory(self, boto3):
        '''Test setting of a new memory size to Lambda function'''
        test_memory_size = 512

        self.benchmarking.set_memory(new_memory=test_memory_size)

        boto3.session.Session.assert_called()

        client = boto3.session.Session().client
        client.assert_called_with('lambda')

        aws_lambda = client()
        aws_lambda.update_function_configuration.assert_called_with(
            FunctionName=c.DEFAULT_LAMBDA_FUNCTION,
            MemorySize=test_memory_size,
            Timeout=c.DEFAULT_LAMBDA_TIMEOUT,
        )

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

    @patch('benchmark.invoke_lambda', new_callable=CustomMock.invoke_lambda_fail)  # NOQA
    def test_check_execution_fail(self, invoke_lambda):
        '''Test checking execution time when an exception is raised'''
        response = self.benchmarking.check_execution_time()

        self.assertFalse(response['success'])
        self.assertIsInstance(response['error'], str)
        self.assertIsNone(response['duration'])
        self.assertIn('KeyError', response['error'])
        self.assertFalse(response['cold_start'])


if __name__ == '__main__':
    unittest.main()
