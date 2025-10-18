#   src/core/resource_manager.py
#   Resource management for GPU memory, CPU utilization, and system resources

# ----- Imports ----- #
import psutil
import gc
import threading
import time
from typing import Dict, Any, Optional
import cv2
import numpy as np

# ----- main Class ----- #
class ResourceManager :
    # Monitors and manages system resources for optimal performance
    # Implements adaptive resource allocation based on system load

    def __init__(self, max_memory_mb: int = 512, max_cpu_percent: int = 80) :
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.monitoring = False
        self.monitor_thread = None
        
        # Resource tracking
        self.memory_usage = 0
        self.cpu_usage = 0
        self.gpu_usage = 0
        self.temperature = 0
        
        # Resource pools
        self.buffer_pool = {}
        self.gpu_resources = {}
        
        # Performance metrics
        self.allocation_count = 0
        self.deallocation_count = 0
        
    def start_monitoring(self) :
        # Start resource monitoring
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_worker)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self) :
        # Stop resource monitoring
        self.monitoring = False
        if self.monitor_thread :
            self.monitor_thread.join(timeout=1.0)
    
    def allocate_buffer(self, key: str, shape: tuple, dtype: np.dtype) -> np.ndarray :
        # Allocate or reuse buffer from pool
        if key in self.buffer_pool :
            buffer = self.buffer_pool[key]
            if buffer.shape == shape and buffer.dtype == dtype :
                return buffer
        
        # Create new buffer
        buffer = np.empty(shape, dtype=dtype)
        self.buffer_pool[key] = buffer
        self.allocation_count += 1
        
        return buffer
    
    def release_buffer(self, key: str) :
        # Release buffer from pool
        if key in self.buffer_pool :
            del self.buffer_pool[key]
            self.deallocation_count += 1
    
    def optimize_resources(self) :
        # Perform resource optimization based on current usage
        memory_info = psutil.virtual_memory()
        self.memory_usage = memory_info.percent
        
        # Force garbage collection if memory usage is high
        if self.memory_usage > 80 :
            gc.collect()
            
        # Release unused buffers if memory is critical
        if self.memory_usage > 90 :
            self._release_unused_buffers()
    
    def _release_unused_buffers(self) :
        # Release buffers that haven't been used recently
        # Simple implementation - release all buffers
        # In production, you'd track buffer usage
        self.buffer_pool.clear()
        gc.collect()
    
    def get_system_status(self) -> Dict[str, Any] :
        # Get comprehensive system status
        return {
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "gpu_usage": self.gpu_usage,
            "temperature": self.temperature,
            "buffer_count": len(self.buffer_pool),
            "allocations": self.allocation_count,
            "deallocations": self.deallocation_count
        }
    
    def should_use_gpu(self) -> bool :
        # Determine if GPU should be used based on system load
        if self.cpu_usage > self.max_cpu_percent:
            return True
        return cv2.cuda.getCudaEnabledDeviceCount() > 0
    
    def _monitor_worker(self) :
        # Background resource monitoring
        while self.monitoring :
            try :
                # CPU usage
                self.cpu_usage = psutil.cpu_percent(interval=0.1)
                
                # Memory usage
                memory_info = psutil.virtual_memory()
                self.memory_usage = memory_info.percent
                
                # GPU usage (simplified - would use py3nvml in production)
                self.gpu_usage = 0  # Placeholder
                
                # Temperature (Linux/Windows specific)
                try :
                    temps = psutil.sensors_temperatures()
                    if temps :
                        self.temperature = list(temps.values())[0][0].current
                except :
                    self.temperature = 0
                
                time.sleep(1.0)  # Monitor every second
                
            except Exception as e :
                print(f"Resource monitoring error: {e}")
                time.sleep(5.0)