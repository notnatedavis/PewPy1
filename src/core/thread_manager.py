#   src/core/thread_manager.py
#   threading optimizations (python 3.13+)

# ----- Imports ----- #
from os import name
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
        # start a worker in a separate thread with validation
        with self.lock :
            # check if worker is already running
            if self._is_worker_active(name) :
                logging.warning(f"Worker '{name}' is already running")
                return False
            
            # clean up previous instances
            self._cleanup_worker(name)
                
            # create and start thread
            thread = threading.Thread(
                target=self._worker_wrapper,
                args=(name, worker),
                name=f"Worker-{name}",
                daemon=True
            )
            
            self.workers[name] = thread
            self.worker_instances[name] = worker
            thread.start()
            
            logging.info(f"Started worker: {name}")
            return True
            
    def _worker_wrapper(self, name: str, worker: BaseWorker) -> None :
        # wrapper for worker execution with comprehensive error handling
        try :
            self._validate_worker(worker, name)
            worker.start()
            logging.debug(f"Worker '{name}' completed successfully")
        except Exception as e :
            logging.error(f"Worker '{name}' failed: {e}")
        finally :
            self._safe_cleanup(name, worker)
                
    def stop_worker(self, name: str) -> bool :
        # stop a specific worker with graceful shutdown handling
        with self.lock :
            if not self._worker_exists(name) :
                logging.warning(f"Worker '{name}' not found")
                return False

            worker_instance = self.worker_instances.get(name)
            worker_thread = self.workers.get(name)
            
            logging.debug(f"Stopping worker: {name}")
            
            # Signal worker to stop
            if worker_instance :
                worker_instance.stop()
            
            # Wait for graceful shutdown
            if worker_thread and worker_thread.is_alive():
                worker_thread.join(timeout=1.0)
                if worker_thread.is_alive():
                    # logging.warning(f"Worker '{name}' didn't stop gracefully") # uncomment if needed
                    pass
            
            self._cleanup_worker(name)
            logging.info(f"Stopped worker: {name}")
            return True

    def is_worker_running(self, name: str) -> bool:
        # check if worker thread is currently active
        with self.lock :
            return self._is_worker_active(name)
             
    def stop_all(self) -> None :
        # stop all active workers
        with self.lock :
            for name in list(self.worker_instances.keys()) :
                self.stop_worker(name)

    # ----- Internal Helper Methods ----- #
    
    def _is_worker_active(self, name: str) -> bool :
        # check if worker exists and is alive
        thread = self.workers.get(name)
        return thread is not None and thread.is_alive()
    
    def _worker_exists(self, name: str) -> bool :
        # check if worker is registered
        return name in self.workers or name in self.worker_instances
    
    def _cleanup_worker(self, name: str) -> None :
        # remove worker references safely
        self.workers.pop(name, None)
        self.worker_instances.pop(name, None)
    
    def _validate_worker(self, worker: BaseWorker, name: str) -> None :
        # validate worker before execution
        if not hasattr(worker, 'start') or not callable(worker.start) :
            raise AttributeError(f"Worker '{name}' missing required 'start' method")
    
    def _safe_cleanup(self, name: str, worker: BaseWorker) -> None :
        # clean up worker references with instance verification
        with self.lock :
            current_worker = self.worker_instances.get(name)
            if current_worker is worker :  # prevent cleaning up new instances
                self._cleanup_worker(name)
                logging.debug(f"Worker '{name}' cleaned up")