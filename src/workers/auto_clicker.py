#   src/workers/auto_clicker.py
#   auto-click functionality worker implementation

# ----- Imports ----- #
import time
import logging
from typing import Optional
from workers.function_worker import BaseWorker
try : 
    import pynput
    from pynput.mouse import Button, Controller as MouseController
    from pynput.keyboard import Listener as KeyboardListener
    PYNPUT_AVAILABLE = True
except ImportError :
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - auto-clicker disabled")

# ----- Main Class Application ----- #
class AutoClicker(BaseWorker) :
    # Auto-clicker worker with configurable settings
    
    def __init__(self, click_interval: float = 0.1, button: Button = Button.left) :
        super().__init__()
        self.click_interval = click_interval
        self.button = button
        self.mouse = MouseController() if PYNPUT_AVAILABLE else None
        
    def _work(self) :
        # Main auto-clicker loop
        if not PYNPUT_AVAILABLE :
            logging.error("Auto-clicker requires pynput")
            return
            
        logging.info(f"Auto-clicker started (interval: {self.click_interval}s)")
        
        try :
            while self.running :
                if self.mouse:
                    self.mouse.click(self.button)
                time.sleep(self.click_interval)
                
        except Exception as e :
            logging.error(f"Auto-clicker error: {e}")
        finally :
            logging.info("Auto-clicker stopped")
            
    def set_interval(self, interval: float):
        self.click_interval = max(0.01, interval)  # Minimum 10ms interval