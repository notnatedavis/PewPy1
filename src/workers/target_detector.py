#   src/workers/target_detector.py
#   OpenCV target detection with GPU acceleration

# ----- Imports ----- #
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, Dict, Any
from workers.function_worker import BaseWorker

# ----- Main Class ----- #
class TargetDetector(BaseWorker):
    """Target detection using OpenCV with HSV color filtering"""
    
    def __init__(self, 
                 lower_hsv: Tuple[int, int, int] = (0, 120, 70),
                 upper_hsv: Tuple[int, int, int] = (10, 255, 255),
                 min_area: int = 50,
                 max_area: int = 50000):
        super().__init__()
        self.lower_hsv = np.array(lower_hsv, dtype=np.uint8)
        self.upper_hsv = np.array(upper_hsv, dtype=np.uint8)
        self.min_area = min_area
        self.max_area = max_area
        
        # Detection state
        self.detection_result: Optional[Dict[str, Any]] = None
        self.result_lock = threading.Lock()
        
        # Reusable buffers for performance
        self.hsv_buffer = None
        self.mask_buffer = None
        
        # GPU acceleration
        self.gpu_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if self.gpu_available:
            logging.info("GPU acceleration available for target detection")
            try:
                self.gpu_stream = cv2.cuda_Stream()
            except Exception as e:
                logging.warning(f"GPU stream creation failed: {e}")
                self.gpu_available = False
        else:
            logging.info("Using CPU for target detection")
    
    def _work(self) -> None:
        """Main detection loop - placeholder for continuous processing"""
        # This worker is designed to be called on-demand via detect_targets()
        # For continuous detection, override this method
        while self.running:
            time.sleep(0.1)  # Minimal CPU usage
    
    def detect_targets(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """Detect targets in a frame and return detection results"""
        if frame is None:
            return None
            
        try:
            if self.gpu_available:
                result = self._gpu_detection(frame)
            else:
                result = self._cpu_detection(frame)
                
            with self.result_lock:
                self.detection_result = result
                
            return result
            
        except Exception as e:
            logging.error(f"Target detection error: {e}")
            return None
    
    def _cpu_detection(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """CPU-based target detection"""
        # Convert to HSV
        if self.hsv_buffer is None or self.hsv_buffer.shape != frame.shape:
            self.hsv_buffer = np.empty_like(frame)
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, dst=self.hsv_buffer)
        
        # Create mask
        if self.mask_buffer is None or self.mask_buffer.shape != frame.shape[:2]:
            self.mask_buffer = np.empty(frame.shape[:2], dtype=np.uint8)
        mask = cv2.inRange(hsv_frame, self.lower_hsv, self.upper_hsv, dst=self.mask_buffer)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return self._process_contours(contours, frame.shape)
    
    def _gpu_detection(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """GPU-accelerated target detection"""
        try:
            # Upload to GPU
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame, stream=self.gpu_stream)
            
            # Convert to HSV on GPU
            gpu_hsv = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2HSV, stream=self.gpu_stream)
            
            # Create mask on GPU
            gpu_mask = cv2.cuda.inRange(gpu_hsv, self.lower_hsv, self.upper_hsv, stream=self.gpu_stream)
            
            # Download result
            cpu_mask = gpu_mask.download(stream=self.gpu_stream)
            self.gpu_stream.waitForCompletion()
            
            # Find contours on CPU
            contours, _ = cv2.findContours(cpu_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            return self._process_contours(contours, frame.shape)
            
        except Exception as e:
            logging.warning(f"GPU detection failed, falling back to CPU: {e}")
            return self._cpu_detection(frame)
    
    def _process_contours(self, contours: list, frame_shape: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """Process contours and return target information"""
        if not contours:
            return None
            
        # Find largest contour by area
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        # Filter by area
        if area < self.min_area or area > self.max_area:
            return None
        
        # Get bounding rectangle and center
        x, y, w, h = cv2.boundingRect(largest_contour)
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Calculate screen coordinates (normalized to 0-1)
        screen_x = center_x / frame_shape[1]
        screen_y = center_y / frame_shape[0]
        
        return {
            'center': (center_x, center_y),
            'screen_position': (screen_x, screen_y),
            'bounding_box': (x, y, w, h),
            'area': area,
            'contour': largest_contour
        }
    
    def get_latest_detection(self) -> Optional[Dict[str, Any]]:
        """Get the latest detection result (thread-safe)"""
        with self.result_lock:
            return self.detection_result.copy() if self.detection_result is not None else None
    
    def set_hsv_range(self, lower_hsv: Tuple[int, int, int], upper_hsv: Tuple[int, int, int]) -> None:
        """Update HSV detection range"""
        self.lower_hsv = np.array(lower_hsv, dtype=np.uint8)
        self.upper_hsv = np.array(upper_hsv, dtype=np.uint8)
        logging.info(f"HSV range updated: {lower_hsv} -> {upper_hsv}")
    
    def set_area_limits(self, min_area: int, max_area: int) -> None:
        """Update area filtering limits"""
        self.min_area = min_area
        self.max_area = max_area
        logging.info(f"Area limits updated: {min_area} - {max_area}")