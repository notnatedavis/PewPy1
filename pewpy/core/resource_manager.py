#   src/core/resource_manager.py
#   Adaptive resource monitoring and management

# ----- Imports ----- #
import threading
import time
import logging
from typing import Dict, Any, Callable, List
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - resource management disabled")

# ----- Main Class ----- #
class ResourceManager:
    # Monitors system resources and triggers adaptive configuration updates
    
    def __init__(self, config: Dict[str, Any]) :
        self.config = config
        self.running = False
        self._thread: threading.Thread = None
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.RLock()
        self._check_interval = config.get('resource_manager', {}).get('check_interval', 5)
        self.cpu_threshold = config.get('resource_manager', {}).get('cpu_threshold', 80)
        self.fps_step = config.get('resource_manager', {}).get('fps_reduction_step', 10)
        self.min_fps = config.get('resource_manager', {}).get('min_fps', 30)
        
    def start(self) -> None :
        if not PSUTIL_AVAILABLE :
            logging.warning("Resource manager disabled (psutil missing)")
            return
        with self._lock :
            if self.running :
                return
            self.running = True
            self._thread = threading.Thread(target=self._monitor, daemon=True, name="ResourceMonitor")
            self._thread.start()
            logging.info("Resource manager started")
    
    def stop(self) -> None :
        with self._lock :
            self.running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            logging.info("Resource manager stopped")
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None :
        with self._lock :
            self._callbacks.append(callback)
            logging.debug(f"Resource callback registered: {callback.__name__}")
    
    def _monitor(self) -> None :
        while self.running :
            try :
                cpu_percent = psutil.cpu_percent(interval=1)
                mem_avail = psutil.virtual_memory().available
                # Placeholder for GPU stats (future)
                new_config = self._calculate_config(cpu_percent, mem_avail)
                if new_config :
                    with self._lock :
                        for cb in self._callbacks :
                            try :
                                cb(new_config)
                            except Exception as e :
                                logging.error(f"Resource callback failed: {e}")
                time.sleep(self._check_interval)
            except Exception as e :
                logging.error(f"Resource monitor error: {e}")
                time.sleep(5)
    
    def _calculate_config(self, cpu: float, mem: int) -> Dict[str, Any] :
        # Simple threshold-based adjustments
        changes = {}
        base_fps = self.config.get('workers', {}).get('screen_capturer', {}).get('target_fps', 60)
        if cpu > self.cpu_threshold :
            # reduce FPS
            new_fps = max(self.min_fps, base_fps - self.fps_step)
            if new_fps != base_fps :
                changes['target_fps'] = new_fps
                logging.info(f"Resource manager: reducing FPS to {new_fps} (CPU={cpu}%)")
        # Add more rules as needed
        return changes