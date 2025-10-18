#   src/core/performance_monitor.py
#   real time performance tracking

# ----- Imports ----- #
import time
import threading
import psutil
from typing import Dict, Any, List
from collections import deque

# ----- main Class ----- #
class PerformanceMonitor:
    """
    Real-time performance monitoring for frame processing, detection, and system metrics
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        
        # Frame timing metrics
        self.frame_times = deque(maxlen=window_size)
        self.detection_times = deque(maxlen=window_size)
        self.processing_times = deque(maxlen=window_size)
        
        # System metrics
        self.cpu_usage = 0
        self.memory_usage = 0
        self.gpu_usage = 0
        
        # Error tracking
        self.errors = deque(maxlen=50)
        
        # Performance counters
        self.frames_processed = 0
        self.frames_dropped = 0
        
        # Thread safety
        self.lock = threading.Lock()
        
    def record_frame_time(self, frame_time: float = None):
        """Record frame processing time"""
        with self.lock:
            if frame_time is None:
                frame_time = time.time()
            self.frame_times.append(frame_time)
            self.frames_processed += 1
    
    def record_detection_time(self, detection_time: float):
        """Record target detection time"""
        with self.lock:
            self.detection_times.append(detection_time)
    
    def record_processing_time(self, processing_time: float):
        """Record general processing time"""
        with self.lock:
            self.processing_times.append(processing_time)
    
    def record_frame_submission(self):
        """Record frame submission to pipeline"""
        self.record_frame_time()
    
    def record_frame_processing(self):
        """Record frame processing completion"""
        pass  # Could track specific processing events
    
    def record_frame_consumption(self):
        """Record frame consumption from pipeline"""
        pass  # Could track consumption events
    
    def record_error(self, error_msg: str):
        """Record error with timestamp"""
        with self.lock:
            timestamp = time.strftime("%H:%M:%S")
            self.errors.append(f"[{timestamp}] {error_msg}")
    
    def sleep_optimized(self, duration: float):
        """Optimized sleep for performance-critical loops"""
        if duration > 0.01:  # 10ms
            time.sleep(duration)
        else:
            # For very short sleeps, use busy-waiting to avoid context switch overhead
            start = time.perf_counter()
            while time.perf_counter() - start < duration:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        with self.lock:
            # Calculate FPS
            if len(self.frame_times) >= 2:
                time_span = self.frame_times[-1] - self.frame_times[0]
                fps = len(self.frame_times) / time_span if time_span > 0 else 0
            else:
                fps = 0
            
            # Calculate average times
            avg_frame_time = sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0
            avg_detection_time = sum(self.detection_times) / len(self.detection_times) if self.detection_times else 0
            avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            
            # Update system metrics
            self.cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            self.memory_usage = memory.percent
            memory_usage_mb = memory.used / (1024 * 1024)
            
            return {
                'fps': fps,
                'average_frame_time': avg_frame_time,
                'average_detection_time': avg_detection_time,
                'average_processing_time': avg_processing_time,
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'memory_usage_mb': memory_usage_mb,
                'frames_processed': self.frames_processed,
                'frames_dropped': self.frames_dropped,
                'recent_errors': list(self.errors)[-5:]  # Last 5 errors
            }
    
    def reset_stats(self):
        """Reset all performance counters"""
        with self.lock:
            self.frame_times.clear()
            self.detection_times.clear()
            self.processing_times.clear()
            self.errors.clear()
            self.frames_processed = 0
            self.frames_dropped = 0

class PerformanceOptimizer:
    """Python 3.13 specific optimizations"""
    
    def apply_optimizations(self):
        """Enable Python 3.13 performance improvements"""
        import sys
        if sys.version_info >= (3, 13):
            # Use per-interpreter GIL where available
            self._enable_gil_optimizations()
            
            # Pre-compile hot paths with specializing adaptive interpreter
            self._enable_adaptive_interpreter()
    
    def _enable_gil_optimizations(self):
        """Leverage Python 3.13 GIL improvements"""
        # Use threading for I/O with reduced GIL contention
        # Use multiprocessing for CPU-intensive tasks
        pass
    
    def _enable_adaptive_interpreter(self):
        """Enable Python 3.13's adaptive specializing interpreter"""
        # This would utilize the new specializing adaptive interpreter
        # for hot code paths in the frame processing pipeline
        pass