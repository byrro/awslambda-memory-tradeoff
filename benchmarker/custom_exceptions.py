'''Custom Exception Classes for the Benchmark Lambda App'''


class CustomBenchmarkException(Exception):
    '''Custom exception handlers'''
    pass


class SetOriginalConfigError(CustomBenchmarkException):
    '''Error setting local reference of original Lambda configuration'''
    pass


class GetOriginalConfigError(CustomBenchmarkException):
    '''Error getting original Lambda configuration'''
    pass


class StoreOriginalConfigError(CustomBenchmarkException):
    '''Error locally storing original Lambda configuration'''
    pass


class RestoreOriginalConfigError(CustomBenchmarkException):
    '''Error restoring original Lambda configuration'''
    pass


class SetLambdaMemoryError(CustomBenchmarkException):
    '''Error setting new Lambda memory size'''
    pass


class InvokeLambdaError(CustomBenchmarkException):
    '''Error Invoking Lambda'''
    pass


class LambdaPayloadError(CustomBenchmarkException):
    '''Error on Lambda response payload'''
    pass


class CalculateLambdaExecutionCostError(CustomBenchmarkException):
    '''Error on Lambda cost calculation'''
    pass
