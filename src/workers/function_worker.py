#   src/workers/function_worker.py
#   base class for all toggleable function workers

# ----- Imports ----- #
import threading
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class WorkerStatus(Enum) :
    # Worker status enumeration
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class WorkerMetrics :
    # Worker performance metrics
    start_time: float = 0.0
    total_cycles: int = 0
    error_count: int = 0
    avg_cycle_time: float = 0.0
    last_cycle_time: float = 0.0

class BaseWorker(ABC) :
    # Abstract base class for all function workers with enhanced monitoring
    
    def __init__(self, name: Optional[str] = None) -> None :
        self.name = name or self.__class__.__name__
        self._running = False
        self._status = WorkerStatus.STOPPED
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Start unpaused
        
        # Performance metrics
        self._metrics = WorkerMetrics()
        self._cycle_times = []
        
        # Configuration
        self._config = {}
        
        logging.debug(f"BaseWorker initialized: {self.name}")
    
    @abstractmethod
    def _work_cycle(self) -> None :
        # Main work cycle to be implemented by subclasses
        pass
    
    def start(self) -> None :
        # Start the worker thread
        with self._lock :
            if self._running :
                logging.warning(f"Worker {self.name} is already running")
                return
            
            # Reset stop event
            self._stop_event.clear()
            self._pause_event.set()
            
            # Create and start thread
            self._thread = threading.Thread(
                target=self._run,
                name=f"{self.name}-Worker",
                daemon=True
            )
            
            self._running = True
            self._status = WorkerStatus.STARTING
            self._metrics.start_time = time.time()
            
            self._thread.start()
            self._status = WorkerStatus.RUNNING
            
            logging.info(f"Worker {self.name} started")
    
    def _run(self) -> None :
        # Main worker run loop with enhanced error handling
        logging.debug(f"Worker {self.name} run loop started")
        
        try :
            while not self._stop_event.is_set() :
                # Check if paused
                self._pause_event.wait()
                
                # Execute work cycle with timing
                cycle_start = time.time()
                
                try :
                    self._work_cycle()
                    self._metrics.total_cycles += 1
                    
                except Exception as e :
                    logging.error(f"Worker {self.name} cycle error: {e}", exc_info=True)
                    self._metrics.error_count += 1
                    
                    # Implement exponential backoff for repeated errors
                    if self._metrics.error_count > 10 :
                        logging.error(f"Worker {self.name} has too many errors, stopping")
                        break
                    
                    time.sleep(min(2 ** self._metrics.error_count, 30))  # Cap at 30 seconds
                
                # Calculate cycle time
                cycle_time = time.time() - cycle_start
                self._metrics.last_cycle_time = cycle_time
                self._cycle_times.append(cycle_time)
                
                # Keep only recent 100 samples
                if len(self._cycle_times) > 100 :
                    self._cycle_times.pop(0)
                
                # Calculate average
                if self._cycle_times :
                    self._metrics.avg_cycle_time = sum(self._cycle_times) / len(self._cycle_times)
                
                # Small sleep to prevent CPU spinning
                if cycle_time < 0.001 :  # If cycle was very fast
                    time.sleep(0.001)
        
        except Exception as e :
            logging.error(f"Worker {self.name} run loop crashed: {e}", exc_info=True)
            self._status = WorkerStatus.ERROR
        
        finally :
            self._cleanup()
            self._running = False
            self._status = WorkerStatus.STOPPED
            logging.info(f"Worker {self.name} stopped")
    
    def stop(self) -> None :
        # Stop the worker gracefully
        with self._lock :
            if not self._running :
                logging.debug(f"Worker {self.name} already stopped")
                return
            
            logging.info(f"Stopping worker {self.name}")
            self._status = WorkerStatus.STOPPING
            
            # Signal stop
            self._stop_event.set()
            self._pause_event.set()  # Unpause if paused
            
            # Wait for thread to finish
            if self._thread and self._thread.is_alive() :
                self._thread.join(timeout=5.0)
                
                if self._thread.is_alive() :
                    logging.warning(f"Worker {self.name} thread didn't stop gracefully")
    
    def pause(self) -> None :
        # Pause the worker
        with self._lock :
            if self._running and self._status == WorkerStatus.RUNNING :
                self._pause_event.clear()
                self._status = WorkerStatus.PAUSED
                logging.debug(f"Worker {self.name} paused")
    
    def resume(self) -> None :
        # Resume the worker
        with self._lock :
            if self._running and self._status == WorkerStatus.PAUSED :
                self._pause_event.set()
                self._status = WorkerStatus.RUNNING
                logging.debug(f"Worker {self.name} resumed")
    
    def is_running(self) -> bool :
        # Check if worker is running
        return self._running and self._status == WorkerStatus.RUNNING
    
    def get_status(self) -> WorkerStatus :
        # Get current worker status
        return self._status
    
    def get_metrics(self) -> Dict[str, Any] :
        # Get worker performance metrics
        with self._lock :
            runtime = time.time() - self._metrics.start_time if self._metrics.start_time > 0 else 0
            
            return {
                'name': self.name,
                'status': self._status.value,
                'running': self.is_running(),
                'runtime_seconds': round(runtime, 2),
                'total_cycles': self._metrics.total_cycles,
                'error_count': self._metrics.error_count,
                'avg_cycle_time_ms': round(self._metrics.avg_cycle_time * 1000, 2),
                'last_cycle_time_ms': round(self._metrics.last_cycle_time * 1000, 2),
                'cycles_per_second': round(self._metrics.total_cycles / runtime, 2) if runtime > 0 else 0
            }
    
    def update_config(self, config: Dict[str, Any]) -> None :
        # Update worker configuration
        with self._lock :
            self._config.update(config)
            logging.debug(f"Worker {self.name} config updated")
    
    def _cleanup(self) -> None :
        # Cleanup resources - can be overridden by subclasses
        pass
    
    def __del__(self) -> None :
        # Destructor for cleanup
        self.stop()