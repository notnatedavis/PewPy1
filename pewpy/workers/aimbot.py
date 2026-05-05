#   pewpy/workers/aimbot.py
#   Aimbot worker (passive) coordinating capture, detection, mouse.

# ----- Imports ----- #
import threading
import time
import logging
from typing import Optional, Tuple, Dict, Any
import numpy as np
try :
    import pynput
    from pynput.mouse import Button, Controller as MouseController
    PYNPUT_AVAILABLE = True
except ImportError :
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - aimbot mouse control disabled")
from .function_worker import BaseWorker
from .screen_capturer import ScreenCapturer
from .target_detector import TargetDetector

# ----- Main Class ----- #
class AimbotWorker(BaseWorker):
    # Aimbot: captures screen, detects targets, moves mouse
    
    def __init__(self, 
                 capture_region: Optional[Tuple[int, int, int, int]] = None,
                 target_fps: int = 60,
                 hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = ((0, 120, 70), (10, 255, 255)),
                 smooth_factor: float = 0.2,
                 activation_key: str = 'alt_l') :
        super().__init__()
        self.capture_region = capture_region
        self.target_fps = target_fps
        self.smooth_factor = max(0.01, min(1.0, smooth_factor))
        self.activation_key = activation_key
        
        self.capturer = ScreenCapturer(region=capture_region, target_fps=target_fps)
        self.detector = TargetDetector(lower_hsv=hsv_range[0], upper_hsv=hsv_range[1])
        self.mouse = MouseController() if PYNPUT_AVAILABLE else None
        
        self.is_active = False
        self.last_target_pos: Optional[Tuple[float, float]] = None
        self.state_lock = threading.RLock()
        self.frame_count = 0
        self.detection_count = 0
        
        # Cache screen dimensions (populated when capturer starts)
        self._screen_width = 1920
        self._screen_height = 1080
        logging.info(f"Aimbot initialized - Region: {capture_region}, FPS: {target_fps}")
    
    def _work_cycle(self) -> None :
        # Called repeatedly by the worker thread
        if not PYNPUT_AVAILABLE :
            return
        # Wait for new frame (non-blocking)
        if self.capturer.wait_for_frame(timeout=0.001) :
            self._process_frame()
    
    def _process_frame(self) -> None :
        frame = self.capturer.get_latest_frame()
        if frame is None :
            return
        self.frame_count += 1
        detection = self.detector.detect_targets(frame)
        with self.state_lock :
            # Placeholder: activation key detection (could be extended)
            self.is_active = True  # For demo
            if detection is not None and self.is_active :
                self.detection_count += 1
                self._aim_at_target(detection)
            else :
                self.last_target_pos = None
    
    def _aim_at_target(self, detection: Dict[str, Any]) -> None :
        if self.mouse is None :
            return
        try :
            screen_x, screen_y = detection['screen_position']
            # Use actual screen dimensions
            target_x = int(screen_x * self._screen_width)
            target_y = int(screen_y * self._screen_height)
            current_x, current_y = self.mouse.position
            if self.last_target_pos :
                last_x, last_y = self.last_target_pos
                smoothed_x = last_x + (target_x - last_x) * self.smooth_factor
                smoothed_y = last_y + (target_y - last_y) * self.smooth_factor
            else :
                smoothed_x = current_x + (target_x - current_x) * self.smooth_factor
                smoothed_y = current_y + (target_y - current_y) * self.smooth_factor
            self.mouse.position = (int(smoothed_x), int(smoothed_y))
            self.last_target_pos = (smoothed_x, smoothed_y)
        except Exception as e :
            logging.error(f"Mouse movement error: {e}")

    # Configuration update methods...
    def set_smooth_factor(self, factor: float) -> None :
        with self.state_lock :
            self.smooth_factor = max(0.01, min(1.0, factor))

    def set_hsv_range(self, lower, upper) :
        self.detector.set_hsv_range(lower, upper)

    def set_capture_region(self, region) :
        self.capture_region = region
        
        # Note: would require restart; for simplicity, ignore dynamic

    # --- Aimbot (tab) activation key ---
    def set_activation_key(self, key: str) -> None :
        # Update the activation key string
        # (Future: integrate with pynput listener to dynamically change the key)
        with self.state_lock :
            self.activation_key = key
        logging.info(f"Aimbot activation key set to: {key}")

    # ----- Core Functions ----- 

    def run(self, stop_event: threading.Event, pause_event: threading.Event) -> None :
        # Override to start capturer before loop
        self.capturer.start()
        # Obtain screen dimensions from capturer after start
        if self.capturer.camera is not None:
            # dxcam stores width/height of the captured region or full screen
            region_info = self.capturer.camera.output_info
            if region_info and isinstance(region_info, dict):
                self._screen_width = region_info.get('width', 1920)
                self._screen_height = region_info.get('height', 1080)
        try :
            super().run(stop_event, pause_event)
        finally :
            self.capturer.stop()
    
    def _cleanup(self) -> None :
        self.capturer.stop()
        logging.debug("Aimbot cleaned up")