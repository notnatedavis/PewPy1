#   src/workers/screen_capturer.py
#   DirectX screen capture

# ----- Imports ----- #
import cv2
import numpy as np
import threading
from ctypes import windll, byref, c_void_p, c_int
import dxcam
from core.performance_monitor import PerformanceMonitor

# ----- main Class ----- #
class HighPerformanceScreenCapturer :
    # Python equivalent of C++ ScreenCapturer using dxcam (DirectX wrapper)
    # leverages Python 3.13 memory views for zero-copy operations

    def __init__(self, region: tuple = None) :
        self.camera = dxcam.create(region=region)
        self.performance = PerformanceMonitor()
        self.frame_buffer = None
        self.lock = threading.Lock()
        self.capture_thread = None
        self.running = False
        
    def start_capture_loop(self) :
        # Continuous capture in background thread
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_worker)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def _capture_worker(self) :
        # Python 3.13 optimized capture loop with minimal allocations
        self.camera.start(region=self.region, target_fps=240)
        while self.running :
            with self.lock :
                # dxcam provides zero-copy numpy arrays
                self.frame_buffer = self.camera.get_latest_frame()
            self.performance.record_frame_time()
    
    def get_latest_frame(self) :
        # Thread-safe frame access with memory view
        with self.lock :
            if self.frame_buffer is not None :
                # Python 3.13 memory view for zero-copy processing
                return memoryview(self.frame_buffer)
        return None