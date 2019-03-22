'''Custom Exception Classes for the Benchmark Lambda App'''


class SetLambdaMemoryError(Exception):
    '''Error setting new Lambda memory size'''
    pass


class InvokeLambdaError(Exception):
    '''Error Invoking Lambda'''
    pass


class LambdaPayloadError(Exception):
    '''Error on Lambda response payload'''
    pass
