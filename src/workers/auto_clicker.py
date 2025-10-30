#   src/workers/auto_clicker.py
#   auto-click functionality worker implementation

# ----- Imports ----- #
import threading
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
        self._interval_lock = threading.Lock()  # thread safety for interval updates
        
    def _work(self) :
        # Main auto-clicker loop - runs continuously until stop() is called
        if not PYNPUT_AVAILABLE :
            logging.error("Auto-clicker requires pynput")
            return
        
        logging.info(f"Auto-clicker started (interval: {self.click_interval}s)")
    
        try :
            last_click_time = 0
            while self.running :
                current_time = time.time()
            
                # get current interval thread-safely
                with self._interval_lock :
                    interval = self.click_interval
            
                # click if enough time has passed
                if current_time - last_click_time >= interval :
                    if self.mouse :
                        try :
                            self.mouse.click(self.button)
                            last_click_time = current_time
                        except Exception as e :
                            logging.error(f"Mouse click failed: {e}")
                            # don't break the loop on click errors

                # small sleep to prevent CPU spinning but remain responsive
                time.sleep(0.01)  # 10ms sleep for better responsiveness

        except Exception as e :
            logging.error(f"Auto-clicker error: {e}")
        finally :
            logging.info("Auto-clicker stopped")
    
    def set_interval(self, interval: float) :
        # Update click interval (thread-safe)
        try :
            interval = float(interval)
            # Validate interval range
            if interval < 0.01 :  # Minimum 10ms
                interval = 0.01
            elif interval > 10.0 :  # Maximum 10 seconds
                interval = 10.0
                
            with self._interval_lock :
                self.click_interval = interval
            logging.debug(f"Auto-clicker interval updated to {interval}s")
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid interval {interval}: {e}")