#   src/workers/target_detector.py
#   OpenCV target detection

# ----- Imports ----- #
import cv2
import numpy as np
from multiprocessing import shared_memory
import threading
from core.performance_monitor import PerformanceMonitor

# ----- main Class ----- #
class GPUTargetDetector :
    # Hybrid CPU/GPU target detection with Python 3.13 multiprocessing
    # Uses shared memory for inter-process zero-copy data transfer

    def __init__(self, lower_hsv: tuple, upper_hsv: tuple) :
        self.lower_hsv = np.array(lower_hsv, dtype=np.uint8)
        self.upper_hsv = np.array(upper_hsv, dtype=np.uint8)
        self.performance = PerformanceMonitor()
        
        # Reusable buffers to avoid allocations
        self.hsv_buffer = None
        self.mask_buffer = None
        self.contours_buffer = []
        
        # GPU acceleration if available
        self.gpu_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if self.gpu_available :
            self.gpu_stream = cv2.cuda_Stream()
    
    def detect_targets(self, frame_memory_view) :
        # Main detection with Python 3.13 memory optimization
        if frame_memory_view is None :
            return None
            
        # Convert memoryview to numpy array without copy
        frame = np.array(frame_memory_view, dtype=np.uint8)
        
        if self.gpu_available :
            return self._gpu_detection(frame)
        else :
            return self._cpu_detection(frame)
    
    def _gpu_detection(self, frame) :
        # CUDA-accelerated detection path
        # Upload to GPU (async)
        gpu_frame = cv2.cuda_GpuMat()
        gpu_frame.upload(frame, stream=self.gpu_stream)
        
        # GPU processing pipeline
        gpu_hsv = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2HSV, stream=self.gpu_stream)
        gpu_mask = cv2.cuda.inRange(gpu_hsv, self.lower_hsv, self.upper_hsv, stream=self.gpu_stream)
        
        # Download result (async)
        cpu_mask = gpu_mask.download(stream=self.gpu_stream)
        self.gpu_stream.waitForCompletion()
        
        return self._find_contours(cpu_mask)
    
    def _cpu_detection(self, frame) :
        # Optimized CPU detection with pre-allocated buffers
        # Reuse buffers to avoid allocations
        if self.hsv_buffer is None or self.hsv_buffer.shape != frame.shape :
            self.hsv_buffer = np.empty_like(frame)
        
        cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, dst=self.hsv_buffer)
        
        if self.mask_buffer is None or self.mask_buffer.shape != frame.shape[:2] :
            self.mask_buffer = np.empty(frame.shape[:2], dtype=np.uint8)
        
        cv2.inRange(self.hsv_buffer, self.lower_hsv, self.upper_hsv, dst=self.mask_buffer)
        
        return self._find_contours(self.mask_buffer)