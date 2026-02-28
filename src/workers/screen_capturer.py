#   src/workers/screen_capturer.py
#   DirectX screen capture for high-performance frame grabbing

# ----- Imports ----- #
import threading
import time
import logging
from typing import Optional, Tuple
import numpy as np

try:
    import dxcam
    DXCAM_AVAILABLE = True
except ImportError:
    DXCAM_AVAILABLE = False
    logging.warning("dxcam not available - screen capture disabled")

from workers.function_worker import BaseWorker

# ----- Main Class ----- #
class ScreenCapturer(BaseWorker) :
    # High-performance screen capturer using DirectX via dxcam
    
    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None, target_fps: int = 60):
        super().__init__()
        self.region = region
        self.target_fps = target_fps
        self.camera = None
        self.frame_buffer = None
        self.frame_lock = threading.Lock()
        self.frame_ready = threading.Event()
        self._setup_camera()
        
    def _setup_camera(self) -> None :
        # Initialize dxcam camera instance
        if not DXCAM_AVAILABLE :
            logging.error("dxcam not available - screen capture disabled")
            return
            
        try :
            self.camera = dxcam.create(region=self.region)
            if self.camera is None :
                logging.error("Failed to initialize dxcam camera")
                return
                
            logging.info(f"Screen capturer initialized - Region: {self.region}, FPS: {self.target_fps}")
        except Exception as e :
            logging.error(f"Failed to setup screen capturer: {e}")
            self.camera = None
    
    def _work(self) -> None :
        # Main capture loop - runs continuously until stop() is called
        if self.camera is None :
            logging.error("Screen capturer not available")
            return
            
        try :
            self.camera.start(target_fps=self.target_fps, video_mode=False)
            logging.info("Screen capture started")
            
            while self.running :
                # Get latest frame (non-blocking)
                frame = self.camera.get_latest_frame()
                
                if frame is not None :
                    with self.frame_lock:
                        self.frame_buffer = frame.copy()
                    self.frame_ready.set()
                    
                # Small sleep to prevent CPU spinning
                time.sleep(0.001)  # 1ms
                
        except Exception as e :
            logging.error(f"Screen capture error: {e}")
        finally :
            self._cleanup_camera()
            logging.info("Screen capture stopped")
    
    def get_latest_frame(self) -> Optional[np.ndarray] :
        # Get the latest captured frame (thread-safe)
        with self.frame_lock :
            return self.frame_buffer.copy() if self.frame_buffer is not None else None
    
    def wait_for_frame(self, timeout: float = 1.0) -> bool :
        # Wait for a new frame to be available
        return self.frame_ready.wait(timeout=timeout)
    
    def _cleanup_camera(self) -> None :
        # Cleanup camera resources
        if self.camera is not None :
            try :
                self.camera.stop()
            except Exception as e :
                logging.debug(f"Camera cleanup warning: {e}")