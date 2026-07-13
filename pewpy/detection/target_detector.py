#   pewpy/detection/target_detector.py
#   OpenCV target detection with GPU acceleration, confidence filtering,
#   outline mode, and mask access for debug preview.
#   Now returns the contour points for target outline rendering.
#   Also returns the best candidate contour (highest confidence regardless of threshold).
#   Added "avoid colors" feature: list of HSV ranges that will be masked out.

# ----- Imports ----- #
import cv2
import numpy as np
import logging
import threading
from typing import Optional, Tuple, Dict, Any, List
from pewpy.utils.color import user_hsv_to_opencv

# ----- Main Class ----- #
class TargetDetector:
    """Target detection using OpenCV with HSV color filtering.
    Supports two modes:
    - normal : uses contour area and confidence threshold (good for solid blobs)
    - outline : bypasses confidence, automatically uses full S/V range and
                a very small minimum area to capture thin borders (hollow targets)

    New: returns contour points of the best target for real-time outline rendering.
    Also returns the best candidate contour (highest confidence) for debug purposes.
    Added: avoid_colors – list of (lower_hsv, upper_hsv) tuples that will be
    excluded from detection.
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

        # Avoid colors: list of (lower, upper) in OpenCV HSV space
        self.avoid_colors: List[Tuple[np.ndarray, np.ndarray]] = []
        self._avoid_lock = threading.Lock()

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

    # ----- Public avoid color management -----
    def add_avoid_color(self, h_center: int, s_pct: int, v_pct: int,
                        hue_tol: int = 5, sat_tol: int = 20, val_tol: int = 20) -> None:
        """
        Add an HSV colour to the avoid list.
        Parameters are in user-friendly scale: H 0-360°, S 0-100%, V 0-100%.
        A tolerance (hue_tol in degrees, sat_tol/val_tol in percentage points) is applied
        to create a small range around the given centre.
        """
        # Convert to OpenCV scale using utility
        h_cv, s_cv, v_cv = user_hsv_to_opencv(h_center, s_pct, v_pct)

        # Tolerances in OpenCV units
        h_tol_cv = max(1, hue_tol // 2)   # because 1° = 0.5 in OpenCV H
        s_tol_cv = int(sat_tol * 255 / 100)
        v_tol_cv = int(val_tol * 255 / 100)

        lower = np.array([max(0, h_cv - h_tol_cv),
                          max(0, s_cv - s_tol_cv),
                          max(0, v_cv - v_tol_cv)], dtype=np.uint8)
        upper = np.array([min(179, h_cv + h_tol_cv),
                          min(255, s_cv + s_tol_cv),
                          min(255, v_cv + v_tol_cv)], dtype=np.uint8)

        with self._avoid_lock:
            self.avoid_colors.append((lower, upper))
        logging.info(f"Avoid color added: center=({h_center}°, {s_pct}%, {v_pct}%) -> "
                     f"range=({lower[0]}-{upper[0]}, {lower[1]}-{upper[1]}, {lower[2]}-{upper[2]})")

    def remove_avoid_color(self, index: int) -> bool:
        """Remove an avoid color by its index in the list."""
        with self._avoid_lock:
            if 0 <= index < len(self.avoid_colors):
                self.avoid_colors.pop(index)
                logging.info(f"Avoid color removed (index {index})")
                return True
        return False

    def clear_avoid_colors(self) -> None:
        """Remove all avoid colors."""
        with self._avoid_lock:
            self.avoid_colors.clear()
        logging.info("All avoid colors cleared")

    def get_avoid_colors(self) -> List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
        """Return a copy of the avoid colours in user-friendly HSV format for display.
        Converts stored numpy uint8 values to Python int before arithmetic to avoid overflow."""
        result = []
        with self._avoid_lock:
            for lower, upper in self.avoid_colors:
                # Convert OpenCV ranges back to user-friendly (approx)
                # Convert to Python int first to prevent uint8 overflow
                h_low = int(lower[0]) * 2
                h_high = int(upper[0]) * 2
                s_low = int(lower[1]) * 100 // 255
                s_high = int(upper[1]) * 100 // 255
                v_low = int(lower[2]) * 100 // 255
                v_high = int(upper[2]) * 100 // 255
                result.append(((h_low, s_low, v_low), (h_high, s_high, v_high)))
        return result

    # ----- Core detection (modified to incorporate avoid mask) -----
    def detect_targets(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """Detect targets in a frame and return detection results,
        filtered according to the active mode (normal or outline).
        The result now includes a 'contour' key with the raw contour points.
        Also stores the best candidate (highest confidence regardless of threshold)
        internally for debug access.
        """
        if frame is None:
            logging.debug("TargetDetector: frame is None")
            return None

        logging.debug(f"TargetDetector: processing frame shape={frame.shape} (outline_mode={self.outline_mode})")
        try:
            if self.gpu_available:
                result, mask, best_candidate = self._gpu_detection(frame)
            else:
                result, mask, best_candidate = self._cpu_detection(frame)

            with self.result_lock:
                self.detection_result = result
                self._best_candidate = best_candidate   # store for debug
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

    def _apply_avoid_mask(self, base_mask: np.ndarray, hsv_frame: np.ndarray) -> np.ndarray:
        """Subtract any pixels that fall into any of the avoid color ranges."""
        if not self.avoid_colors:
            return base_mask

        combined_avoid_mask = np.zeros(base_mask.shape, dtype=np.uint8)
        with self._avoid_lock:
            # Copy avoid list to avoid holding lock while doing OpenCV ops
            avoid_list = list(self.avoid_colors)

        for lower, upper in avoid_list:
            try:
                avoid_part = cv2.inRange(hsv_frame, lower, upper)
                combined_avoid_mask = cv2.bitwise_or(combined_avoid_mask, avoid_part)
            except Exception as e:
                logging.error(f"Failed to generate avoid mask for range {lower}-{upper}: {e}")

        # Subtract from base mask
        final_mask = cv2.bitwise_and(base_mask, cv2.bitwise_not(combined_avoid_mask))
        return final_mask

    def _cpu_detection(self, frame: np.ndarray) -> Tuple[Optional[Dict[str, Any]], Optional[np.ndarray], Optional[Dict[str, Any]]]:
        # CPU-based target detection
        if self.hsv_buffer is None or self.hsv_buffer.shape != frame.shape:
            self.hsv_buffer = np.empty_like(frame)
        # Use RGB2HSV because capturer now outputs RGB
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV, dst=self.hsv_buffer)

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
        base_mask = cv2.inRange(hsv_frame, lower, upper, dst=self.mask_buffer)

        # Apply avoid colors if any
        mask = self._apply_avoid_mask(base_mask, hsv_frame)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        result, best_candidate = self._process_contours(contours, frame.shape)
        return result, mask.copy(), best_candidate

    def _gpu_detection(self, frame: np.ndarray) -> Tuple[Optional[Dict[str, Any]], Optional[np.ndarray], Optional[Dict[str, Any]]]:
        # GPU-accelerated target detection (with avoid mask on CPU after download)
        try:
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame, stream=self.gpu_stream)

            # Use RGB2HSV
            gpu_hsv = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_RGB2HSV, stream=self.gpu_stream)

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

            # Apply avoid mask on CPU (simpler than implementing GPU merging)
            # Recreate hsv frame for avoid mask using RGB2HSV
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            final_mask = self._apply_avoid_mask(cpu_mask, hsv_frame)

            contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            result, best_candidate = self._process_contours(contours, frame.shape)
            return result, final_mask.copy(), best_candidate
        except Exception as e:
            logging.warning(f"GPU detection failed, falling back to CPU: {e}")
            return self._cpu_detection(frame)

    # ----- The rest of the class (unchanged) -----
    def _process_contours(self, contours: list, frame_shape: Tuple[int, int]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Process contours according to the active detection mode.
        Returns:
            - result: the best detection that meets confidence/area thresholds (or outline mode)
            - best_candidate: the contour with highest confidence (regardless of threshold) for debug
        """
        if not contours:
            logging.debug("TargetDetector: No contours found")
            return None, None

        frame_h, frame_w = frame_shape[:2]

        # First, evaluate all contours and track the best candidate (highest confidence)
        best_candidate = None
        best_confidence = -1.0
        best_result = None

        if self.outline_mode:
            # ---- Outline mode: simple area filter with very low threshold ----
            min_area_eff = max(1, self.min_area_outline)
            best_area = -1
            best_bbox = None
            best_contour = None
            best_candidate_contour = None   # same as best in outline mode
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area_eff:
                    continue
                if area > self.max_area:
                    continue
                # track best candidate (largest area)
                if area > best_area:
                    best_area = area
                    x, y, w, h = cv2.boundingRect(cnt)
                    best_bbox = (x, y, w, h)
                    best_contour = cnt
                    best_candidate_contour = cnt

            if best_bbox is None:
                logging.debug(f"TargetDetector (outline): No contour passed area filter (min={min_area_eff})")
                return None, None

            x, y, w, h = best_bbox
            cx = x + w // 2
            cy = y + h // 2
            screen_x = cx / frame_w
            screen_y = cy / frame_h

            contour_points = [(int(pt[0][0]), int(pt[0][1])) for pt in best_contour] if best_contour is not None else []
            logging.debug(f"TargetDetector (outline): contour pts={len(contour_points)}, bbox={best_bbox}, center=({cx},{cy})")

            result = {
                'center': (cx, cy),
                'bounding_box': (x, y, w, h),
                'confidence': 1.0,
                'screen_position': (screen_x, screen_y),
                'contour': contour_points
            }
            # best_candidate is same as result in outline mode
            best_candidate = result.copy()
            return result, best_candidate

        else:
            # ---- Normal mode: confidence + area ----
            # First pass: find best candidate (highest confidence, ignoring min_confidence)
            best_candidate_conf = -1.0
            best_candidate_data = None

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < self.min_area or area > self.max_area:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                bbox_area = w * h
                if bbox_area == 0:
                    continue
                confidence = area / bbox_area
                if confidence > best_candidate_conf:
                    best_candidate_conf = confidence
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx, cy = x + w // 2, y + h // 2
                    best_candidate_data = {
                        'center': (cx, cy),
                        'bounding_box': (x, y, w, h),
                        'confidence': confidence,
                        'screen_position': (cx / frame_w, cy / frame_h),
                        'contour': cnt   # store raw contour for later conversion if needed
                    }

            # Second pass: find best result that meets threshold
            best_result_confidence = -1.0
            best_result_data = None
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < self.min_area or area > self.max_area:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                bbox_area = w * h
                if bbox_area == 0:
                    continue
                confidence = area / bbox_area
                if confidence < self.min_confidence:
                    continue
                if confidence > best_result_confidence:
                    best_result_confidence = confidence
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        cx, cy = x + w // 2, y + h // 2
                    best_result_data = {
                        'center': (cx, cy),
                        'bounding_box': (x, y, w, h),
                        'confidence': confidence,
                        'screen_position': (cx / frame_w, cy / frame_h),
                        'contour': cnt
                    }

            # Convert contours to point lists
            if best_result_data is not None:
                cnt = best_result_data['contour']
                contour_points = [(int(pt[0][0]), int(pt[0][1])) for pt in cnt]
                best_result_data['contour'] = contour_points
            if best_candidate_data is not None:
                cnt = best_candidate_data['contour']
                contour_points = [(int(pt[0][0]), int(pt[0][1])) for pt in cnt]
                best_candidate_data['contour'] = contour_points

            # Convert best_candidate to dict without raw contour for debug (already done)
            if best_result_data is None:
                logging.debug("TargetDetector (normal): No contour passed confidence threshold")
            if best_candidate_data is None:
                logging.debug("TargetDetector (normal): No candidate found at all")

            return best_result_data, best_candidate_data

    def get_latest_detection(self) -> Optional[Dict[str, Any]]:
        with self.result_lock:
            return self.detection_result.copy() if self.detection_result is not None else None

    def get_best_candidate(self) -> Optional[Dict[str, Any]]:
        """Return the best candidate contour (highest confidence regardless of threshold)."""
        with self.result_lock:
            return getattr(self, '_best_candidate', None)

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