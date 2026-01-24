#   src/core/app_manager.py
#   Main application coordination - Fixed circular imports

# ----- Imports ----- #
import logging
import threading
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from .thread_manager import ThreadManager

class PewPyApplication :
    # Main application class coordinating all components
    
    def __init__(self) -> None:
        self.running = False
        self.workers: Dict[str, Any] = {}
        self.worker_instances: Dict[str, Any] = {}
        self.thread_manager = ThreadManager()
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="PewPyWorker")
        
        # initialize workers lazily to avoid circular imports
        self._initialize_workers()
        logging.info("PewPyApplication initialized")
        
    def _initialize_workers(self) -> None :
        # initialize all toggleable function workers - lazy imports
        with self._lock :
            try :
                # import workers only when needed
                from src.workers.auto_clicker import AutoClicker
                from src.workers.overlay import Overlay
                
                self.workers['auto_clicker'] = AutoClicker(click_interval=0.1)
                logging.debug("AutoClicker worker initialized")
                
                self.workers['overlay'] = Overlay(position=(0, 0), size=(300, 200))
                logging.debug("Overlay worker initialized")
                
                # note: AimbotWorker requires additional configuration
                # Uncomment and configure when needed
                # from src.workers.aimbot import AimbotWorker
                # self.workers['aimbot'] = AimbotWorker(...)
                
            except ImportError as e :
                logging.error(f"Failed to import worker: {e}")
                raise
            except Exception as e :
                logging.error(f"Worker initialization failed: {e}")
                raise
    
    def start_worker(self, worker_name: str) -> bool :
        # start a specific worker
        with self._lock :
            if worker_name not in self.workers :
                logging.error(f"Worker '{worker_name}' not found")
                return False
            
            if self.thread_manager.is_worker_running(worker_name) :
                logging.warning(f"Worker '{worker_name}' is already running")
                return False
            
            worker = self.workers[worker_name]
            success = self.thread_manager.start_worker(worker_name, worker)
            
            if success :
                self.worker_instances[worker_name] = worker
                logging.info(f"Worker '{worker_name}' started successfully")
            else :
                logging.error(f"Failed to start worker '{worker_name}'")
            
            return success
    
    def stop_worker(self, worker_name: str) -> bool :
        # stop a specific worker
        with self._lock :
            if worker_name not in self.worker_instances :
                logging.warning(f"Worker '{worker_name}' not found in active instances")
                return False
            
            success = self.thread_manager.stop_worker(worker_name)
            
            if success :
                self.worker_instances.pop(worker_name, None)
                logging.info(f"Worker '{worker_name}' stopped successfully")
            else :
                logging.warning(f"Worker '{worker_name}' failed to stop gracefully")
            
            return success
    
    def is_worker_running(self, worker_name: str) -> bool :
        # check if worker is running
        return self.thread_manager.is_worker_running(worker_name)
    
    def stop_all(self) -> None :
        # stop all workers and cleanup
        with self._lock :
            logging.info("Initiating shutdown of all workers")
            self.thread_manager.stop_all()
            self.worker_instances.clear()
            self._executor.shutdown(wait=True, cancel_futures=True)
            logging.info("All workers stopped")