#   pewpy/workers/overlay_communication.py
#   Thread‑safe data bridge between workers (e.g. aimbot → overlay)

# ----- Imports ----- 
import threading
from typing import Dict, Any

# ----- Main Class ----- 
class OverlayData :
    # A simple thread‑safe dictionary for sharing detection results
    # and other visualisation data among workers

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}

    def update(self, data: Dict[str, Any]) -> None:
        # Merge new key‑value pairs into the shared data
        with self._lock:
            self._data.update(data)

    def get(self) -> Dict[str, Any]:
        # Return a copy of the current data
        with self._lock:
            return self._data.copy()

    def clear(self) -> None:
        # Remove all stored data
        with self._lock:
            self._data.clear()