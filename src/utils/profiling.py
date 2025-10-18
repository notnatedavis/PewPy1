#   src/utils/profiling.py
#   Performance profiling and benchmarking utilities

# ----- Imports ----- #
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, Any, Optional
from ..core.performance_monitor import PerformanceMonitor

# ----- main Class ----- #
class Profiler :
    # Advanced performance profiler with context manager support

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.profiler = cProfile.Profile()
        self.start_time = None
        self.measurements = {}
    
    def start(self):
        # Start profiling
        if self.enabled:
            self.profiler.enable()
            self.start_time = time.time()
    
    def stop(self) -> dict:
        # Stop profiling and return results
        if not self.enabled or self.start_time is None:
            return {}
        
        self.profiler.disable()
        end_time = time.time()
        
        # Capture profile stats
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats()
        
        return {
            'total_time': end_time - self.start_time,
            'profile_stats': s.getvalue()
        }
    
    @contextmanager
    def profile_section(self, name: str):
        # Context manager for profiling code sections
        section_start = time.time()
        try:
            yield
        finally:
            section_end = time.time()
            self.measurements[name] = section_end - section_start
    
    def get_measurements(self) -> dict:
        # Get all section measurements
        return self.measurements.copy()

def benchmark(func: Callable) -> Callable :
    # Decorator for benchmarking function execution time
    @functools.wraps(func)
    def wrapper(*args, **kwargs) :
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        print(f"Function {func.__name__} took {end_time - start_time:.6f} seconds")
        return result
    
    return wrapper

@contextmanager
def timer(description: str = "Operation") :
    # Simple context manager for timing code blocks
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        print(f"{description} took {end - start:.6f} seconds")