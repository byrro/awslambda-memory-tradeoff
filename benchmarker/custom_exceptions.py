'''Custom Exception Classes for the Benchmark Lambda App'''


class SetOriginalConfigError(Exception):
    '''Error setting local reference of original Lambda configuration'''
    pass


class GetOriginalConfigError(Exception):
    '''Error getting original Lambda configuration'''
    pass


class RestoreOriginalConfigError(Exception):
    '''Error restoring original Lambda configuration'''
    pass


class SetLambdaMemoryError(Exception):
    '''Error setting new Lambda memory size'''
    pass


class InvokeLambdaError(Exception):
    '''Error Invoking Lambda'''
    pass


class LambdaPayloadError(Exception):
    '''Error on Lambda response payload'''
    pass
