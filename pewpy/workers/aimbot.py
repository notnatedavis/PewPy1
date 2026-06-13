#   pewpy/workers/aimbot.py
#   Aimbot worker (passive) coordinating capture, detection, mouse.
#   Now passes target contour to overlay for real‑time outline rendering.
#   Also sends detection debug info to UI queue.

# ----- Imports ----- #
import threading
import time
import logging
from typing import Optional, Tuple, Dict, Any
import numpy as np
try:
    import pynput
    from pynput.mouse import Button, Controller as MouseController
    from pynput.keyboard import Key, Listener as KeyboardListener, KeyCode
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available - aimbot mouse/keyboard control disabled")
from .base import BaseWorker
from ..capture.dxcam_capturer import ScreenCapturer
from ..detection.target_detector import TargetDetector
from ..communication.overlay_bridge import OverlayData

# ----- Main Class ----- #
class AimbotWorker(BaseWorker):
    """Aimbot: captures screen, detects targets, moves mouse.
    Activation key toggles the aiming on/off while the worker is running.
    ROI mode restricts detection to a circular area around the mouse cursor.
    Target contour data is sent to the overlay bridge for real‑time outline rendering.
    Debug info (HSV bounds, detection status) is sent to the UI queue every ~0.5s.
    """

    def __init__(self, 
                 capture_region: Optional[Tuple[int, int, int, int]] = None,
                 target_fps: int = 60,
                 hsv_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = ((0, 120, 70), (10, 255, 255)),
                 smooth_factor: float = 0.2,
                 activation_key: str = 'alt_l',
                 overlay_data: Optional[OverlayData] = None,
                 debug_queue: Optional[queue.Queue] = None) -> None:
        super().__init__()
        self.capture_region = capture_region
        self.target_fps = target_fps
        self.smooth_factor = max(0.01, min(1.0, smooth_factor))
        self.activation_key = activation_key
        self.overlay_data = overlay_data
        self.debug_queue = debug_queue   # UI queue for debug messages

        self.roi_enabled = False
        self.roi_radius = 150

        self.capturer = ScreenCapturer(region=capture_region, target_fps=target_fps)
        self.detector = TargetDetector(lower_hsv=hsv_range[0], upper_hsv=hsv_range[1])
        self.mouse = MouseController() if PYNPUT_AVAILABLE else None

        self._aiming_enabled = threading.Event()

        self.last_target_pos: Optional[Tuple[float, float]] = None
        self.state_lock = threading.RLock()
        self.frame_count = 0
        self.detection_count = 0

        self._keyboard_listener: Optional[KeyboardListener] = None
        self._keyboard_lock = threading.Lock()

        self._screen_width = 1920
        self._screen_height = 1080

        # Debug throttling
        self._last_debug_time = 0.0
        self._debug_interval = 0.5  # seconds

        logging.info(f"Aimbot initialized - Region: {capture_region}, FPS: {target_fps}")

    def _on_key_press(self, key) -> None:
        try:
            target = self.activation_key
            if isinstance(key, Key):
                if str(key) == target:
                    self._toggle_aiming()
            elif isinstance(key, KeyCode):
                if key.char == target:
                    self._toggle_aiming()
        except Exception as e:
            logging.error(f"Key press handler error: {e}")

    def _toggle_aiming(self) -> None:
        if self._aiming_enabled.is_set():
            self._aiming_enabled.clear()
            logging.info("Aiming DISABLED by activation key")
        else:
            self._aiming_enabled.set()
            logging.info("Aiming ENABLED by activation key")

    def _start_keyboard_listener(self) -> None:
        if not PYNPUT_AVAILABLE:
            return
        with self._keyboard_lock:
            if self._keyboard_listener and self._keyboard_listener.running:
                return
            self._keyboard_listener = KeyboardListener(on_press=self._on_key_press)
            self._keyboard_listener.start()
            logging.info(f"Keyboard listener started (key={self.activation_key})")

    def _stop_keyboard_listener(self) -> None:
        with self._keyboard_lock:
            if self._keyboard_listener and self._keyboard_listener.running:
                self._keyboard_listener.stop()
                self._keyboard_listener = None
                logging.info("Keyboard listener stopped")

    def _work_cycle(self) -> None:
        if not PYNPUT_AVAILABLE:
            return
        if self.capturer.wait_for_frame(timeout=0.001):
            self._process_frame()

    def _process_frame(self) -> None:
        frame = self.capturer.get_latest_frame()
        if frame is None:
            logging.debug("Aimbot: no frame available")
            return
        self.frame_count += 1

        roi_enabled = self.roi_enabled
        roi_offset = (0, 0)
        detection_frame = frame
        if roi_enabled and self.mouse is not None:
            mouse_x, mouse_y = self.mouse.position
            mouse_x = max(0, min(frame.shape[1] - 1, mouse_x))
            mouse_y = max(0, min(frame.shape[0] - 1, mouse_y))
            radius = self.roi_radius
            x1 = max(0, mouse_x - radius)
            y1 = max(0, mouse_y - radius)
            x2 = min(frame.shape[1], mouse_x + radius)
            y2 = min(frame.shape[0], mouse_y + radius)
            if x2 > x1 and y2 > y1:
                detection_frame = frame[y1:y2, x1:x2]
                roi_offset = (x1, y1)
                logging.debug(f"Aimbot: ROI active, mouse=({mouse_x},{mouse_y}), ROI region=({x1},{y1})-({x2},{y2})")
            else:
                detection_frame = None
                logging.debug("Aimbot: ROI region invalid, skipping detection")

        detection = None
        best_candidate = None
        if detection_frame is not None:
            detection = self.detector.detect_targets(detection_frame)
            best_candidate = self.detector.get_best_candidate()   # get candidate for debug
            if detection is not None:
                logging.debug(f"Aimbot: Detection found! Confidence={detection.get('confidence',0):.2f}, center={detection['center']}, contour pts={len(detection.get('contour', []))}")
                if roi_offset != (0,0):
                    center_abs = (detection['center'][0] + roi_offset[0], detection['center'][1] + roi_offset[1])
                    detection['center'] = center_abs
                    # Adjust bounding box
                    detection['bounding_box'] = (detection['bounding_box'][0] + roi_offset[0],
                                                 detection['bounding_box'][1] + roi_offset[1],
                                                 detection['bounding_box'][2],
                                                 detection['bounding_box'][3])
                    detection['screen_position'] = (center_abs[0] / self._screen_width,
                                                    center_abs[1] / self._screen_height)
                    # Adjust contour points
                    if 'contour' in detection and detection['contour']:
                        adjusted_contour = [(px + roi_offset[0], py + roi_offset[1]) for px, py in detection['contour']]
                        detection['contour'] = adjusted_contour
                        logging.debug(f"Aimbot: Adjusted contour to absolute coordinates, first point: {adjusted_contour[0] if adjusted_contour else 'N/A'}")
                    logging.debug(f"Aimbot: Converted to absolute center={center_abs}")
            else:
                logging.debug("Aimbot: No target detected in current frame")

        mask = self.detector.get_latest_mask()

        if self.overlay_data is not None:
            data_to_send = {}
            if detection is not None:
                self.detection_count += 1
                data_to_send = {
                    'target': detection['screen_position'],
                    'target_center': detection['center'],
                    'bbox': detection['bounding_box'],
                    'frame_dims': (self._screen_width, self._screen_height),
                    'target_contour': detection.get('contour', None)
                }
                if data_to_send.get('target_contour'):
                    logging.debug(f"Aimbot: sending contour with {len(data_to_send['target_contour'])} points to overlay")
                else:
                    logging.debug("Aimbot: no contour to send (none in detection)")
            else:
                data_to_send = {'target': None, 'target_center': None, 'bbox': None, 'target_contour': None}
            if mask is not None:
                data_to_send['mask'] = mask
            self.overlay_data.update(data_to_send)

        # Send debug info to UI (throttled)
        if self.debug_queue is not None:
            now = time.time()
            if now - self._last_debug_time >= self._debug_interval:
                self._last_debug_time = now
                debug_data = self._collect_debug_info(detection, best_candidate)
                try:
                    self.debug_queue.put_nowait({'type': 'detection_debug', 'data': debug_data})
                except queue.Full:
                    pass  # drop update if queue is full

        if detection is not None and self._aiming_enabled.is_set():
            self._aim_at_target(detection)

    def _collect_debug_info(self, detection: Optional[Dict], best_candidate: Optional[Dict]) -> Dict:
        """Collect current HSV bounds (user-friendly), detection status, and candidate info."""
        # Convert OpenCV HSV (0-179,0-255,0-255) to user-friendly (0-360,0-100,0-100)
        lower_cv = self.detector.lower_hsv
        upper_cv = self.detector.upper_hsv
        lower_user = (int(lower_cv[0] * 2), int(lower_cv[1] / 255 * 100), int(lower_cv[2] / 255 * 100))
        upper_user = (int(upper_cv[0] * 2), int(upper_cv[1] / 255 * 100), int(upper_cv[2] / 255 * 100))

        info = {
            'hsv_lower_user': lower_user,
            'hsv_upper_user': upper_user,
            'target_detected': detection is not None,
        }
        if detection is not None:
            info['center'] = detection.get('center')
            info['confidence'] = detection.get('confidence')
            info['contour_points'] = len(detection.get('contour', []))
        else:
            # Provide best candidate if available
            if best_candidate is not None:
                info['candidate_center'] = best_candidate.get('center')
                info['candidate_confidence'] = best_candidate.get('confidence')
            else:
                info['candidate_center'] = None
                info['candidate_confidence'] = None
        return info

    def _aim_at_target(self, detection: Dict[str, Any]) -> None:
        if self.mouse is None:
            return
        try:
            screen_x, screen_y = detection['screen_position']
            target_x = int(screen_x * self._screen_width)
            target_y = int(screen_y * self._screen_height)
            current_x, current_y = self.mouse.position
            if self.last_target_pos:
                last_x, last_y = self.last_target_pos
                smoothed_x = last_x + (target_x - last_x) * self.smooth_factor
                smoothed_y = last_y + (target_y - last_y) * self.smooth_factor
            else:
                smoothed_x = current_x + (target_x - current_x) * self.smooth_factor
                smoothed_y = current_y + (target_y - current_y) * self.smooth_factor
            self.mouse.position = (int(smoothed_x), int(smoothed_y))
            self.last_target_pos = (smoothed_x, smoothed_y)
            if self.overlay_data is not None:
                self.overlay_data.update({'mouse_pos': (int(smoothed_x), int(smoothed_y))})
        except Exception as e:
            logging.error(f"Mouse movement error: {e}")

    def set_smooth_factor(self, factor: float) -> None:
        with self.state_lock:
            self.smooth_factor = max(0.01, min(1.0, factor))

    def set_hsv_range(self, lower, upper):
        self.detector.set_hsv_range(lower, upper)

    def set_capture_region(self, region):
        self.capture_region = region

    def set_activation_key(self, key: str) -> None:
        with self.state_lock:
            self.activation_key = key
        logging.info(f"Aimbot activation key set to: {key}")
        if self._keyboard_listener and self._keyboard_listener.running:
            self._stop_keyboard_listener()
            self._start_keyboard_listener()

    def set_confidence(self, confidence: float) -> None:
        self.detector.set_confidence(confidence)

    def set_roi_enabled(self, enabled: bool) -> None:
        self.roi_enabled = enabled
        logging.info(f"ROI detection {'enabled' if enabled else 'disabled'}")

    def set_roi_radius(self, radius: int) -> None:
        self.roi_radius = max(20, min(500, radius))
        logging.info(f"ROI radius set to {self.roi_radius} px")

    def set_outline_mode(self, enabled: bool) -> None:
        self.detector.set_outline_mode(enabled)
        logging.info(f"Outline detection mode {'enabled' if enabled else 'disabled'}")

    def run(self, stop_event: threading.Event, pause_event: threading.Event) -> None:
        self.capturer.start()
        if self.capturer.camera is not None:
            try:
                out = self.capturer.camera.output
                if out is not None:
                    self._screen_width = out.width
                    self._screen_height = out.height
                else:
                    if self.capture_region:
                        self._screen_width = self.capture_region[2]
                        self._screen_height = self.capture_region[3]
                    else:
                        from ctypes import windll
                        user32 = windll.user32
                        self._screen_width = user32.GetSystemMetrics(0)
                        self._screen_height = user32.GetSystemMetrics(1)
                    logging.warning(f"Camera output was None, using fallback dimensions: {self._screen_width}x{self._screen_height}")
            except Exception as e:
                logging.warning(f"Failed to get screen dimensions from camera: {e}. Using default {self._screen_width}x{self._screen_height}")
        self._start_keyboard_listener()
        try:
            super().run(stop_event, pause_event)
        finally:
            self._stop_keyboard_listener()
            self.capturer.stop()

    def _cleanup(self) -> None:
        self._stop_keyboard_listener()
        self.capturer.stop()
        logging.debug("Aimbot cleaned up")