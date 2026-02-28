#   src/workers/screen_capturer.py
#   Screen capturer using dxcam (passive)

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
from .function_worker import BaseWorker

# ----- Main Class ----- #
class ScreenCapturer(BaseWorker) :
    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None, target_fps: int = 60) :
        super().__init__()
        self.region = region
        self.target_fps = target_fps
        self.camera = None
        self.frame_buffer = None
        self.frame_lock = threading.Lock()
        self.frame_ready = threading.Event()
        self._setup_camera()
    
    def _setup_camera(self) -> None :
        if not DXCAM_AVAILABLE :
            logging.error("dxcam not available")
            return
        try :
            self.camera = dxcam.create(region=self.region)
            if self.camera is None :
                logging.error("Failed to create dxcam camera")
                return
            logging.info(f"Screen capturer initialized - Region: {self.region}, FPS: {self.target_fps}")
        except Exception as e :
            logging.error(f"Camera setup failed: {e}")
            self.camera = None
    
    def _work_cycle(self) -> None :
        # Called repeatedly. Get latest frame and store
        if self.camera is None :
            time.sleep(0.1)
            return
        # In passive mode, we rely on camera's internal thread; we just fetch.
        frame = self.camera.get_latest_frame()
        if frame is not None :
            with self.frame_lock :
                self.frame_buffer = frame.copy()
            self.frame_ready.set()
        # No sleep needed; BaseWorker will sleep if cycle too fast.
    
    def run(self, stop_event: threading.Event, pause_event: threading.Event) -> None :
        # Start the camera and then run the base loop
        if self.camera is not None :
            self.camera.start(target_fps=self.target_fps, video_mode=False)
            logging.info("Screen capture started")
        try :
            super().run(stop_event, pause_event)
        finally :
            self._cleanup_camera()
    
    def get_latest_frame(self) -> Optional[np.ndarray] :
        with self.frame_lock :
            return self.frame_buffer.copy() if self.frame_buffer is not None else None
    
    def wait_for_frame(self, timeout: float = 1.0) -> bool :
        return self.frame_ready.wait(timeout=timeout)
    
    def _cleanup_camera(self) -> None :
        if self.camera is not None :
            try :
                self.camera.stop()
            except Exception as e :
                logging.debug(f"Camera cleanup warning: {e}")
    
    def _cleanup(self) -> None :
        self._cleanup_camera()
    
    def update_fps(self, new_fps: int) -> None :
        # Called by resource manager to adjust capture rate
        if new_fps != self.target_fps :
            self.target_fps = new_fps
            logging.info(f"Screen capturer FPS updated to {new_fps}")
            # In practice, dxcam doesn't support dynamic FPS change without restart.
            # We could restart the camera, but that's heavy. For placeholder, just log.