#   src/workers/function_worker.py
#   Base class for all workers (passive, managed by ThreadManager)

# ----- Imports ----- #
import threading
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

# ----- Main Class ----- #
class WorkerStatus(Enum) :
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class WorkerMetrics :
    start_time: float = 0.0
    total_cycles: int = 0
    error_count: int = 0
    avg_cycle_time: float = 0.0
    last_cycle_time: float = 0.0

class BaseWorker(ABC):
    # Abstract base class for workers. Subclasses must implement _work_cycle()
    
    def __init__(self, name: Optional[str] = None) -> None :
        self.name = name or self.__class__.__name__
        self._metrics = WorkerMetrics()
        self._cycle_times = []
        self._config: Dict[str, Any] = {}
        self._status = WorkerStatus.STOPPED
        logging.debug(f"BaseWorker initialized: {self.name}")
    
    @abstractmethod
    def _work_cycle(self) -> None :
        # One unit of work. Called repeatedly in the worker thread
        pass
    
    def run(self, stop_event: threading.Event, pause_event: threading.Event) -> None :
        # Main run loop, to be called by ThreadManager in a separate thread
        self._status = WorkerStatus.RUNNING
        self._metrics.start_time = time.time()
        logging.info(f"Worker {self.name} started")
        
        try :
            while not stop_event.is_set() :
                # Wait if paused
                pause_event.wait()
                
                cycle_start = time.time()
                try :
                    self._work_cycle()
                    self._metrics.total_cycles += 1
                except Exception as e :
                    logging.error(f"Worker {self.name} cycle error: {e}", exc_info=True)
                    self._metrics.error_count += 1
                    if self._metrics.error_count > 10 :
                        logging.error(f"Worker {self.name} too many errors, exiting")
                        break
                    time.sleep(min(2 ** self._metrics.error_count, 30))
                
                cycle_time = time.time() - cycle_start
                self._metrics.last_cycle_time = cycle_time
                self._cycle_times.append(cycle_time)
                if len(self._cycle_times) > 100 :
                    self._cycle_times.pop(0)
                if self._cycle_times :
                    self._metrics.avg_cycle_time = sum(self._cycle_times) / len(self._cycle_times)
                
                # Prevent CPU spinning if cycle was extremely fast
                if cycle_time < 0.001 :
                    time.sleep(0.001)
        except Exception as e :
            logging.error(f"Worker {self.name} run loop crashed: {e}", exc_info=True)
            self._status = WorkerStatus.ERROR
        finally :
            self._status = WorkerStatus.STOPPED
            logging.info(f"Worker {self.name} stopped")
    
    def get_metrics(self) -> Dict[str, Any] :
        runtime = time.time() - self._metrics.start_time if self._metrics.start_time > 0 else 0
        return {
            'name': self.name,
            'status': self._status.value,
            'running': (self._status == WorkerStatus.RUNNING),
            'runtime_seconds': round(runtime, 2),
            'total_cycles': self._metrics.total_cycles,
            'error_count': self._metrics.error_count,
            'avg_cycle_time_ms': round(self._metrics.avg_cycle_time * 1000, 2),
            'last_cycle_time_ms': round(self._metrics.last_cycle_time * 1000, 2),
            'cycles_per_second': round(self._metrics.total_cycles / runtime, 2) if runtime > 0 else 0
        }
    
    def update_config(self, config: Dict[str, Any]) -> None :
        self._config.update(config)
        logging.debug(f"Worker {self.name} config updated")
    
    def _cleanup(self) -> None :
        # Override for resource cleanup
        pass