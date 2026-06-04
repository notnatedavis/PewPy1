#   src/capture/dxcam_capturer.py
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
from pewpy.workers.base import BaseWorker

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

        # Additional thread for continuous capture when using start/stop
        self._capture_thread = None
        self._capture_running = False

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

    # ------------------ New start / stop methods ------------------
    def start(self) -> None :
        """Start the dxcam camera and a background thread that continuously fetches frames."""
        if self.camera is None:
            logging.error("Cannot start screen capturer: camera not available")
            return
        self.camera.start(target_fps=self.target_fps, video_mode=False)
        self._capture_running = True
        self._capture_thread = threading.Thread(target=self._capture_loop,
                                                daemon=True,
                                                name="ScreenCapturerLoop")
        self._capture_thread.start()
        logging.info("Screen capture started (background thread)")

    def stop(self) -> None :
        """Stop the capture thread and the dxcam camera."""
        self._capture_running = False
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None
        if self.camera is not None:
            try:
                self.camera.stop()
            except Exception as e:
                logging.debug(f"Camera cleanup warning: {e}")
        logging.info("Screen capture stopped")

    def _capture_loop(self) -> None :
        """Continuously fetch frames from the camera in a background thread."""
        cycle_delay = 1.0 / max(self.target_fps, 1)   # respect target FPS
        while self._capture_running:
            try:
                frame = self.camera.get_latest_frame()
                if frame is not None:
                    with self.frame_lock:
                        self.frame_buffer = frame.copy()
                    self.frame_ready.set()
            except Exception as e:
                logging.error(f"Capture loop error: {e}")
            time.sleep(cycle_delay)

    # -----------------------------------------------------------------

    def _work_cycle(self) -> None :
        # Called repeatedly when the worker is used in full BaseWorker mode.
        # In that case the camera is already started by the run() method.
        if self.camera is None :
            time.sleep(0.1)
            return
        frame = self.camera.get_latest_frame()
        if frame is not None :
            with self.frame_lock :
                self.frame_buffer = frame.copy()
            self.frame_ready.set()

    def run(self, stop_event: threading.Event, pause_event: threading.Event) -> None :
        # Full worker mode (used by ThreadManager)
        if self.camera is not None :
            self.camera.start(target_fps=self.target_fps, video_mode=False)
            logging.info("Screen capture started (worker mode)")
        try :
            super().run(stop_event, pause_event)
        finally :
            self._cleanup_camera()

    def get_latest_frame(self) -> Optional[np.ndarray] :
        """Return the most recent frame and clear the ready signal."""
        with self.frame_lock :
            if self.frame_buffer is not None :
                frame = self.frame_buffer.copy()
                self.frame_ready.clear()
                return frame
        return None

    def wait_for_frame(self, timeout: float = 1.0) -> bool :
        """Block until a new frame has been captured."""
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
        if new_fps != self.target_fps :
            self.target_fps = new_fps
            logging.info(f"Screen capturer FPS updated to {new_fps}")
            # A running capture will respect the new target_fps only on the next start.