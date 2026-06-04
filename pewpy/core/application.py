#   pewpy/core/application.py
#   Main application coordination - uses config, resource manager, and worker factory

# ----- Imports ----- #
import logging
import threading
from typing import Dict, Any, Optional
from .thread_manager import ThreadManager
from .config import Config
from .resource_manager import ResourceManager
from ..utils.platform import get_cpu_count
from ..workers import create_workers

# ----- Main Class ----- #
class PewPyApplication :
    def __init__(self, config: Optional[Config] = None) -> None :
        self.config = config or Config()
        self.running = False
        self.workers: Dict[str, Any] = {}
        self.worker_instances: Dict[str, Any] = {}
        self.thread_manager = ThreadManager()
        self.resource_manager = ResourceManager(self.config.config)
        self._lock = threading.RLock()
        
        # Use the factory to build all workers and the communication bridge
        self.workers, self.overlay_data = create_workers(self.config)
        
        if self.config.get('resource_manager.enabled', True) :
            self.resource_manager.start()
            self._register_resource_callbacks()
        logging.info("PewPyApplication initialized")

    def _register_resource_callbacks(self) -> None :
        def on_resource_update(changes) :
            if 'aimbot' in self.worker_instances:
                aimbot = self.worker_instances['aimbot']
                if hasattr(aimbot, 'capturer') and hasattr(aimbot.capturer, 'update_fps'):
                    if 'target_fps' in changes:
                        aimbot.capturer.update_fps(changes['target_fps'])
        self.resource_manager.register_callback(on_resource_update)
    
    def start_worker(self, worker_name: str) -> bool :
        with self._lock :
            if worker_name not in self.workers :
                logging.error(f"Worker '{worker_name}' not found")
                return False
            if self.thread_manager.is_worker_running(worker_name) :
                logging.warning(f"Worker '{worker_name}' already running")
                return False
            worker = self.workers[worker_name]
            success = self.thread_manager.start_worker(worker_name, worker)
            if success :
                self.worker_instances[worker_name] = worker
                logging.info(f"Worker '{worker_name}' started")
            else :
                logging.error(f"Failed to start worker '{worker_name}'")
            return success
    
    def stop_worker(self, worker_name: str) -> bool :
        with self._lock :
            if worker_name not in self.worker_instances :
                logging.warning(f"Worker '{worker_name}' not active")
                return False
            success = self.thread_manager.stop_worker(worker_name)
            if success :
                self.worker_instances.pop(worker_name, None)
                logging.info(f"Worker '{worker_name}' stopped")
            else :
                logging.warning(f"Worker '{worker_name}' stop failed")
            return success
    
    def is_worker_running(self, worker_name: str) -> bool :
        return self.thread_manager.is_worker_running(worker_name)
    
    def pause_worker(self, worker_name: str) -> bool :
        return self.thread_manager.pause_worker(worker_name)
    
    def resume_worker(self, worker_name: str) -> bool :
        return self.thread_manager.resume_worker(worker_name)
    
    def stop_all(self) -> None :
        with self._lock :
            logging.info("Stopping all workers")
            self.thread_manager.stop_all()
            self.worker_instances.clear()
            self.resource_manager.stop()
            logging.info("All workers stopped")