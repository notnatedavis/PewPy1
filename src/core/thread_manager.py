#   src/core/thread_manager.py
#   threading optimizations (python 3.13+)

# ----- Imports ----- #
import threading
import logging
import time
from typing import Dict, Optional
from workers.function_worker import BaseWorker

# ----- Main Class Application ----- #
class ThreadManager :
    # manages worker threads with Python 3.13 optimizations

    def __init__(self) :
        self.workers: Dict[str, threading.Thread] = {}
        self.worker_instances: Dict[str, BaseWorker] = {}
        self.lock = threading.RLock()
        
    def start_worker(self, name: str, worker: BaseWorker) -> bool :
        # Start a worker in a separate thread
        with self.lock :
            if name in self.workers and self.workers[name].is_alive():
                logging.warning(f"Worker {name} is already running")
                return False
            
            # Clean up any previous instance
            self.workers.pop(name, None)
            self.worker_instances.pop(name, None)
                
            # Create and start thread
            thread = threading.Thread(
                target=self._worker_wrapper,
                args=(name, worker),
                name=f"Worker-{name}",
                daemon=True  # Python 3.13+ daemon improvements
            )
            
            self.workers[name] = thread
            self.worker_instances[name] = worker
            
            thread.start()
            logging.info(f"Started worker: {name}")
            return True
            
    def _worker_wrapper(self, name: str, worker: BaseWorker) :
        # Wrapper to handle worker execution and cleanup
        try :
            worker.start()
        except Exception as e :
            logging.error(f"Worker {name} error: {e}")
        finally :
            with self.lock :
                if name in self.workers :
                    self.workers.pop(name, None)
                if name in self.worker_instances :
                    self.worker_instances.pop(name, None)
                
    def stop_worker(self, name: str) -> bool :
        # Stop a specific worker
        with self.lock :
            worker_instance = self.worker_instances.get(name)
            worker_thread = self.workers.get(name)
            
            if worker_instance:
                worker_instance.stop()
                
            if worker_thread and worker_thread.is_alive():
                worker_thread.join(timeout=2.0)
                if worker_thread.is_alive():
                    logging.warning(f"Worker {name} didn't stop gracefully")
                
            self.workers.pop(name, None)
            self.worker_instances.pop(name, None)
            logging.info(f"Stopped worker: {name}")

            return True
        
    def is_worker_running(self, name: str) -> bool :
        # Check if worker is running
        with self.lock :
            thread = self.workers.get(name)
            return thread is not None and thread.is_alive()
             
    def stop_all(self) :
        # Stop all workers
        with self.lock :
            for name in list(self.worker_instances.keys()) :
                self.stop_worker(name)