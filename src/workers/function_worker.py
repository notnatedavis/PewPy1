#   src/workers/function_worker.py
#   base class for all toggleable function workers

# ----- Imports ----- #
import threading
import time
from abc import ABC, abstractmethod

# ----- Main Class Application ----- #
class BaseWorker(ABC) :
     # abstract base class for all function workers

    def __init__(self) :
        self.running = False
        self.thread = None
        
    @abstractmethod
    def _work(self) :
        # Main work method to be implemented by subclasses
        pass
        
    def start(self) :
        # Start the worker
        self.running = True
        self._work()
        
    def stop(self) :
        # Stop the worker
        self.running = False
        
    def is_running(self) -> bool :
        # Check if worker is running
        return self.running