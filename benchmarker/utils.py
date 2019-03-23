'''Utility functions for the memory benchmark Lambda'''
import json
import logging
from typing import (
    Dict,
)
import boto3


logger = logging.getLogger()
logger.setLevel(logging.WARNING)


def lambda_client():
    '''Instantiate a thread-safe Lambda client'''
    session = boto3.session.Session()
    return session.client('lambda')


def invoke_lambda(
        *,
        function_name: str,
        payload,
        invocation_type: str,
        log_type: str = 'None',
        ) -> Dict:
    '''Invoke a Lambda function

    :arg function_name: name of the function to invoke
    :arg invocation_type: one of these options:
        'RequestResponse': synchronous call, will wait for Lambda processing
        'Event': asynchronous call, will NOT wait for Lambda processing
        'DryRun': validate param values and user permission
    :arg payload: payload data to submit to the Lambda function
    :arg log_type: one of these options:
        'None': does not include execution logs in the response
        'Tail': includes execution logs in the response
    '''
    aws_lambda = lambda_client()

    response = aws_lambda.invoke(
        FunctionName=function_name,
        InvocationType=invocation_type,
        LogType=log_type,
        Payload=json.dumps(payload),
    )

    # Decode response payload
    try:
        payload = response['Payload'].read(amt=None).decode('utf-8')
        response['Payload'] = json.loads(payload)

    except (TypeError, json.decoder.JSONDecodeError):
        logger.warning('Unable to parse Lambda Payload JSON response.')
        response['Payload'] = None

    return response


def update_lambda_config(*, function_name: str, **kwargs) -> Dict:
    aws_lambda = lambda_client()

    config_args = {
        'FunctionName': function_name,
    }

    if 'timeout' in kwargs:
        config_args['Timeout'] = kwargs['timeout']

    if 'memory_size' in kwargs:
        config_args['MemorySize'] = kwargs['memory_size']

    response = aws_lambda.update_function_configuration(**config_args)

    return response


def get_lambda_config(*, function_name):
    '''Get current configuration parameters for a given Lambda function'''
    aws_lambda = lambda_client()

    
