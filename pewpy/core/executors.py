#   src/core/executors.py
#   Abstract executor backends for parallel processing

# ----- Imports ----- 
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Callable, Any, Optional

# ----- Main Class ----- 
class ExecutorBackend(ABC) :
    # abstract base for execution backends
    
    @abstractmethod
    def submit(self, fn: Callable, *args, **kwargs) -> Any :
        # submit a callable for execution
        pass
    
    @abstractmethod
    def shutdown(self, wait: bool = True) -> None :
        # shutdown the executor
        pass

class ThreadExecutor(ExecutorBackend) :
    # thread-based executor
    
    def __init__(self, max_workers: Optional[int] = None) :
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="PewPyThread")
        logging.debug(f"ThreadExecutor initialized with max_workers={max_workers}")
        
    def submit(self, fn: Callable, *args, **kwargs) -> Any :
        return self._executor.submit(fn, *args, **kwargs)
    
    def shutdown(self, wait: bool = True) -> None :
        self._executor.shutdown(wait=wait)

class ProcessExecutor(ExecutorBackend) :
    # process-based executor (bypasses GIL)
    
    def __init__(self, max_workers: Optional[int] = None) :
        self._executor = ProcessPoolExecutor(max_workers=max_workers)
        logging.debug(f"ProcessExecutor initialized with max_workers={max_workers}")
        
    def submit(self, fn: Callable, *args, **kwargs) -> Any :
        return self._executor.submit(fn, *args, **kwargs)
    
    def shutdown(self, wait: bool = True) -> None :
        self._executor.shutdown(wait=wait)