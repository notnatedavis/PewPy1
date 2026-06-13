#   pewpy/ui/tabs/general_tab.py
#   General tab: title, placeholders, status bar, and a separate debug window
#   with live logging and diagnostics, plus detection debug tab.
#   Extended with Hue Detection and Avoid Colors tabs

# ----- Imports ----- #
import customtkinter as ctk
import logging
import threading
import time
import tkinter as tk
from .base_tab import BaseTab
import queue

# ----- Custom Logging Handler for Debug Window -----
class DebugWindowHandler(logging.Handler):
    """Forward log records to the debug window via the UI queue."""
    def __init__(self, ui_queue):
        super().__init__()
        self.ui_queue = ui_queue
        self.setLevel(logging.DEBUG)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.ui_queue.put_nowait({'type': 'debug_log', 'log': msg})
        except Exception:
            pass  # avoid recursion

# ----- Debug Window Class (separate toplevel) -----
class DebugWindow(ctk.CTkToplevel):
    # Standalone window that displays live diagnostics, logs, detection debug info,
    # and provides hue detection tools
    def __init__(self, master=None, ui_queue=None, aimbot_ref=None):
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

        # ----- New: Hue Detection tab -----
        self.calib_tab = self.tabview.add("Hue Detection")
        self._setup_detection_tab()

        # ----- New: Avoid Colors tab -----
        self.avoid_tab = self.tabview.add("Avoid Colors")
        self._setup_avoid_tab()

        self._closed = False
        self._log_buffer = []       # keep last 500 lines
        self._max_log_lines = 500
        self._detection_data = {}   # store latest detection debug info

    # ----- Hue Detection UI -----
    def _setup_detection_tab(self):
        """Build the Hue Detection tab: scan button, tuning parameters, scrollable list of detected colors."""
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

        self.detected_color_widgets = []  # list of (frame, canvas, label, avoid_button)

    def _scan_colors(self):
        """Trigger color scanning in a background thread."""
        if not self.aimbot_ref:
            self.scan_status.configure(text="Aimbot worker not available", text_color="red")
            return

        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.scan_status.configure(text="Scanning ROI for 7 seconds...", text_color="orange")
        # Clear previous list
        for widget_frame, _, _, _ in self.detected_color_widgets:
            widget_frame.destroy()
        self.detected_color_widgets.clear()

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

            import dxcam
            import cv2
            import numpy as np

            camera = dxcam.create(region=roi_region, output_color="RGB")
            if not camera:
                self._update_scan_status("dxcam: failed to create camera", "red")
                return

            # collect pixel samples over 7 seconds
            sample_rate = 0.5  # seconds between grabs
            duration = 7.0
            end_time = time.time() + duration
            all_pixels = []

            while time.time() < end_time:
                frame = camera.grab()
                if frame is not None:
                    # Ensure frame has 3 channels (RGB or BGR)
                    if len(frame.shape) == 3 and frame.shape[2] == 3:
                        # Downsample to reduce data size
                        sample_step = 5
                        sampled = frame[::sample_step, ::sample_step].reshape(-1, 3)
                        all_pixels.extend(sampled)
                    else:
                        logging.warning(f"Color scan: unexpected frame shape {frame.shape}, skipping")
                else:
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
            for hsv_color in dominant_colors : 
                h_opencv, s_opencv, v_opencv = hsv_color
                # Convert to native int to prevent numpy.uint8 overflow
                h_deg = int(h_opencv) * 2
                s_pct = int(s_opencv) * 100 // 255
                v_pct = int(v_opencv) * 100 // 255
                if v_pct < min_v or s_pct < min_s:
                    continue
                color_list.append((h_deg, s_pct, v_pct))
                logging.info(f"Detected color: H={h_deg}°, S={s_pct}%, V={v_pct}%")

            # update UI
            self.after(0, self._populate_colors, color_list)
            self._update_scan_status(f"Scan complete: {len(color_list)} colors found", "green")

        except Exception as e :
            logging.error(f"Color scan error: {e}", exc_info=True)
            self._update_scan_status(f"Error: {str(e)[:80]}", "red")
        finally :
            self.after(0, lambda: self.scan_btn.configure(state="normal", text="Scan ROI Colors"))

    def _get_current_roi_region(self):
        """Return (left, top, right, bottom) tuple for the current ROI, or None if invalid."""
        aimbot = self.aimbot_ref
        if not aimbot:
            return None
        # Get screen dimensions (fallback)
        try:
            from ctypes import windll
            user32 = windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
        except:
            screen_w, screen_h = 1920, 1080

        # If ROI enabled, use circle around mouse
        if getattr(aimbot, 'roi_enabled', False):
            try:
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
                else:
                    return None
            except:
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
        """Populate the scrollable frame with detected color widgets."""
        import colorsys
        for h_deg, s_pct, v_pct in color_list:
            # Create a frame for this color
            item_frame = ctk.CTkFrame(self.colors_container, fg_color="transparent")
            item_frame.pack(fill="x", pady=2, padx=5)

            # Color preview canvas (20x20)
            canvas = tk.Canvas(item_frame, width=20, height=20, highlightthickness=0)
            # Convert HSV to RGB for preview
            rgb = colorsys.hsv_to_rgb(h_deg/360.0, s_pct/100.0, v_pct/100.0)
            hex_color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
            canvas.configure(bg=hex_color)
            canvas.pack(side="left", padx=5)

            # Label: HSV values
            label = ctk.CTkLabel(item_frame, text=f"H: {h_deg}°  S: {s_pct}%  V: {v_pct}%", width=150)
            label.pack(side="left", padx=5)

            # Avoid button (X)
            avoid_btn = ctk.CTkButton(
                item_frame, text="X", width=30, height=24,
                fg_color="#dc3545", hover_color="#c82333",
                command=lambda h=h_deg, s=s_pct, v=v_pct, frame=item_frame: self._avoid_color(h, s, v, frame)
            )
            avoid_btn.pack(side="right", padx=5)

            self.detected_color_widgets.append((item_frame, canvas, label, avoid_btn))

    def _avoid_color(self, h, s, v, item_frame):
        """Move the selected color to the avoid list.
           Passes the original user-friendly values (H in degrees, S/V in percent)
           directly to the detector, which handles its own conversion.
           Wraps the call in try/except to avoid UI crashes."""
        if not (self.aimbot_ref and hasattr(self.aimbot_ref, 'detector')):
            return

        try:
            detector = self.aimbot_ref.detector
            # Call the detector with the original percentage values –
            # its add_avoid_color expects H 0‑360°, S 0‑100%, V 0‑100%
            detector.add_avoid_color(int(h), int(s), int(v))
            # Remove from display only on success
            item_frame.destroy()
            # Update the avoid colors tab
            self._refresh_avoid_tab()
            self._update_scan_status(f"Avoided color H:{h}° S:{s}% V:{v}%", "orange")
        except OverflowError as oe:
            logging.error(f"OverflowError adding avoided color H:{h} S:{s} V:{v}: {oe}")
            self._update_scan_status("Failed to add avoid color (overflow)", "red")
        except Exception as e:
            logging.error(f"Error adding avoided color H:{h} S:{s} V:{v}: {e}", exc_info=True)
            self._update_scan_status(f"Failed to add avoid color: {str(e)[:60]}", "red")

    def _refresh_avoid_tab(self):
        """Rebuild the Avoid Colors tab from current detector avoid list.
           Displays the **center** of each avoided range as a single H, S, V
           (instead of the full range), giving the exact colour that was added."""
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

            # Compute the centre of the stored range (OpenCV scale)
            center_h = (low_h + high_h) // 2
            center_s = (low_s + high_s) // 2
            center_v = (low_v + high_v) // 2

            # Convert centre to user-friendly units
            h_deg = center_h * 2
            s_pct = center_s * 100 // 255
            v_pct = center_v * 100 // 255

            # Preview canvas (using the centre colour)
            import colorsys
            rgb = colorsys.hsv_to_rgb(h_deg/360.0, s_pct/100.0, v_pct/100.0)
            hex_color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
            canvas = tk.Canvas(item_frame, width=20, height=20, bg=hex_color, highlightthickness=0)
            canvas.pack(side="left", padx=5)

            # Label shows the single centre values
            label = ctk.CTkLabel(item_frame,
                                 text=f"H: {h_deg}°  S: {s_pct}%  V: {v_pct}%")
            label.pack(side="left", padx=5)

            restore_btn = ctk.CTkButton(
                item_frame, text="Restore", width=60, height=24,
                command=lambda idx=idx: self._restore_avoid_color(idx)
            )
            restore_btn.pack(side="right", padx=5)

            self.avoid_widgets.append(item_frame)

    def _restore_avoid_color(self, index):
        if self.aimbot_ref and hasattr(self.aimbot_ref, 'detector'):
            self.aimbot_ref.detector.remove_avoid_color(index)
            self._refresh_avoid_tab()
            self._update_scan_status(f"Avoid color removed", "green")

    def _setup_avoid_tab(self):
        """Build the Avoid Colors tab."""
        self.avoid_container = ctk.CTkScrollableFrame(self.avoid_tab, label_text="Avoided Colors")
        self.avoid_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.avoid_widgets = []
        # Clear all button
        clear_btn = ctk.CTkButton(
            self.avoid_tab, text="Clear All Avoided Colors",
            command=self._clear_all_avoid, fg_color="#6c757d"
        )
        clear_btn.pack(pady=10)

    def _clear_all_avoid(self):
        if self.aimbot_ref and hasattr(self.aimbot_ref, 'detector'):
            self.aimbot_ref.detector.clear_avoid_colors()
            self._refresh_avoid_tab()
            self._update_scan_status("All avoided colors cleared", "green")

    # ----- Existing methods (update_stats, add_log, etc.) remain -----
    def update_stats(self, data: dict) -> None:
        if self._closed:
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

    def _refresh_detection_display(self):
        if self._closed:
            return
        lines = []
        lower = self._detection_data.get('hsv_lower_user', (0,0,0))
        upper = self._detection_data.get('hsv_upper_user', (0,0,0))
        lines.append(f"HSV Bounds (user): Lower ({lower[0]}°, {lower[1]}%, {lower[2]}%)")
        lines.append(f"                   Upper ({upper[0]}°, {upper[1]}%, {upper[2]}%)")
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
        else:
            cand_center = self._detection_data.get('candidate_center')
            cand_conf = self._detection_data.get('candidate_confidence')
            if cand_center is not None and cand_conf is not None:
                lines.append(f"Best candidate (rejected):")
                lines.append(f"  Center: ({cand_center[0]}, {cand_center[1]})")
                lines.append(f"  Confidence: {cand_conf:.3f}")
            else:
                lines.append("No candidate contours found.")
        lines.append("")
        lines.append("(Updates every 0.5s)")

        text = "\n".join(lines)
        self.detection_text.configure(state="normal")
        self.detection_text.delete("1.0", "end")
        self.detection_text.insert("1.0", text)
        self.detection_text.configure(state="disabled")

    def add_log(self, log_msg: str) -> None:
        if self._closed:
            return
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] {log_msg}"
        self._log_buffer.append(formatted)
        if len(self._log_buffer) > self._max_log_lines:
            self._log_buffer.pop(0)
        if not self._closed:
            self.after(0, self._update_logs)

    def _update_text(self, text_widget, text: str) -> None:
        if self._closed:
            return
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", text)
        text_widget.configure(state="disabled")

    def _update_logs(self) -> None:
        if self._closed:
            return
        full_log = "\n".join(self._log_buffer)
        self.logs_text.configure(state="normal")
        self.logs_text.delete("1.0", "end")
        self.logs_text.insert("1.0", full_log)
        self.logs_text.configure(state="disabled")
        self.logs_text.see("end")

    def on_close(self) -> None:
        self._closed = True
        self.destroy()

# ----- Main General Tab (unchanged except passing aimbot reference) -----
class GeneralTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        super().__init__(parent_tab, app, ui_queue)
        self._diagnostics_running = False
        self._diagnostics_thread = None
        self.debug_window = None
        self._log_handler = None

    def _create_widgets(self) -> None:
        # Title
        self.title_label = ctk.CTkLabel(
            self.frame,
            text="PewPy",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(pady=(0, 10), anchor="center")

        # Placeholder buttons
        self.placeholder_btn1 = ctk.CTkButton(
            self.frame,
            text="Placeholder 1",
            command=lambda: self._placeholder_action("Placeholder 1"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.placeholder_btn1.pack(pady=6, anchor="center")

        self.placeholder_btn2 = ctk.CTkButton(
            self.frame,
            text="Placeholder 2",
            command=lambda: self._placeholder_action("Placeholder 2"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.placeholder_btn2.pack(pady=6, anchor="center")

        # Status bar
        self.status_var = ctk.StringVar(value="Ready - PewPy Online")
        self.status_bar = ctk.CTkLabel(
            self.frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_bar.pack(pady=(20, 10), anchor="center")

        # Debug window button
        self.debug_btn = ctk.CTkButton(
            self.frame,
            text="Open Debug Window",
            command=self._toggle_debug_window,
            width=140,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.debug_btn.pack(pady=(0, 5), anchor="center")

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _placeholder_action(self, name: str) -> None:
        logging.info(f"Placeholder '{name}' clicked")

    # --- Debug window management ---
    def _toggle_debug_window(self) -> None:
        if self.debug_window is None or not self.debug_window.winfo_exists():
            # Pass aimbot reference to debug window for calibration
            aimbot = self.app.workers.get('aimbot') if self.app.workers else None
            self.debug_window = DebugWindow(self.frame.winfo_toplevel(), self.ui_queue, aimbot)
            self.debug_btn.configure(text="Close Debug Window")
            self._install_log_handler()
            self._start_diagnostics()
            logging.info("Debug window opened")
        else:
            self.debug_window.on_close()
            self.debug_window = None
            self.debug_btn.configure(text="Open Debug Window")
            self._remove_log_handler()
            self._stop_diagnostics()
            logging.info("Debug window closed")

    def _install_log_handler(self) -> None:
        if self._log_handler is None:
            self._log_handler = DebugWindowHandler(self.ui_queue)
            self._log_handler.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))
            logging.getLogger().addHandler(self._log_handler)
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Custom debug logging handler installed")

    def _remove_log_handler(self) -> None:
        if self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler = None
            logging.debug("Custom debug logging handler removed")

    def _start_diagnostics(self) -> None:
        if self._diagnostics_running:
            return
        self._diagnostics_running = True
        self._diagnostics_thread = threading.Thread(
            target=self._diagnostics_loop,
            daemon=True,
            name="Diagnostics"
        )
        self._diagnostics_thread.start()

    def _stop_diagnostics(self) -> None:
        self._diagnostics_running = False
        if self._diagnostics_thread and self._diagnostics_thread.is_alive():
            self._diagnostics_thread.join(timeout=1.0)

    def _diagnostics_loop(self) -> None :
        while self._diagnostics_running : 
            data = {}
            try :
                data['workers'] = self.app.thread_manager.get_worker_stats()

                try :
                    import psutil
                    data['cpu'] = psutil.cpu_percent(interval=0.1)
                    data['mem'] = psutil.virtual_memory().percent
                except Exception :
                    data['cpu'] = 'N/A'
                    data['mem'] = 'N/A'

                data['rm_running'] = self.app.resource_manager.running

            except Exception as e:
                data['error'] = str(e)

            self.ui_queue.put_nowait({'type': 'debug_data', 'data': data})
            time.sleep(2)

    def update_debug_info(self, data: dict) -> None :
        if self.debug_window and not self.debug_window._closed:
            self.debug_window.update_stats(data)

    def handle_debug_log(self, log_msg: str) -> None:
        if self.debug_window and not self.debug_window._closed:
            self.debug_window.add_log(log_msg)

    def update_detection_debug(self, data: dict) -> None:
        """Forward detection debug data to the debug window."""
        if self.debug_window and not self.debug_window._closed:
            self.debug_window.update_detection_debug(data)