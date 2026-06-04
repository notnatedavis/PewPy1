#   src/core/thread_manager.py
#   Manages worker threads (passive workers) with events for stop/pause.

# ----- Imports ----- #
import threading
import logging
import time
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from pewpy.common.constants import WorkerState

# ----- Main Class ----- #
@dataclass
class WorkerInfo :
    thread: threading.Thread
    instance: Any
    state: WorkerState
    start_time: float
    stop_event: threading.Event
    pause_event: threading.Event
    error_count: int = 0

class ThreadManager :
    # Manages worker threads with stop/pause events
    
    def __init__(self) -> None :
        self.workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()
        self._monitor_thread = None
        self._running = True
        self._start_monitor()
        
    def _start_monitor(self) -> None :
        self._monitor_thread = threading.Thread(target=self._monitor_workers, name="ThreadMonitor", daemon=True)
        self._monitor_thread.start()
        logging.debug("Worker monitor thread started")
    
    def _monitor_workers(self) -> None :
        while self._running :
            try :
                with self._lock :
                    for name, info in list(self.workers.items()) :
                        if not info.thread.is_alive() and info.state == WorkerState.RUNNING :
                            logging.warning(f"Worker '{name}' thread died unexpectedly")
                            info.state = WorkerState.ERROR
                            if info.error_count < 3 :
                                logging.info(f"Attempting to restart worker '{name}'")
                                self._restart_worker(name, info)
                            else :
                                self._cleanup_worker(name)
                        elif info.state == WorkerState.RUNNING and (time.time() - info.start_time) > 3600 :
                            logging.info(f"Worker '{name}' has been running for 1+ hours")
                time.sleep(2)
            except Exception as e :
                logging.error(f"Monitor thread error: {e}")
                time.sleep(5)
    
    def _restart_worker(self, name: str, info: WorkerInfo) -> None :
        try :
            # Create new events
            stop_event = threading.Event()
            pause_event = threading.Event()
            pause_event.set()  # start unpaused
            
            # Create new thread
            thread = threading.Thread(
                target=self._worker_wrapper,
                args=(name, info.instance, stop_event, pause_event),
                name=f"Worker-{name}",
                daemon=True
            )
            
            # Update info
            info.thread = thread
            info.stop_event = stop_event
            info.pause_event = pause_event
            info.state = WorkerState.STARTING
            info.start_time = time.time()
            info.error_count += 1
            
            thread.start()
            info.state = WorkerState.RUNNING
            logging.info(f"Worker '{name}' restarted")
        except Exception as e :
            logging.error(f"Failed to restart worker '{name}': {e}")
            info.state = WorkerState.ERROR
    
    def start_worker(self, name: str, worker_instance: Any) -> bool :
        with self._lock :
            if name in self.workers :
                info = self.workers[name]
                if info.thread.is_alive() :
                    logging.warning(f"Worker '{name}' already running")
                    return False
                else :
                    self._cleanup_worker(name)
            
            if not self._validate_worker(worker_instance) :
                logging.error(f"Invalid worker instance for '{name}'")
                return False
            
            stop_event = threading.Event()
            pause_event = threading.Event()
            pause_event.set()  # start unpaused
            
            thread = threading.Thread(
                target=self._worker_wrapper,
                args=(name, worker_instance, stop_event, pause_event),
                name=f"Worker-{name}",
                daemon=True
            )
            
            self.workers[name] = WorkerInfo(
                thread=thread,
                instance=worker_instance,
                state=WorkerState.STARTING,
                start_time=time.time(),
                stop_event=stop_event,
                pause_event=pause_event
            )
            
            thread.start()
            self.workers[name].state = WorkerState.RUNNING
            logging.info(f"Started worker: {name} (Thread: {thread.native_id})")
            return True
    
    def _worker_wrapper(self, name: str, worker: Any, stop_event: threading.Event, pause_event: threading.Event) -> None :
        worker_info = self.workers.get(name)
        if worker_info :
            worker_info.state = WorkerState.RUNNING
        
        try :
            # Worker must have a run method accepting stop_event and pause_event
            if hasattr(worker, 'run') and callable(worker.run):
                worker.run(stop_event, pause_event)
            else :
                raise AttributeError(f"Worker '{name}' missing required 'run(stop_event, pause_event)' method")
        except Exception as e :
            logging.error(f"Worker '{name}' crashed: {e}", exc_info=True)
            if worker_info:
                worker_info.state = WorkerState.ERROR
                worker_info.error_count += 1
        finally :
            # Ensure cleanup
            if hasattr(worker, '_cleanup') :
                try :
                    worker._cleanup()
                except Exception as e :
                    logging.debug(f"Worker cleanup error '{name}': {e}")
            if worker_info :
                worker_info.state = WorkerState.STOPPED
    
    def stop_worker(self, name: str, timeout: float = 2.0) -> bool :
        with self._lock :
            if name not in self.workers :
                logging.warning(f"Worker '{name}' not found")
                return False
            info = self.workers[name]
            if info.state == WorkerState.STOPPED :
                return True
            
            logging.info(f"Stopping worker: {name}")
            info.state = WorkerState.STOPPING
            info.stop_event.set()
            info.pause_event.set()  # unpause to allow exit
            
            if info.thread.is_alive() :
                info.thread.join(timeout=timeout)
                if info.thread.is_alive() :
                    logging.warning(f"Worker '{name}' didn't stop gracefully within {timeout}s")
            
            info.state = WorkerState.STOPPED
            self._cleanup_worker(name)
            logging.info(f"Worker '{name}' stopped")
            return True
    
    def stop_all(self, timeout: float = 5.0) -> None :
        with self._lock :
            logging.info(f"Stopping all workers (timeout={timeout}s)")
            self._running = False
            for name in list(self.workers.keys()) :
                self.stop_worker(name, timeout=1.0)
            if self._monitor_thread and self._monitor_thread.is_alive() :
                self._monitor_thread.join(timeout=1.0)
            self.workers.clear()
            logging.info("All workers stopped")
    
    def pause_worker(self, name: str) -> bool :
        with self._lock :
            if name not in self.workers :
                return False
            info = self.workers[name]
            if info.state == WorkerState.RUNNING :
                info.pause_event.clear()
                info.state = WorkerState.PAUSED
                logging.debug(f"Worker '{name}' paused")
                return True
            return False
    
    def resume_worker(self, name: str) -> bool :
        with self._lock :
            if name not in self.workers : 
                return False
            info = self.workers[name]
            if info.state == WorkerState.PAUSED :
                info.pause_event.set()
                info.state = WorkerState.RUNNING
                logging.debug(f"Worker '{name}' resumed")
                return True
            return False
    
    def is_worker_running(self, name: str) -> bool :
        with self._lock :
            if name not in self.workers :
                return False
            info = self.workers[name]
            return info.thread.is_alive() and info.state == WorkerState.RUNNING
    
    def get_worker_stats(self) -> Dict[str, Any] :
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
    
    def _validate_worker(self, worker: Any) -> bool :
        if not worker :
            return False
        # Must have run method with two args
        if not hasattr(worker, 'run') or not callable(worker.run) :
            return False
        return True
    
    def _cleanup_worker(self, name: str) -> None : 
        if name in self.workers :
            self.workers.pop(name, None)
    
    def __del__(self) -> None :
        self.stop_all()