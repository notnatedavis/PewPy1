#   src/workers/auto_clicker.py
#   Auto-clicker worker (passive)

# ----- Imports ----- #
import threading
import time
import logging
from .base import BaseWorker
try:
    from pynput.mouse import Button, Controller as MouseController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - auto-clicker disabled")

# ----- Main Class ----- #
class AutoClicker(BaseWorker) :
    def __init__(self, click_interval: float = 0.1, button: str = "left") -> None :
        super().__init__(name="AutoClicker")
        self.click_interval = max(0.01, min(10.0, click_interval))
        self.button_name = button
        self._button_map = {
            "left": Button.left if PYNPUT_AVAILABLE else None,
            "right": Button.right if PYNPUT_AVAILABLE else None,
            "middle": Button.middle if PYNPUT_AVAILABLE else None
        }
        self.button = self._button_map.get(button, Button.left if PYNPUT_AVAILABLE else None)
        self.mouse = MouseController() if PYNPUT_AVAILABLE else None
        self._interval_lock = threading.Lock()
        self._last_click_time = 0.0
        self._click_count = 0
        logging.info(f"AutoClicker initialized: interval={self.click_interval}s")
    
    def _work_cycle(self) -> None :
        if not PYNPUT_AVAILABLE :
            return
        current_time = time.time()
        with self._interval_lock :
            interval = self.click_interval
        if current_time - self._last_click_time >= interval :
            try :
                if self.mouse :
                    self.mouse.click(self.button)
                    self._last_click_time = current_time
                    self._click_count += 1
            except Exception as e :
                logging.error(f"Mouse click failed: {e}")
                time.sleep(min(interval * 2, 1.0))
    
    def set_interval(self, interval: float) -> None :
        interval_float = max(0.01, min(10.0, float(interval)))
        with self._interval_lock :
            self.click_interval = interval_float
        logging.info(f"Auto-clicker interval updated to {interval_float}s")