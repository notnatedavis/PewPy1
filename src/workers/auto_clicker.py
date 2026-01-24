#   src/workers/auto_clicker.py
#   Auto-click functionality worker

# ----- Imports ----- #
import threading
import time
import logging
from .function_worker import BaseWorker
try : 
    import pynput
    from pynput.mouse import Button, Controller as MouseController
    PYNPUT_AVAILABLE = True
except ImportError :
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - auto-clicker disabled")

class AutoClicker(BaseWorker) :
    # Auto-clicker worker with configurable settings
    
    def __init__(self, click_interval: float = 0.1, button: str = "left") -> None :
        super().__init__(name="AutoClicker")
        
        self.click_interval = max(0.01, min(10.0, click_interval))
        self.button_name = button
        
        # map button names
        self._button_map = {
            "left": Button.left if PYNPUT_AVAILABLE else None,
            "right": Button.right if PYNPUT_AVAILABLE else None,
            "middle": Button.middle if PYNPUT_AVAILABLE else None
        }
        
        self.button = self._button_map.get(button, Button.left if PYNPUT_AVAILABLE else None)
        self.mouse = MouseController() if PYNPUT_AVAILABLE else None
        
        # thread-safe interval updates
        self._interval_lock = threading.Lock()
        self._last_click_time = 0.0
        self._click_count = 0
        
        logging.info(f"AutoClicker initialized: interval={self.click_interval}s")
    
    def _work_cycle(self) -> None :
        # Main auto-clicker loop
        if not PYNPUT_AVAILABLE :
            logging.error("Auto-clicker requires pynput")
            self.stop()
            return
        
        current_time = time.time()
        
        # get current interval
        with self._interval_lock :
            interval = self.click_interval
        
        # check if time to click
        if current_time - self._last_click_time >= interval :
            try :
                if self.mouse :
                    self.mouse.click(self.button)
                    self._last_click_time = current_time
                    self._click_count += 1
                    
            except Exception as e :
                logging.error(f"Mouse click failed: {e}")
                time.sleep(min(interval * 2, 1.0))
        
        # adaptive sleep
        next_click_in = max(0, interval - (time.time() - self._last_click_time))
        if next_click_in > 0.001 :
            time.sleep(min(next_click_in, 0.1))
    
    def set_interval(self, interval: float) -> None :
        # update click interval
        try :
            interval_float = float(interval)
            
            # validate and clamp
            interval_float = max(0.01, min(10.0, interval_float))
            
            # update thread-safely
            with self._interval_lock :
                old_interval = self.click_interval
                self.click_interval = interval_float
            
            logging.info(f"Auto-clicker interval updated: {old_interval}s -> {interval_float}s")
            
        except (ValueError, TypeError) as e :
            logging.error(f"Invalid interval: {e}")
            raise ValueError(f"Interval must be a number between 0.01 and 10.0")