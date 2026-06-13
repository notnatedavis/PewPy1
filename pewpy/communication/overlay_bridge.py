#   pewpy/communication/overlay_bridge.py
#   Thread‑safe data bridge between workers (e.g. aimbot → overlay)

# ----- Imports ----- 
import threading
import logging
from typing import Dict, Any

# ----- Main Class ----- 
class OverlayData :
    # A simple thread‑safe dictionary for sharing detection results
    # and other visualisation data among workers

    def __init__(self) -> None :
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}

    def update(self, data: Dict[str, Any]) -> None :
        with self._lock :
            self._data.update(data)
            if 'target_center' in data :
                logging.debug(f"OverlayData updated: target_center={data.get('target_center')}")
            if 'target_center' in data and data['target_center'] is None :
                logging.debug("OverlayData cleared target_center")

    def get(self) -> Dict[str, Any] :
        # return a copy of the current data
        with self._lock:
            return self._data.copy()

    def clear(self) -> None :
        # remove all stored data
        with self._lock:
            self._data.clear()
            logging.debug("OverlayData cleared completely")