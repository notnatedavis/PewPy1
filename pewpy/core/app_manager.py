#   pewpy/core/app_manager.py
#   Main application coordination - uses config and resource manager

# ----- Imports ----- #
import logging
import threading
from typing import Dict, Any, Optional
from .thread_manager import ThreadManager
from .config import Config
from .resource_manager import ResourceManager
from ..utils.system_utils import get_cpu_count

# ----- Main Class ----- #
class PewPyApplication :
    def __init__(self, config: Optional[Config] = None) -> None :
        self.config = config or Config()
        self.running = False
        self.workers: Dict[str, Any] = {}
        self.worker_instances: Dict[str, Any] = {}
        self.thread_manager = ThreadManager()
        self.resource_manager = ResourceManager(self.config.config)
        self._lock = threading.RLock()
        
        self._initialize_workers()
        if self.config.get('resource_manager.enabled', True) :
            self.resource_manager.start()
            # Register callbacks for workers that can adapt
            self._register_resource_callbacks()
        logging.info("PewPyApplication initialized")
    
    def _initialize_workers(self) -> None :
        with self._lock :
            try :
                from pewpy.workers.auto_clicker import AutoClicker
                from pewpy.workers.overlay import Overlay
                
                # AutoClicker with config
                interval = self.config.get('workers.auto_clicker.default_interval', 0.1)
                button = self.config.get('workers.auto_clicker.button', 'left')
                self.workers['auto_clicker'] = AutoClicker(click_interval=interval, button=button)
                
                # Overlay with config
                pos = self.config.get('workers.overlay.position', [0,0])
                size = self.config.get('workers.overlay.size', [300,200])
                opacity = self.config.get('workers.overlay.opacity', 0.7)
                self.workers['overlay'] = Overlay(position=tuple(pos), size=tuple(size), opacity=opacity)
                
                # Aimbot - try to load, but make optional
                try:
                    from pewpy.workers.aimbot import AimbotWorker
                    aimbot_cfg = self.config.get('workers.aimbot', {})
                    self.workers['aimbot'] = AimbotWorker(
                        capture_region=aimbot_cfg.get('capture_region'),
                        target_fps=aimbot_cfg.get('target_fps', 60),
                        hsv_range=(
                            tuple(aimbot_cfg.get('hsv_lower', [0,120,70])),
                            tuple(aimbot_cfg.get('hsv_upper', [10,255,255]))
                        ),
                        smooth_factor=aimbot_cfg.get('smooth_factor', 0.2),
                        activation_key=aimbot_cfg.get('activation_key', 'alt_l')
                    )
                    logging.info("Aimbot worker loaded")
                except ImportError:
                    logging.info("Aimbot worker not available (import failed)")
                except Exception as e:
                    logging.warning(f"Aimbot worker init failed: {e}")
                
                logging.debug("Workers initialized from config")
            except ImportError as e :
                logging.error(f"Failed to import worker: {e}")
                raise
            except Exception as e :
                logging.error(f"Worker initialization failed: {e}")
                raise

    def _register_resource_callbacks(self) -> None :
        # Example: ScreenCapturer not directly a worker here, but inside AimbotWorker.
        # For now, we can register a callback that updates screen_capturer if aimbot exists.
        def on_resource_update(changes) :
            if 'target_fps' in changes and 'aimbot' in self.worker_instances :
                # Update screen capturer inside aimbot
                aimbot = self.worker_instances['aimbot']
                if hasattr(aimbot, 'capturer') and hasattr(aimbot.capturer, 'update_fps'):
                    aimbot.capturer.update_fps(changes['target_fps'])
        self.resource_manager.register_callback(on_resource_update)
    
    def start_worker(self, worker_name: str) -> bool :
        with self._lock :
            if worker_name not in self.workers :
                logging.error(f"Worker '{worker_name}' not found")
                return False
            if self.thread_manager.is_worker_running(worker_name) :
                logging.warning(f"Worker '{worker_name}' already running")
                return False
            worker = self.workers[worker_name]
            success = self.thread_manager.start_worker(worker_name, worker)
            if success :
                self.worker_instances[worker_name] = worker
                logging.info(f"Worker '{worker_name}' started")
            else :
                logging.error(f"Failed to start worker '{worker_name}'")
            return success
    
    def stop_worker(self, worker_name: str) -> bool :
        with self._lock :
            if worker_name not in self.worker_instances :
                logging.warning(f"Worker '{worker_name}' not active")
                return False
            success = self.thread_manager.stop_worker(worker_name)
            if success :
                self.worker_instances.pop(worker_name, None)
                logging.info(f"Worker '{worker_name}' stopped")
            else :
                logging.warning(f"Worker '{worker_name}' stop failed")
            return success
    
    def is_worker_running(self, worker_name: str) -> bool :
        return self.thread_manager.is_worker_running(worker_name)
    
    def pause_worker(self, worker_name: str) -> bool :
        return self.thread_manager.pause_worker(worker_name)
    
    def resume_worker(self, worker_name: str) -> bool :
        return self.thread_manager.resume_worker(worker_name)
    
    def stop_all(self) -> None :
        with self._lock :
            logging.info("Stopping all workers")
            self.thread_manager.stop_all()
            self.worker_instances.clear()
            self.resource_manager.stop()
            logging.info("All workers stopped")