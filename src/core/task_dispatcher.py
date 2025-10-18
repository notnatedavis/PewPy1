#   src/core/task_dispatcher.py
#   adaptive work management

# ----- Imports ----- #
import multiprocessing as mp
import threading
import queue
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import psutil
from typing import Callable, Any

# ----- main Class ----- #
class ResourceMonitor:
    """Simple resource monitor for task dispatcher"""
    
    def __init__(self):
        self.cpu_threshold = 80  # Percentage
    
    def should_use_threads(self) -> bool:
        """Determine if threads should be used based on CPU usage"""
        current_cpu = psutil.cpu_percent(interval=0.1)
        return current_cpu > self.cpu_threshold

class AdaptiveTaskDispatcher :
    # dynamically assigns tasks to thread or processes based on :
    # -  CPU/GPU utilization
    # - Task type (I/O vs CPU bound)
    # - System resource availability
    # - Python 3.13 GIL optimization awareness

    def __init__(self) :
        self.cpu_executor = ProcessPoolExecutor(max_workers=mp.cpu_count())
        self.io_executor = ThreadPoolExecutor(max_workers=10)
        self.resource_monitor = ResourceMonitor()
        self.task_queue = queue.Queue()
        self.adaptive_thread = threading.Thread(target=self._adaptive_dispatcher)
        self.adaptive_thread.daemon = True
        self.adaptive_thread.start()

    def submit_task(self, task_type: str, task_fn: Callable, *args, **kwargs) : 
        # submit task with automatic resource-aware routing
        future = mp.Manager().Future()
        self.task_queue.put((future, task_type, task_fn, args, kwargs))
        return future
    
    def _adaptive_dispatcher(self) :
        while True :
            future, task_type, task_fn, args, kwargs = self.task_queue.get()
            
            # Resource-aware task routing
            if task_type == "screen_capture" and self.resource_monitor.should_use_threads():
                # I/O bound - use threading with Python 3.13 optimized GIL
                self.io_executor.submit(self._execute_task, future, task_fn, args, kwargs)
            elif task_type == "target_detection":
                # CPU/GPU bound - use multiprocessing
                self.cpu_executor.submit(self._execute_task, future, task_fn, args, kwargs)
            elif task_type == "input_control":
                # Low latency required - direct execution
                self._execute_task(future, task_fn, args, kwargs)