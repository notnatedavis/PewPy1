#   pewpy/detection/target_detector.py
#   OpenCV target detection with GPU acceleration, confidence filtering,
#   outline mode, and mask access for debug preview.
#   Now returns the contour points for target outline rendering.

# ----- Imports ----- #
import cv2
import numpy as np
import logging
import threading
from typing import Optional, Tuple, Dict, Any, List

# ----- Main Class ----- #
class TargetDetector:
    """Target detection using OpenCV with HSV color filtering.
    Supports two modes:
    - normal : uses contour area and confidence threshold (good for solid blobs)
    - outline : bypasses confidence, automatically uses full S/V range and
                a very small minimum area to capture thin borders (hollow targets)

    New: returns contour points of the best target for real-time outline rendering.
    """

    def __init__(self, 
                 lower_hsv: Tuple[int, int, int] = (0, 120, 70),
                 upper_hsv: Tuple[int, int, int] = (10, 255, 255),
                 min_area: int = 50,
                 max_area: int = 50000,
                 min_confidence: float = 0.8,
                 min_area_outline: int = 10):
        self.lower_hsv = np.array(lower_hsv, dtype=np.uint8)
        self.upper_hsv = np.array(upper_hsv, dtype=np.uint8)
        self.min_area = min_area
        self.max_area = max_area
        self.min_confidence = min_confidence

        # Outline detection mode (thin borders)
        self.outline_mode = False
        self.min_area_outline = min_area_outline

        # Detection state
        self.detection_result: Optional[Dict[str, Any]] = None
        self.result_lock = threading.Lock()

        # Mask for debug preview
        self.latest_mask: Optional[np.ndarray] = None
        self.mask_lock = threading.Lock()

        # Reusable buffers for performance
        self.hsv_buffer = None
        self.mask_buffer = None

        # GPU acceleration
        self.gpu_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if self.gpu_available:
            logging.info("GPU acceleration available for target detection")
            try:
                self.gpu_stream = cv2.cuda_Stream()
            except Exception as e:
                logging.warning(f"GPU stream creation failed: {e}")
                self.gpu_available = False
        else:
            logging.info("Using CPU for target detection")

    def detect_targets(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """Detect targets in a frame and return detection results,
        filtered according to the active mode (normal or outline).
        The result now includes a 'contour' key with the raw contour points."""
        if frame is None:
            logging.debug("TargetDetector: frame is None")
            return None

        logging.debug(f"TargetDetector: processing frame shape={frame.shape} (outline_mode={self.outline_mode})")
        try:
            if self.gpu_available:
                result, mask = self._gpu_detection(frame)
            else:
                result, mask = self._cpu_detection(frame)

            with self.result_lock:
                self.detection_result = result
            with self.mask_lock:
                self.latest_mask = mask

            if result:
                pts_count = len(result.get('contour', []))
                logging.debug(f"TargetDetector: detection result -> contour points: {pts_count}, center: {result.get('center')}")
            else:
                logging.debug("TargetDetector: no detection result")

            return result

        except Exception as e:
            logging.error(f"Target detection error: {e}", exc_info=True)
            return None

    def _cpu_detection(self, frame: np.ndarray) -> Tuple[Optional[Dict[str, Any]], Optional[np.ndarray]]:
        # CPU-based target detection
        if self.hsv_buffer is None or self.hsv_buffer.shape != frame.shape:
            self.hsv_buffer = np.empty_like(frame)
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, dst=self.hsv_buffer)

        # --- In outline mode, use full S/V range so only hue matters ---
        lower = self.lower_hsv.copy()
        upper = self.upper_hsv.copy()
        if self.outline_mode:
            lower[1] = 0     # saturation
            lower[2] = 0     # value
            upper[1] = 255
            upper[2] = 255

        if self.mask_buffer is None or self.mask_buffer.shape != frame.shape[:2]:
            self.mask_buffer = np.empty(frame.shape[:2], dtype=np.uint8)
        mask = cv2.inRange(hsv_frame, lower, upper, dst=self.mask_buffer)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        return self._process_contours(contours, frame.shape), mask.copy()

    def _gpu_detection(self, frame: np.ndarray) -> Tuple[Optional[Dict[str, Any]], Optional[np.ndarray]]:
        # GPU-accelerated target detection
        try:
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame, stream=self.gpu_stream)

            gpu_hsv = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2HSV, stream=self.gpu_stream)

            # Same S/V override for outline mode
            lower = self.lower_hsv.copy()
            upper = self.upper_hsv.copy()
            if self.outline_mode:
                lower[1] = 0
                lower[2] = 0
                upper[1] = 255
                upper[2] = 255

            gpu_mask = cv2.cuda.inRange(gpu_hsv, lower, upper, stream=self.gpu_stream)
            cpu_mask = gpu_mask.download(stream=self.gpu_stream)
            self.gpu_stream.waitForCompletion()

            contours, _ = cv2.findContours(cpu_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return self._process_contours(contours, frame.shape), cpu_mask.copy()
        except Exception as e:
            logging.warning(f"GPU detection failed, falling back to CPU: {e}")
            return self._cpu_detection(frame)

    def _process_contours(self, contours: list, frame_shape: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """Process contours according to the active detection mode.
        - Normal mode: picks the contour with highest confidence that meets
          area and confidence thresholds, and returns its contour points.
        - Outline mode: picks the largest contour by area (above a tiny
          minimum) and returns its bounding box center; confidence is ignored.
        Both modes now include the raw contour points as a list of (x,y) tuples."""

        if not contours:
            logging.debug("TargetDetector: No contours found")
            return None

        frame_h, frame_w = frame_shape[:2]

        if self.outline_mode:
            # ---- Outline mode: simple area filter with very low threshold ----
            min_area_eff = max(1, self.min_area_outline)
            best_area = -1
            best_bbox = None
            best_contour = None
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area_eff:
                    continue
                if area > self.max_area:
                    continue
                if area > best_area:
                    best_area = area
                    x, y, w, h = cv2.boundingRect(cnt)
                    best_bbox = (x, y, w, h)
                    best_contour = cnt

            if best_bbox is None:
                logging.debug(f"TargetDetector (outline): No contour passed area filter (min={min_area_eff})")
                return None

            x, y, w, h = best_bbox
            cx = x + w // 2
            cy = y + h // 2
            screen_x = cx / frame_w
            screen_y = cy / frame_h

            # Convert contour to list of (x,y) ints
            contour_points = [(int(pt[0][0]), int(pt[0][1])) for pt in best_contour] if best_contour is not None else []
            logging.debug(f"TargetDetector (outline): contour pts={len(contour_points)}, bbox={best_bbox}, center=({cx},{cy})")

            result = {
                'center': (cx, cy),
                'bounding_box': (x, y, w, h),
                'confidence': 1.0,
                'screen_position': (screen_x, screen_y),
                'contour': contour_points
            }
            return result

        else:
            # ---- Normal mode: confidence + area ----
            best_result = None
            best_confidence = -1.0
            best_contour = None

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < self.min_area:
                    continue
                if area > self.max_area:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                bbox_area = w * h
                if bbox_area == 0:
                    continue
                confidence = area / bbox_area
                if confidence < self.min_confidence:
                    continue
                if confidence > best_confidence:
                    best_confidence = confidence
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx, cy = x + w // 2, y + h // 2

                    screen_x = cx / frame_w
                    screen_y = cy / frame_h

                    best_result = {
                        'center': (cx, cy),
                        'bounding_box': (x, y, w, h),
                        'confidence': confidence,
                        'screen_position': (screen_x, screen_y),
                        'contour': []  # will fill after loop
                    }
                    best_contour = cnt

            if best_result is not None and best_contour is not None:
                contour_points = [(int(pt[0][0]), int(pt[0][1])) for pt in best_contour]
                best_result['contour'] = contour_points
                logging.debug(f"TargetDetector (normal): contour pts={len(contour_points)}, center=({best_result['center']})")
            elif best_result is not None:
                logging.debug("TargetDetector (normal): no contour stored")

            if best_result is None:
                logging.debug("TargetDetector (normal): No contour passed all filters")

            return best_result

    def get_latest_detection(self) -> Optional[Dict[str, Any]]:
        with self.result_lock:
            return self.detection_result.copy() if self.detection_result is not None else None

    def get_latest_mask(self) -> Optional[np.ndarray]:
        """Return the latest binary mask (grayscale) for debug preview."""
        with self.mask_lock:
            return self.latest_mask.copy() if self.latest_mask is not None else None

    def set_hsv_range(self, lower_hsv: Tuple[int, int, int], upper_hsv: Tuple[int, int, int]) -> None:
        self.lower_hsv = np.array(lower_hsv, dtype=np.uint8)
        self.upper_hsv = np.array(upper_hsv, dtype=np.uint8)
        logging.info(f"HSV range updated: {lower_hsv} -> {upper_hsv}")

    def set_area_limits(self, min_area: int, max_area: int) -> None:
        self.min_area = min_area
        self.max_area = max_area
        logging.info(f"Area limits updated: {min_area} - {max_area}")

    def set_confidence(self, confidence: float) -> None:
        """Set minimum confidence threshold (0.0-1.0)."""
        self.min_confidence = max(0.0, min(1.0, confidence))
        logging.info(f"Confidence threshold set to {self.min_confidence:.2f}")

    def set_outline_mode(self, enabled: bool) -> None:
        self.outline_mode = enabled
        if enabled:
            self.min_area_outline = 1
        logging.info(f"Outline detection mode {'enabled' if enabled else 'disabled'} "
                     f"(min_area_outline={self.min_area_outline})")

    def set_min_area_outline(self, area: int) -> None:
        self.min_area_outline = max(1, area)
        logging.info(f"Outline min area set to {self.min_area_outline}")