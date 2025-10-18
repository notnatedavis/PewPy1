#   src/workers/input_controller.py
#   mouse movement control

# ----- Imports ----- #
import ctypes
from ctypes import wintypes
import time
import math
import threading
from core.performance_monitor import PerformanceMonitor

# ----- main Class ----- #
class LowLatencyInputController :
    # High-performance mouse input with smoothing and prediction
    # Uses Windows API directly via ctypes for minimal latency

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.performance = PerformanceMonitor()
        self.input_lock = threading.Lock()
        self.last_position = (0, 0)
        
        # Smoothing parameters
        self.smoothing_steps = 8
        self.prediction_factor = 0.1
    
    def move_mouse_smooth(self, target_x: int, target_y: int):
        # Thread-safe smooth mouse movement with prediction
        with self.input_lock:
            current_x, current_y = self._get_cursor_pos()
            
            # Apply prediction based on previous movement
            predicted_x, predicted_y = self._predict_position(
                current_x, current_y, target_x, target_y
            )
            
            # Cubic easing function for smooth movement
            for step in range(1, self.smoothing_steps + 1):
                t = step / self.smoothing_steps
                eased_t = self._cubic_ease_out(t)
                
                interp_x = current_x + (predicted_x - current_x) * eased_t
                interp_y = current_y + (predicted_y - current_y) * eased_t
                
                self._set_cursor_pos(int(interp_x), int(interp_y))
                time.sleep(0.001)  # 1ms between steps
    
    def _predict_position(self, current_x, current_y, target_x, target_y):
        # Simple prediction to compensate for system latency
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Apply prediction based on movement velocity
        predicted_x = target_x + dx * self.prediction_factor
        predicted_y = target_y + dy * self.prediction_factor
        
        return predicted_x, predicted_y
    
    def _cubic_ease_out(self, t):
        # Cubic easing function for smooth movement
        return 1 - (1 - t) ** 3
    
    def _get_cursor_pos(self):
        # Direct Windows API call for cursor position
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y
    
    def _set_cursor_pos(self, x, y):
        # Direct Windows API call for setting cursor position
        self.user32.SetCursorPos(x, y)