#   src/workers/aimbot.py
#   Aimbot worker coordinating screen capture, target detection, and mouse control

# ----- Imports ----- #
import threading
import time
import logging
from typing import Optional, Tuple, Dict, Any
import numpy as np

try:
    import pynput
    from pynput.mouse import Button, Controller as MouseController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - aimbot mouse control disabled")

from workers.function_worker import BaseWorker
from workers.screen_capturer import ScreenCapturer
from workers.target_detector import TargetDetector

# ----- Main Class ----- #
class AimbotWorker(BaseWorker) :
    # Main aimbot worker coordinating capture, detection, and mouse movement
    
    def __init__(self, 
                 capture_region: Optional[Tuple[int, int, int, int]] = None,
                 target_fps: int = 60,
                 hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = ((0, 120, 70), (10, 255, 255)),
                 smooth_factor: float = 0.2,
                 activation_key: str = 'alt_l'):
        super().__init__()
        
        # Configuration
        self.capture_region = capture_region
        self.target_fps = target_fps
        self.smooth_factor = max(0.01, min(1.0, smooth_factor))  # Clamp to valid range
        self.activation_key = activation_key
        
        # Components
        self.capturer = ScreenCapturer(region=capture_region, target_fps=target_fps)
        self.detector = TargetDetector(lower_hsv=hsv_range[0], upper_hsv=hsv_range[1])
        self.mouse = MouseController() if PYNPUT_AVAILABLE else None
        
        # State management
        self.is_active = False
        self.last_target_pos: Optional[Tuple[float, float]] = None
        self.state_lock = threading.RLock()
        
        # Performance monitoring
        self.frame_count = 0
        self.detection_count = 0
        self.start_time = time.time()
        
        logging.info(f"Aimbot worker initialized - Region: {capture_region}, FPS: {target_fps}")
    
    def _work(self) -> None :
        # Main aimbot processing loop
        if not PYNPUT_AVAILABLE :
            logging.error("Aimbot requires pynput for mouse control")
            return
            
        # Start screen capture
        self.capturer.start()
        
        logging.info("Aimbot worker started")
        
        try :
            while self.running :
                # Wait for new frame
                if self.capturer.wait_for_frame(timeout=0.1):
                    self._process_frame()
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.001)
                
        except Exception as e :
            logging.error(f"Aimbot worker error: {e}")
        finally :
            self._cleanup()
            logging.info("Aimbot worker stopped")
    
    def _process_frame(self) -> None :
        # Process a single frame for target detection and aiming
        # get latest frame
        frame = self.capturer.get_latest_frame()
        if frame is None :
            return
            
        self.frame_count += 1
        
        # detect targets
        detection = self.detector.detect_targets(frame)
        
        with self.state_lock :
            # Update activation state based on key press
            self._update_activation_state()
            
            if detection is not None and self.is_active :
                self.detection_count += 1
                self._aim_at_target(detection)
            else :
                self.last_target_pos = None
    
    def _update_activation_state(self) -> None :
        # Update aimbot activation state based on key presses

        # use pynput's keyboard listener
        # can extend this with proper key detection
        self.is_active = self.running
    
    def _aim_at_target(self, detection: Dict[str, Any]) -> None :
        # Move mouse to aim at detected target
        if self.mouse is None :
            return
            
        try :
            screen_x, screen_y = detection['screen_position']
            
            # Convert normalized coordinates to screen coordinates
            screen_width, screen_height = self._get_screen_dimensions()
            target_x = int(screen_x * screen_width)
            target_y = int(screen_y * screen_height)
            
            # Get current mouse position
            current_x, current_y = self.mouse.position
            
            # Apply smoothing
            if self.last_target_pos:
                last_x, last_y = self.last_target_pos
                smoothed_x = last_x + (target_x - last_x) * self.smooth_factor
                smoothed_y = last_y + (target_y - last_y) * self.smooth_factor
            else:
                smoothed_x = current_x + (target_x - current_x) * self.smooth_factor
                smoothed_y = current_y + (target_y - current_y) * self.smooth_factor
            
            # Move mouse to smoothed position
            self.mouse.position = (int(smoothed_x), int(smoothed_y))
            self.last_target_pos = (smoothed_x, smoothed_y)
            
        except Exception as e :
            logging.error(f"Mouse movement error: {e}")
    
    def _get_screen_dimensions(self) -> Tuple[int, int] :
        # Get screen dimensions - simplified implementation
        # In production, you'd use a proper screen info library
        # For now, return a default resolution
        return 1920, 1080
    
    def set_activation_key(self, key: str) -> None :
        # Update activation key
        with self.state_lock :
            self.activation_key = key
            logging.info(f"Activation key updated: {key}")
    
    def set_smooth_factor(self, factor: float) -> None :
        # Update mouse smoothing factor
        with self.state_lock :
            self.smooth_factor = max(0.01, min(1.0, factor))
            logging.info(f"Smooth factor updated: {self.smooth_factor}")
    
    def set_hsv_range(self, lower_hsv: Tuple[int, int, int], upper_hsv: Tuple[int, int, int]) -> None :
        # Update target detection HSV range
        self.detector.set_hsv_range(lower_hsv, upper_hsv)
    
    def set_capture_region(self, region: Optional[Tuple[int, int, int, int]]) -> None :
        # Update screen capture region
        # Note: This requires restarting the capturer
        self.capture_region = region
        logging.info(f"Capture region updated: {region}")
    
    def get_performance_stats(self) -> Dict[str, Any] :
        # Get performance statistics
        current_time = time.time()
        runtime = current_time - self.start_time
        
        return {
            'runtime': runtime,
            'frames_processed': self.frame_count,
            'detections_made': self.detection_count,
            'fps': self.frame_count / runtime if runtime > 0 else 0,
            'detection_rate': self.detection_count / self.frame_count if self.frame_count > 0 else 0,
            'is_active': self.is_active
        }
    
    def _cleanup(self) -> None :
        # Cleanup resources
        self.capturer.stop()
        logging.debug("Aimbot resources cleaned up")