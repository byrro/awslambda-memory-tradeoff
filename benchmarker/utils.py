'''Utility functions for the memory benchmark Lambda'''
import json
import logging
import math
from typing import (
    Dict,
)
import boto3
import constants as c
import custom_exceptions as custom_exc


logger = logging.getLogger()
logger.setLevel(logging.WARNING)


def validate_event(*, event):
    '''Validate Lambda event payload input'''
    error = None

    if type(event) is not dict:
        error = f'Event payload input must be a dict, got {type(event)}'

    elif not all(key in c.VALID_EVENT_ARGS for key in event.keys()):
        error = f"Invalid event key, valid are {', '.join(c.VALID_EVENT_ARGS)}"

    valid = True if error is None else False

    return valid, error


def print_payload(*, payload_type: str, payload_obj: Dict):
    '''Print payload objects for debugging purposes'''
    print(c.PAYLOAD_PRINT_MSG.get(payload_type, f'PAYLOAD {payload_type}:'))
    print(json.dumps(payload_obj))


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

    response = aws_lambda.get_function_configuration(
        FunctionName=function_name,
    )

    return response


def lambda_execution_cost(*, memory: int, duration: int) -> float:
    '''Calculate Lambda execution cost'''
    cost_per_100ms = c.LAMBDA_COST_BY_MEMORY.get(memory)

    if not cost_per_100ms:
        raise custom_exc.CalculateLambdaExecutionCostError(
            f'Cost/100ms not found for memory size ({memory})'
        )

    return round(math.ceil(duration/100) * cost_per_100ms, 6)
