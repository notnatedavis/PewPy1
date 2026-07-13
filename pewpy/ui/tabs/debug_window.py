# pewpy/ui/tabs/debug_window.py
# Debug console window with live logs, detection debug, hue detection and avoid colors

# ----- Imports -----
import customtkinter as ctk
import logging
import threading
import time
import tkinter as tk
from datetime import datetime
import queue
import numpy as np
import cv2
try :
    import dxcam
except ImportError :
    dxcam = None
    logging.warning("dxcam not available – Hue Detection tab will not work")
from pewpy.utils.color import opencv_hsv_to_user, user_hsv_to_opencv, user_hsv_to_rgb_hex

# ----- Custom Logging Handler for Debug Window -----
class DebugWindowHandler(logging.Handler):
    # Forward log records to the debug window via the UI queue
    def __init__(self, ui_queue) :
        super().__init__()
        self.ui_queue = ui_queue
        self.setLevel(logging.DEBUG)

    def emit(self, record) :
        try :
            msg = self.format(record)
            self.ui_queue.put_nowait({'type': 'debug_log', 'log': msg})
        except Exception :
            pass  # avoid recursion

# ----- Main Debug Window -----
class DebugWindow(ctk.CTkToplevel) :
    # Standalone window that displays live diagnostics, logs, detection debug info,
    # and provides hue detection tools
    def __init__(self, master=None, ui_queue=None, aimbot_ref=None) :
        super().__init__(master)
        self.ui_queue = ui_queue
        self.aimbot_ref = aimbot_ref   # reference to aimbot worker for ROI settings and avoid list
        self.title("PewPy Debug Console")
        self.geometry("800x700")
        self.minsize(600, 500)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Create tabview for separate panes
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Stats tab
        self.stats_tab = self.tabview.add("System Stats")
        self.stats_text = ctk.CTkTextbox(
            self.stats_tab,
            fg_color="#1e1e1e",
            text_color="#cccccc",
            font=ctk.CTkFont(size=10, family="Courier"),
            state="disabled"
        )
        self.stats_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Logs tab
        self.logs_tab = self.tabview.add("Live Logs")
        self.logs_text = ctk.CTkTextbox(
            self.logs_tab,
            fg_color="#1e1e1e",
            text_color="#cccccc",
            font=ctk.CTkFont(size=10, family="Courier"),
            state="disabled"
        )
        self.logs_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Detection Debug tab
        self.detection_tab = self.tabview.add("Detection Debug")
        self.detection_frame = ctk.CTkFrame(self.detection_tab)
        self.detection_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.detection_text = ctk.CTkTextbox(
            self.detection_frame,
            fg_color="#1e1e1e",
            text_color="#cccccc",
            font=ctk.CTkFont(size=11, family="Consolas"),
            state="disabled",
            wrap="word"
        )
        self.detection_text.pack(fill="both", expand=True)

        # Hue Detection tab
        self.calib_tab = self.tabview.add("Hue Detection")
        self._setup_detection_tab()

        # Avoid Colors tab
        self.avoid_tab = self.tabview.add("Avoid Colors")
        self._setup_avoid_tab()

        self._closed = False
        self._log_buffer = []       # keep last 500 lines
        self._max_log_lines = 500
        self._detection_data = {}   # store latest detection debug info

    # ----- Hue Detection UI -----
    def _setup_detection_tab(self):
        # Build the Hue Detection tab: scan button, tuning parameters, scrollable list of detected colors."""
        # Top frame with scan button, status, and tuning entries
        top_frame = ctk.CTkFrame(self.calib_tab)
        top_frame.pack(fill="x", padx=10, pady=10)

        self.scan_btn = ctk.CTkButton(
            top_frame,
            text="Scan ROI Colors",
            command=self._scan_colors,
            width=150
        )
        self.scan_btn.pack(side="left", padx=5)

        self.scan_status = ctk.CTkLabel(top_frame, text="", text_color="gray")
        self.scan_status.pack(side="left", padx=10)

        # Tuning parameters row
        tune_frame = ctk.CTkFrame(self.calib_tab)
        tune_frame.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(tune_frame, text="Clusters:").pack(side="left", padx=(0, 2))
        self.clusters_entry = ctk.CTkEntry(tune_frame, width=50, justify="center")
        self.clusters_entry.pack(side="left", padx=(0, 10))
        self.clusters_entry.insert(0, "12")   # default

        ctk.CTkLabel(tune_frame, text="Min S%:").pack(side="left", padx=(0, 2))
        self.mins_entry = ctk.CTkEntry(tune_frame, width=50, justify="center")
        self.mins_entry.pack(side="left", padx=(0, 10))
        self.mins_entry.insert(0, "5")        # default

        ctk.CTkLabel(tune_frame, text="Min V%:").pack(side="left", padx=(0, 2))
        self.minv_entry = ctk.CTkEntry(tune_frame, width=50, justify="center")
        self.minv_entry.pack(side="left", padx=(0, 10))
        self.minv_entry.insert(0, "5")        # default

        # Scrollable frame for color list
        self.colors_container = ctk.CTkScrollableFrame(self.calib_tab, label_text="Detected Colors")
        self.colors_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.detected_color_widgets = []  # list of (frame, canvas, label, check_var, check_button, avoid_btn)
        self._color_check_vars = []       # list of BooleanVar for group management
        self._selected_color_index = None # index of currently selected color (or None)

    def _scan_colors(self):
        # Trigger color scanning in a background thread
        if not self.aimbot_ref:
            self.scan_status.configure(text="Aimbot worker not available", text_color="red")
            return

        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.scan_status.configure(text="Scanning ROI for 7 seconds...", text_color="orange")
        # Clear previous list
        for widget_frame, _, _, _, _, _ in self.detected_color_widgets:
            widget_frame.destroy()
        self.detected_color_widgets.clear()
        self._color_check_vars.clear()
        self._selected_color_index = None

        # Read tuning values (default if empty)
        try:
            clusters = int(self.clusters_entry.get())
        except:
            clusters = 12
        try:
            min_s = int(self.mins_entry.get())
        except:
            min_s = 5
        try:
            min_v = int(self.minv_entry.get())
        except:
            min_v = 5

        threading.Thread(target=self._scan_colors_thread, args=(clusters, min_s, min_v), daemon=True).start()

    def _scan_colors_thread(self, clusters, min_s, min_v) :
        # Background thread: capture ROI over 7 seconds, collect pixel samples,
        # extract dominant colors via k-means, and display them.

        try :
            # determine ROI region once (static during scan)
            roi_region = self._get_current_roi_region()
            if roi_region is None :
                self._update_scan_status("Failed to determine ROI region", "red")
                return

            camera = dxcam.create(region=roi_region, output_color="RGB")
            if not camera :
                self._update_scan_status("dxcam: failed to create camera", "red")
                return

            # collect pixel samples over 7 seconds
            sample_rate = 0.5  # seconds between grabs
            duration = 7.0
            end_time = time.time() + duration
            all_pixels = []

            while time.time() < end_time:
                frame = camera.grab()
                if frame is not None :
                    # Ensure frame has 3 channels (RGB or BGR)
                    if len(frame.shape) == 3 and frame.shape[2] == 3:
                        # Downsample to reduce data size
                        sample_step = 5
                        sampled = frame[::sample_step, ::sample_step].reshape(-1, 3)
                        all_pixels.extend(sampled)
                    else :
                        logging.warning(f"Color scan: unexpected frame shape {frame.shape}, skipping")
                else :
                    logging.warning("Color scan: frame grab failed")
                time.sleep(sample_rate)

            camera.stop()
            del camera

            if len(all_pixels) == 0:
                self._update_scan_status("No valid pixel data collected", "red")
                return

            # convert to numpy array and validate shape
            pixels_np = np.array(all_pixels, dtype=np.uint8)
            if pixels_np.ndim != 2 or pixels_np.shape[1] != 3:
                self._update_scan_status(f"Invalid pixel array shape: {pixels_np.shape}", "red")
                logging.error(f"Color scan: invalid pixel array shape {pixels_np.shape}")
                return

            # Reshape flat list of RGB pixels into a 1-row image for OpenCV cvtColor,
            # because cvtColor expects a proper image array (height, width, channels).
            # After conversion, reshape back to a flat list of HSV pixels.
            img_flat = pixels_np.reshape(1, -1, 3)
            hsv_img = cv2.cvtColor(img_flat, cv2.COLOR_RGB2HSV)
            hsv_pixels = hsv_img.reshape(-1, 3)

            # limit number of samples for performance
            max_samples = 10000
            if len(hsv_pixels) > max_samples:
                indices = np.random.choice(len(hsv_pixels), max_samples, replace=False)
                hsv_pixels = hsv_pixels[indices]

            # K-means clustering – use the tunable cluster count
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(hsv_pixels.astype(np.float32), clusters, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            # count cluster sizes
            counts = np.bincount(labels.flatten())
            sorted_indices = np.argsort(counts)[::-1]
            dominant_colors = centers[sorted_indices].astype(np.uint8)

            # convert to user-friendly HSV and filter out colours below the tunable thresholds
            color_list = []
            for hsv_color in dominant_colors:
                h_opencv, s_opencv, v_opencv = hsv_color
                h_deg, s_pct, v_pct = opencv_hsv_to_user(int(h_opencv), int(s_opencv), int(v_opencv))
                if v_pct < min_v or s_pct < min_s:
                    continue
                color_list.append((h_deg, s_pct, v_pct))
                logging.info(f"Detected color: H={h_deg}°, S={s_pct}%, V={v_pct}%")

            # update UI
            self.after(0, self._populate_colors, color_list)
            self._update_scan_status(f"Scan complete: {len(color_list)} colors found", "green")

        except Exception as e:
            logging.error(f"Color scan error: {e}", exc_info=True)
            self._update_scan_status(f"Error: {str(e)[:80]}", "red")
        finally:
            self.after(0, lambda: self.scan_btn.configure(state="normal", text="Scan ROI Colors"))

    def _get_current_roi_region(self) :
        # Return (left, top, right, bottom) tuple for the current ROI, or None if invalid
        aimbot = self.aimbot_ref
        if not aimbot:
            return None
        # Get screen dimensions (fallback)
        try:
            from ctypes import windll
            user32 = windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
        except :
            screen_w, screen_h = 1920, 1080

        # If ROI enabled, use circle around mouse
        if getattr(aimbot, 'roi_enabled', False):
            try :
                from pynput.mouse import Controller
                mouse = Controller()
                mx, my = mouse.position
                radius = getattr(aimbot, 'roi_radius', 150)
                left = max(0, mx - radius)
                top = max(0, my - radius)
                right = min(screen_w, mx + radius)
                bottom = min(screen_h, my + radius)
                if right > left and bottom > top:
                    return (left, top, right, bottom)
                else :
                    return None
            except :
                pass
        # Else use capture_region or full screen
        capture_region = getattr(aimbot, 'capture_region', None)
        if capture_region:
            x, y, w, h = capture_region
            return (x, y, x + w, y + h)
        return (0, 0, screen_w, screen_h)

    def _update_scan_status(self, msg, color):
        self.after(0, lambda: self.scan_status.configure(text=msg, text_color=color))

    def _populate_colors(self, color_list):
        # Populate the scrollable frame with detected color widgets.
        #    Each item shows a colour preview, HSV label, a selection checkbox (radio‑group),
        #    and an "Avoid" button (X)
       
        for idx, (h_deg, s_pct, v_pct) in enumerate(color_list) :
            # Create a frame for this color
            item_frame = ctk.CTkFrame(self.colors_container, fg_color="transparent")
            item_frame.pack(fill="x", pady=2, padx=5)

            # Color preview canvas (20x20)
            canvas = tk.Canvas(item_frame, width=20, height=20, highlightthickness=0)
            hex_color = user_hsv_to_rgb_hex(h_deg, s_pct, v_pct)
            canvas.configure(bg=hex_color)
            canvas.pack(side="left", padx=5)

            # Label: HSV values
            label = ctk.CTkLabel(item_frame, text=f"H: {h_deg}°  S: {s_pct}%  V: {v_pct}%", width=150)
            label.pack(side="left", padx=5)

            # Selection checkbox (radio‑group behaviour)
            check_var = ctk.BooleanVar(value=False)
            self._color_check_vars.append(check_var)
            check_btn = ctk.CTkCheckBox(
                item_frame,
                text="Select",
                variable=check_var,
                command=lambda idx=idx: self._on_color_selected(idx)
            )
            check_btn.pack(side="right", padx=2)

            # Avoid button (red)
            avoid_btn = ctk.CTkButton(
                item_frame, text="X", width=30, height=24,
                fg_color="#dc3545", hover_color="#c82333",
                command=lambda h=h_deg, s=s_pct, v=v_pct, frame=item_frame, idx=idx:
                    self._avoid_color(h, s, v, frame, idx)
            )
            avoid_btn.pack(side="right", padx=2)

            self.detected_color_widgets.append((item_frame, canvas, label, check_var, check_btn, avoid_btn))

    def _on_color_selected(self, selected_idx) :
        # Handle checkbox toggle: only one selection allowed at a time
        # Ensure the index is valid and the frame exists
        if selected_idx >= len(self.detected_color_widgets) :
            return

        # If the selected checkbox is being unchecked, we just clear selection.
        if not self._color_check_vars[selected_idx].get():
            # Unchecking: deselect and clear target
            self._selected_color_index = None
            # Remove highlight from all frames – only if they still exist
            for i, (frame, _, _, _, _, _) in enumerate(self.detected_color_widgets):
                try:
                    if frame.winfo_exists():
                        frame.configure(border_width=0)
                except Exception:
                    pass  # widget already gone
            self._update_scan_status("Target colour deselected", "gray")
            return

        # If checked, uncheck all others
        for i, var in enumerate(self._color_check_vars):
            if i != selected_idx:
                var.set(False)

        # Highlight the selected frame with a green border
        for i, (frame, _, _, _, _, _) in enumerate(self.detected_color_widgets):
            try:
                if frame.winfo_exists():
                    if i == selected_idx:
                        frame.configure(border_width=2, border_color="#28a745")
                    else:
                        frame.configure(border_width=0)
            except Exception:
                pass

        # Retrieve the HSV values of the selected color
        _, _, label, _, _, _ = self.detected_color_widgets[selected_idx]
        # Parse label text: "H: xxx°  S: xxx%  V: xxx%"
        import re
        match = re.search(r"H:\s*(\d+)°\s+S:\s*(\d+)%\s+V:\s*(\d+)%", label.cget("text"))
        if not match:
            self._update_scan_status("Failed to parse HSV from label", "red")
            return
        h = int(match.group(1))
        s = int(match.group(2))
        v = int(match.group(3))

        # Set target colour (with tolerance)
        self._set_target_color(h, s, v)
        self._selected_color_index = selected_idx
        self._update_scan_status(f"Target set: H:{h}° S:{s}% V:{v}%", "green")

    def _set_target_color(self, h, s, v) :
        # Set the aimbot's HSV detection range to the selected colour (with tolerance)
        if not (self.aimbot_ref and hasattr(self.aimbot_ref, 'detector')):
            self._update_scan_status("Aimbot detector not available", "red")
            return

        # Define tolerance (in user-friendly scale)
        h_tol = 5      # degrees
        s_tol = 20     # percentage points
        v_tol = 20     # percentage points

        lower_h = max(0, h - h_tol)
        lower_s = max(0, s - s_tol)
        lower_v = max(0, v - v_tol)
        upper_h = min(360, h + h_tol)
        upper_s = min(100, s + s_tol)
        upper_v = min(100, v + v_tol)

        # Convert to OpenCV scale
        lower_cv = user_hsv_to_opencv(lower_h, lower_s, lower_v)
        upper_cv = user_hsv_to_opencv(upper_h, upper_s, upper_v)

        try:
            detector = self.aimbot_ref.detector
            detector.set_hsv_range(lower_cv, upper_cv)
            logging.info(f"Target HSV set to: lower=({lower_h}°,{lower_s}%,{lower_v}%) upper=({upper_h}°,{upper_s}%,{upper_v}%)")
            self._update_scan_status(f"Target set: H:{h}° S:{s}% V:{v}% (tol ±{h_tol}°, ±{s_tol}%, ±{v_tol}%)", "green")

            # Notify main UI to update the Aimbot tab entries
            if self.ui_queue:
                self.ui_queue.put_nowait({
                    'type': 'update_hsv_entries',
                    'lower_h': lower_h,
                    'lower_s': lower_s,
                    'lower_v': lower_v,
                    'upper_h': upper_h,
                    'upper_s': upper_s,
                    'upper_v': upper_v
                })
        except Exception as e:
            logging.error(f"Failed to set target color: {e}", exc_info=True)
            self._update_scan_status(f"Error: {str(e)[:60]}", "red")

    def _avoid_color(self, h, s, v, item_frame, idx) :
        # Move the selected color to the avoid list and remove the widget
        if not (self.aimbot_ref and hasattr(self.aimbot_ref, 'detector')):
            return

        try :
            detector = self.aimbot_ref.detector
            detector.add_avoid_color(int(h), int(s), int(v))
            # Remove from display
            item_frame.destroy()
            # Remove from our lists
            if idx < len(self.detected_color_widgets):
                self.detected_color_widgets.pop(idx)
                self._color_check_vars.pop(idx)
            # If this was the selected index, clear it
            if self._selected_color_index == idx:
                self._selected_color_index = None
            elif self._selected_color_index is not None and self._selected_color_index > idx:
                self._selected_color_index -= 1
            # Update the avoid colors tab
            self._refresh_avoid_tab()
            self._update_scan_status(f"Avoided color H:{h}° S:{s}% V:{v}%", "orange")
        except OverflowError as oe:
            logging.error(f"OverflowError adding avoided color H:{h} S:{s} V:{v}: {oe}")
            self._update_scan_status("Failed to add avoid color (overflow)", "red")
        except Exception as e:
            logging.error(f"Error adding avoided color H:{h} S:{s} V:{v}: {e}", exc_info=True)
            self._update_scan_status(f"Failed to add avoid color: {str(e)[:60]}", "red")

    def _refresh_avoid_tab(self) :
        # Rebuild the Avoid Colors tab from current detector avoid list."""
        if not self.aimbot_ref or not hasattr(self.aimbot_ref, 'detector'):
            return
        detector = self.aimbot_ref.detector
        avoid_list = detector.get_avoid_colors()  # list of ((low_h,low_s,low_v), (high_h,high_s,high_v))
        # Clear existing widgets
        for widget in self.avoid_widgets:
            widget.destroy()
        self.avoid_widgets.clear()

        for idx, ((low_h, low_s, low_v), (high_h, high_s, high_v)) in enumerate(avoid_list):
            item_frame = ctk.CTkFrame(self.avoid_container, fg_color="transparent")
            item_frame.pack(fill="x", pady=2, padx=5)

            # Compute the centre of the stored range
            center_h = (low_h + high_h) // 2
            center_s = (low_s + high_s) // 2
            center_v = (low_v + high_v) // 2

            # Preview canvas
            hex_color = user_hsv_to_rgb_hex(center_h, center_s, center_v)
            canvas = tk.Canvas(item_frame, width=20, height=20, bg=hex_color, highlightthickness=0)
            canvas.pack(side="left", padx=5)

            label = ctk.CTkLabel(item_frame,
                                 text=f"H: {center_h}°  S: {center_s}%  V: {center_v}%")
            label.pack(side="left", padx=5)

            restore_btn = ctk.CTkButton(
                item_frame, text="Restore", width=60, height=24,
                command=lambda idx=idx: self._restore_avoid_color(idx)
            )
            restore_btn.pack(side="right", padx=5)

            self.avoid_widgets.append(item_frame)

    def _restore_avoid_color(self, index) :
        if self.aimbot_ref and hasattr(self.aimbot_ref, 'detector'):
            self.aimbot_ref.detector.remove_avoid_color(index)
            self._refresh_avoid_tab()
            self._update_scan_status("Avoid color removed", "green")

    def _setup_avoid_tab(self) :
        # Build the Avoid Colors tab
        self.avoid_container = ctk.CTkScrollableFrame(self.avoid_tab, label_text="Avoided Colors")
        self.avoid_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.avoid_widgets = []
        clear_btn = ctk.CTkButton(
            self.avoid_tab, text="Clear All Avoided Colors",
            command=self._clear_all_avoid, fg_color="#6c757d"
        )
        clear_btn.pack(pady=10)

    def _clear_all_avoid(self) :
        if self.aimbot_ref and hasattr(self.aimbot_ref, 'detector'):
            self.aimbot_ref.detector.clear_avoid_colors()
            self._refresh_avoid_tab()
            self._update_scan_status("All avoided colors cleared", "green")

    # ----- Existing methods (update_stats, add_log, etc.) -----
    def update_stats(self, data: dict) -> None :
        if self._closed :
            return
        lines = []
        w = data.get('workers', {})
        lines.append(f"--- Workers ({w.get('running_workers', 0)}/{w.get('total_workers', 0)}) ---")
        for name, info in w.get('worker_details', {}).items():
            state = info.get('state', '?')
            alive = "alive" if info.get('thread_alive') else "dead"
            runtime = info.get('runtime_seconds', 0)
            errors = info.get('error_count', 0)
            lines.append(f"  {name}: {state} ({alive}) | {runtime:.1f}s | errors:{errors}")

        lines.append(f"CPU: {data.get('cpu', 'N/A')}%")
        lines.append(f"RAM: {data.get('mem', 'N/A')}%")
        lines.append(f"Resource Manager: {'ON' if data.get('rm_running') else 'OFF'}")

        if 'error' in data:
            lines.append(f"ERROR: {data['error']}")

        text = "\n".join(lines)
        if not self._closed:
            self.after(0, self._update_text, self.stats_text, text)

    def update_detection_debug(self, data: dict) -> None:
        if self._closed:
            return
        self._detection_data = data
        self.after(0, self._refresh_detection_display)

    def _refresh_detection_display(self) :
        if self._closed :
            return
        lines = []
        lower = self._detection_data.get('hsv_lower_user', (0,0,0))
        upper = self._detection_data.get('hsv_upper_user', (0,0,0))
        lines.append(f"HSV Bounds (user): Lower ({lower[0]}°, {lower[1]}%, {lower[2]}%)")
        lines.append(f"                   Upper ({upper[0]}°, {upper[1]}%, {upper[2]}%)")
        lines.append("")
        lines.append(f"Aimbot Running: {'YES' if self._detection_data.get('aimbot_running', False) else 'NO'}")
        lines.append(f"ROI Enabled: {'YES' if self._detection_data.get('roi_enabled', False) else 'NO'}")
        if self._detection_data.get('roi_enabled', False):
            radius = self._detection_data.get('roi_radius', 0)
            mouse = self._detection_data.get('mouse_pos')
            if mouse :
                lines.append(f"  Mouse position: ({mouse[0]}, {mouse[1]})")
            else :
                lines.append("  Mouse position: unknown")
            lines.append(f"  ROI radius: {radius} px")
        lines.append(f"Confidence Threshold: {self._detection_data.get('confidence_threshold', 0.0):.2f}")
        lines.append(f"Outline Mode: {'ON' if self._detection_data.get('outline_mode', False) else 'OFF'}")
        lines.append("")
        lines.append(f"Contours found: {self._detection_data.get('contour_count', 0)}")
        lines.append(f"Best candidate confidence: {self._detection_data.get('best_candidate_confidence', 0.0):.3f}")
        reject_reason = self._detection_data.get('reject_reason', '')
        if reject_reason :
            lines.append(f"Reject reason: {reject_reason}")
        lines.append("")
        detected = self._detection_data.get('target_detected', False)
        lines.append(f"Target Detected: {'YES' if detected else 'NO'}")
        if detected:
            center = self._detection_data.get('center', (0,0))
            conf = self._detection_data.get('confidence', 0.0)
            pts = self._detection_data.get('contour_points', 0)
            lines.append(f"  Center: ({center[0]}, {center[1]})")
            lines.append(f"  Confidence: {conf:.3f}")
            lines.append(f"  Contour points: {pts}")
        else :
            cand_center = self._detection_data.get('candidate_center')
            cand_conf = self._detection_data.get('candidate_confidence')
            if cand_center is not None and cand_conf is not None:
                lines.append("Best candidate (rejected):")
                lines.append(f"  Center: ({cand_center[0]}, {cand_center[1]})")
                lines.append(f"  Confidence: {cand_conf:.3f}")
            else :
                lines.append("No candidate contours found.")
        lines.append("")
        lines.append("(Updates every 0.5s)")

        text = "\n".join(lines)
        self.detection_text.configure(state="normal")
        self.detection_text.delete("1.0", "end")
        self.detection_text.insert("1.0", text)
        self.detection_text.configure(state="disabled")

    def add_log(self, log_msg: str) -> None :
        if self._closed :
            return
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] {log_msg}"
        self._log_buffer.append(formatted)
        if len(self._log_buffer) > self._max_log_lines:
            self._log_buffer.pop(0)
        if not self._closed :
            self.after(0, self._update_logs)

    def _update_text(self, text_widget, text: str) -> None :
        if self._closed :
            return
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", text)
        text_widget.configure(state="disabled")

    def _update_logs(self) -> None :
        if self._closed:
            return
        full_log = "\n".join(self._log_buffer)
        self.logs_text.configure(state="normal")
        self.logs_text.delete("1.0", "end")
        self.logs_text.insert("1.0", full_log)
        self.logs_text.configure(state="disabled")
        self.logs_text.see("end")

    def on_close(self) -> None :
        self._closed = True
        self.destroy()