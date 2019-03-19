'''Test cases for benchmark Lambda'''
import json
import unittest
from unittest.mock import patch
from utils import (
    invoke_lambda,
    update_lambda_config,
)
import constants as c


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
    def TestInvokeLambda(self, boto3):
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


if __name__ == '__main__':
    unittest.main()
