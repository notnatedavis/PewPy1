#   src/core/thread_manager.py
#   Enhanced thread management with Python 3.13+ optimizations

# ----- Imports ----- #
import threading
import logging
import time
import queue
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

# ----- Main Classes ----- #
class WorkerState(Enum) :
    # Worker thread states
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class WorkerInfo :
    # Information about a worker thread
    thread: threading.Thread
    instance: Any
    state: WorkerState
    start_time: float
    error_count: int = 0

class ThreadManager :
    # Manages worker threads with enhanced monitoring and error handling
    
    def __init__(self) -> None :
        self.workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()
        self._message_queue = queue.Queue(maxsize=100)
        self._monitor_thread = None
        self._running = True
        
        # Start monitor thread
        self._start_monitor()
        
    def _start_monitor(self) -> None :
        # Start background thread to monitor worker health
        self._monitor_thread = threading.Thread(
            target=self._monitor_workers,
            name="ThreadMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        logging.debug("Worker monitor thread started")
    
    def _monitor_workers(self) -> None :
        # Monitor worker threads for health and errors
        while self._running :
            try :
                with self._lock :
                    workers_to_remove = []
                    
                    for name, info in list(self.workers.items()) :
                        # Check thread health
                        if not info.thread.is_alive() and info.state == WorkerState.RUNNING :
                            logging.warning(f"Worker '{name}' thread died unexpectedly")
                            info.state = WorkerState.ERROR
                            
                            # Attempt restart for transient errors
                            if info.error_count < 3 :
                                logging.info(f"Attempting to restart worker '{name}'")
                                self._restart_worker(name, info)
                            else :
                                workers_to_remove.append(name)
                        
                        # Check for long-running threads (potential hangs)
                        elif (info.state == WorkerState.RUNNING and time.time() - info.start_time > 3600) :  # 1 hour
                            logging.info(f"Worker '{name}' has been running for 1+ hours")
                
                # Remove dead workers
                for name in workers_to_remove :
                    self._cleanup_worker(name)
                    logging.error(f"Removed worker '{name}' after multiple failures")
                
                time.sleep(2.0)  # Check every 2 seconds
                
            except Exception as e :
                logging.error(f"Monitor thread error: {e}")
                time.sleep(5.0)
    
    def _restart_worker(self, name: str, info: WorkerInfo) -> None :
        # Restart a failed worker
        try :
            # Cleanup old instance
            if hasattr(info.instance, 'stop') :
                info.instance.stop()
            
            # Create new thread
            new_thread = threading.Thread(
                target=self._worker_wrapper,
                args=(name, info.instance),
                name=f"Worker-{name}",
                daemon=True
            )
            
            # Update worker info
            info.thread = new_thread
            info.state = WorkerState.STARTING
            info.start_time = time.time()
            info.error_count += 1
            
            # Start new thread
            new_thread.start()
            info.state = WorkerState.RUNNING
            
            logging.info(f"Worker '{name}' restarted successfully")
            
        except Exception as e :
            logging.error(f"Failed to restart worker '{name}': {e}")
            info.state = WorkerState.ERROR
    
    def start_worker(self, name: str, worker_instance: Any) -> bool :
        # Start a worker in a separate thread with enhanced validation
        with self._lock :
            # Check if worker already exists and is running
            if name in self.workers :
                info = self.workers[name]
                if info.thread.is_alive() :
                    logging.warning(f"Worker '{name}' is already running")
                    return False
                else :
                    # Clean up dead worker
                    self._cleanup_worker(name)
            
            # Validate worker instance
            if not self._validate_worker(worker_instance) :
                logging.error(f"Invalid worker instance for '{name}'")
                return False
            
            # Create and start thread
            try :
                thread = threading.Thread(
                    target=self._worker_wrapper,
                    args=(name, worker_instance),
                    name=f"Worker-{name}",
                    daemon=True
                )
                
                # Store worker info
                self.workers[name] = WorkerInfo(
                    thread=thread,
                    instance=worker_instance,
                    state=WorkerState.STARTING,
                    start_time=time.time()
                )
                
                # Start thread
                thread.start()
                self.workers[name].state = WorkerState.RUNNING
                
                logging.info(f"Started worker: {name} (Thread: {thread.native_id})")
                return True
                
            except Exception as e :
                logging.error(f"Failed to start worker '{name}': {e}")
                if name in self.workers :
                    self.workers[name].state = WorkerState.ERROR
                return False
    
    def _worker_wrapper(self, name: str, worker_instance: Any) -> None :
        # Wrapper for worker execution with comprehensive error handling
        worker_info = self.workers.get(name)
        
        if worker_info :
            worker_info.state = WorkerState.RUNNING
        
        try :
            # Execute worker
            if hasattr(worker_instance, 'start') and callable(worker_instance.start) :
                worker_instance.start()
            elif hasattr(worker_instance, 'run') and callable(worker_instance.run) :
                worker_instance.run()
            else :
                raise AttributeError(f"Worker '{name}' missing required execution method")
            
            # Worker completed successfully
            if worker_info :
                worker_info.state = WorkerState.STOPPED
            
        except Exception as e :
            logging.error(f"Worker '{name}' failed: {e}", exc_info=True)
            
            if worker_info :
                worker_info.state = WorkerState.ERROR
                worker_info.error_count += 1
        
        finally :
            # Cleanup worker resources
            self._safe_worker_cleanup(name, worker_instance)
    
    def stop_worker(self, name: str, timeout: float = 2.0) -> bool :
        # Stop a specific worker with graceful shutdown
        with self._lock :
            if name not in self.workers :
                logging.warning(f"Worker '{name}' not found")
                return False
            
            worker_info = self.workers[name]
            
            if worker_info.state == WorkerState.STOPPED :
                logging.debug(f"Worker '{name}' already stopped")
                return True
            
            logging.info(f"Stopping worker: {name}")
            worker_info.state = WorkerState.STOPPING
            
            # Signal worker to stop
            if hasattr(worker_info.instance, 'stop') :
                try :
                    worker_info.instance.stop()
                except Exception as e :
                    logging.error(f"Error stopping worker instance '{name}': {e}")
            
            # Wait for thread to terminate
            if worker_info.thread.is_alive() :
                worker_info.thread.join(timeout=timeout)
                
                if worker_info.thread.is_alive() :
                    logging.warning(f"Worker '{name}' didn't stop gracefully within {timeout}s")
                    # Thread will be cleaned up by monitor
            
            # Update state and cleanup
            worker_info.state = WorkerState.STOPPED
            self._cleanup_worker(name)
            
            logging.info(f"Worker '{name}' stopped")
            return True
    
    def stop_all(self, timeout: float = 5.0) -> None :
        # Stop all active workers with coordinated shutdown
        with self._lock :
            logging.info(f"Stopping all workers (timeout: {timeout}s)")
            self._running = False
            
            # Stop all workers
            for name in list(self.workers.keys()) :
                self.stop_worker(name, timeout=1.0)
            
            # Wait for monitor thread
            if self._monitor_thread and self._monitor_thread.is_alive() :
                self._monitor_thread.join(timeout=1.0)
            
            # Clear all workers
            self.workers.clear()
            
            logging.info("All workers stopped")
    
    def is_worker_running(self, name: str) -> bool :
        # Check if worker thread is currently active
        with self._lock :
            if name not in self.workers :
                return False
            
            worker_info = self.workers[name]
            return (worker_info.thread.is_alive() and worker_info.state == WorkerState.RUNNING)
    
    def get_worker_stats(self) -> Dict[str, Any] :
        # Get statistics about all workers
        with self._lock :
            stats = {
                'total_workers': len(self.workers),
                'running_workers': 0,
                'worker_details': {}
            }
            
            for name, info in self.workers.items() :
                is_alive = info.thread.is_alive()
                runtime = time.time() - info.start_time
                
                stats['worker_details'][name] = {
                    'state': info.state.value,
                    'thread_alive': is_alive,
                    'runtime_seconds': round(runtime, 2),
                    'error_count': info.error_count,
                    'thread_id': info.thread.native_id if hasattr(info.thread, 'native_id') else None
                }
                
                if is_alive and info.state == WorkerState.RUNNING : 
                    stats['running_workers'] += 1
            
            return stats
    
    # ----- Internal Helper Methods ----- #
    
    def _validate_worker(self, worker_instance: Any) -> bool :
        # Validate worker before execution
        if not worker_instance :
            return False
        
        # Check for required methods
        required_methods = ['start', 'stop', 'is_running']
        for method in required_methods :
            if not hasattr(worker_instance, method) or not callable(getattr(worker_instance, method, None)) :
                logging.error(f"Worker missing required method: {method}")
                return False
        
        return True
    
    def _cleanup_worker(self, name: str) -> None :
        # Remove worker references safely
        if name in self.workers :
            # Cleanup worker instance if possible
            worker_info = self.workers[name]
            if hasattr(worker_info.instance, 'cleanup') :
                try :
                    worker_info.instance.cleanup()
                except Exception as e :
                    logging.debug(f"Worker cleanup error for '{name}': {e}")
            
            # Remove from dictionary
            self.workers.pop(name, None)
    
    def _safe_worker_cleanup(self, name: str, worker_instance: Any) -> None :
        # Clean up worker references with instance verification
        with self._lock :
            if name in self.workers :
                current_info = self.workers[name]
                if current_info.instance is worker_instance :  # Prevent cleaning up new instances
                    self._cleanup_worker(name)
                    logging.debug(f"Worker '{name}' cleaned up")
    
    def __del__(self) -> None :
        # Destructor for cleanup
        self.stop_all()