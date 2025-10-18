#   src/core/app_manager.py
#   main application coordination

# ----- Imports ----- #
import logging
import threading
from typing import Dict, Any
from workers.auto_clicker import AutoClicker
from core.thread_manager import ThreadManager

# ----- Main Class Application ----- #
class PewPyApplication :
    # main application class coordinating all components
    
    def __init__(self) :
        self.running = False
        self.workers = {}
        self.thread_manager = ThreadManager()
        
        # Initialize workers
        self._initialize_workers()
        
    def _initialize_workers(self) :
        # Initialize all toggleable function workers
        self.workers['auto_clicker'] = AutoClicker()
        # Add more workers here as needed
        
    def start_worker(self, worker_name: str) -> bool :
        # start a specific worker
        if worker_name in self.workers :
            worker = self.workers[worker_name]
            return self.thread_manager.start_worker(worker_name, worker)
        return False
        
    def stop_worker(self, worker_name: str) -> bool :
        # stop a specific worker
        return self.thread_manager.stop_worker(worker_name)
        
    def is_worker_running(self, worker_name: str) -> bool :
        # check if worker is running
        return self.thread_manager.is_worker_running(worker_name)
        
    def stop_all(self) :
        # stop all workers and cleanup
        self.thread_manager.stop_all()
        logging.info("All workers stopped")