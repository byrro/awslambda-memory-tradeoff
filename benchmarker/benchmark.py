'''Routine to benchmark Lambda performance with different memory allocations'''
from typing import (
    Dict,
    List
)
import boto3
import constants as c


class Benchmark():
    '''Routine to benchmark Lambda with different memory allocations'''

    def __init__(
            self,
            *,
            ignore_coldstart: bool = c.IGNORE_COLDSTART,
            test_count: int = c.DEFAULT_TEST_COUNT,
            max_threads: int = c.DEFAULT_MAX_THREADS,
            lambda_function: str = c.DEFAULT_LAMBDA_FUNCTION,
            lambda_event: Dict = c.DEFAULT_LAMBDA_EVENT,
            memory_sets: List[int] = c.DEFAULT_MEMORY_SETS,
            boto3=boto3,
            **kwargs,
            ):
        self.ignore_coldstart = ignore_coldstart
        self.test_count = test_count
        self.max_threads = max_threads
        self.lambda_function = lambda_function
        self.lambda_event = lambda_event
        self.memory_sets = memory_sets

        self.boto3 = boto3

        self.results = {
            'average': {memory: 0 for memory in self.memory_sets},
            'details': {memory: [] for memory in self.memory_sets},
        }

    def run(self) -> Dict[str, Dict]:
        '''Run benchmarking routine'''
        pass

    def benchmark_memory(self, memory: int) -> Dict:
        '''Benchmark a given memory size'''
        pass

    def set_memory(self, new_memory) -> bool:
        '''Set new memory for the Lambda'''
        pass

    def check_execution_time(self) -> Dict:
        '''Invoke the Lambda function and check execution time'''
        pass


if __name__ == '__main__':
    pass
