#   src/workers/safety_monitor.py
#   Safety monitoring with emergency stop functionality

# ----- Imports ----- #
import threading
import time
import logging
from pynput import keyboard
from typing import Callable, Optional

# ----- main Class ----- #
class SafetyMoniter :
    # Monitors system state and provides emergency stop functionality
    # Separate from UI hotkeys for critical safety functions

    def __init__(self) :
        self.emergency_stop = False
        self.aimbot_enabled = False
        self.listener = None
        self.running = False
        
        # Callbacks
        self.emergency_callbacks = []
        self.toggle_callbacks = []
        
        # Cooldown to prevent rapid toggling
        self.last_toggle_time = 0
        self.toggle_cooldown = 0.5  # seconds
    
    def register_emergency_callback(self, callback: Callable) :
        # Register callback for emergency stop
        self.emergency_callbacks.append(callback)
    
    def register_toggle_callback(self, callback: Callable) :
        # Register callback for aimbot toggle
        self.toggle_callbacks.append(callback)
    
    def start(self) :
        # Start safety monitoring
        if self.running :
            return
        
        self.running = True
        
        # Start keyboard listener
        self.listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.listener.start()
        
        logging.info("Safety monitor started")
    
    def stop(self) :
        # Stop safety monitoring
        self.running = False
        self.emergency_stop = True
        
        if self.listener :
            self.listener.stop()
        
        logging.info("Safety monitor stopped")
    
    def _on_key_press(self, key) :
        # Handle key press events
        try:
            # Emergency stop (F10)
            if key == keyboard.Key.f10 :
                self._trigger_emergency_stop()
            
            # Toggle aimbot (F2)
            elif key == keyboard.Key.f2 :
                current_time = time.time()
                if current_time - self.last_toggle_time > self.toggle_cooldown :
                    self._toggle_aimbot()
                    self.last_toggle_time = current_time
            
            # Exit application (F12)
            elif key == keyboard.Key.f12 :
                self._trigger_exit()
                
        except Exception as e :
            logging.error(f"Key press handling error: {e}")
    
    def _on_key_release(self, key) :
        # Handle key release events
        pass  # Currently not used
    
    def _trigger_emergency_stop(self) :
        # Trigger emergency stop
        if not self.emergency_stop :
            self.emergency_stop = True
            self.aimbot_enabled = False
            logging.warning("EMERGENCY STOP TRIGGERED")
            
            # Notify callbacks
            for callback in self.emergency_callbacks :
                try :
                    callback()
                except Exception as e :
                    logging.error(f"Emergency callback error: {e}")
    
    def _toggle_aimbot(self) :
        # Toggle aimbot enabled state
        self.aimbot_enabled = not self.aimbot_enabled
        state = "ENABLED" if self.aimbot_enabled else "DISABLED"
        logging.info(f"Aimbot {state}")
        
        # Notify callbacks
        for callback in self.toggle_callbacks :
            try :
                callback(self.aimbot_enabled)
            except Exception as e :
                logging.error(f"Toggle callback error: {e}")
    
    def _trigger_exit(self):
        # Trigger application exit
        logging.info("Exit triggered by hotkey")
        self.stop()
        
        # This would typically signal the main application to exit
        # In practice, you'd have a more sophisticated shutdown mechanism
    
    def is_safe(self) -> bool :
        # Check if system is in safe state
        return not self.emergency_stop
    
    def is_aimbot_enabled(self) -> bool :
        # Check if aimbot is enabled
        return self.aimbot_enabled and not self.emergency_stop
    
    def reset_emergency(self) :
        # Reset emergency stop state
        self.emergency_stop = False
        logging.info("Emergency state reset")