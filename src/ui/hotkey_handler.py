#   src/ui/hotkey_handler.py
#   UI-specific hotkey handling separate from safety monitoring

# ----- Imports ----- #
import threading
import time
import logging
from pynput import keyboard
from typing import Dict, Callable, Optional

# ----- main Class ----- #
class UIHotkeyHandler :
    # Handles UI-specific hotkeys for overlay control and configuration

    def __init__(self) :
        self.hotkeys = {}
        self.listener = None
        self.running = False
        self.callbacks = {}
        
    def register_hotkey(self, hotkey: str, callback: Callable, description: str = "") :
        # Register a hotkey with callback
        self.hotkeys[hotkey] = {
            'callback': callback,
            'description': description
        }
        logging.info(f"Registered UI hotkey: {hotkey} - {description}")
    
    def unregister_hotkey(self, hotkey: str) :
        # Unregister a hotkey
        if hotkey in self.hotkeys:
            del self.hotkeys[hotkey]
            logging.info(f"Unregistered UI hotkey: {hotkey}")
    
    def start(self) :
        # Start hotkey listener
        if self.running:
            return
        
        self.running = True
        self.listener = keyboard.GlobalHotKeys(self.hotkeys)
        self.listener.start()
        logging.info("UI hotkey handler started")
    
    def stop(self) :
        # Stop hotkey listener
        self.running = False
        if self.listener:
            self.listener.stop()
        logging.info("UI hotkey handler stopped")
    
    def get_registered_hotkeys(self) -> Dict :
        # Get all registered hotkeys with descriptions
        return {
            hotkey: info['description'] 
            for hotkey, info in self.hotkeys.items()
        }