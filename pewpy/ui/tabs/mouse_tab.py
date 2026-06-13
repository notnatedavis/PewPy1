#   pewpy/ui/tabs/mouse_tab.py
#   Mouse tab: auto-clicker toggle, interval entry, live HSV reader

# ----- Imports ----- #
import customtkinter as ctk
import logging
import threading
import time
from .base_tab import BaseTab

# ----- Main Class ----- #
class MouseTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        # ---- Availability checks must happen BEFORE _create_widgets is called ----
        self._dxcam_available = False
        self._pynput_available = False
        try:
            import dxcam
            self._dxcam_available = True
        except ImportError:
            logging.warning("dxcam not available – HSV reader disabled")
        try:
            from pynput.mouse import Controller
            self._pynput_available = True
        except ImportError:
            logging.warning("pynput not available – HSV reader disabled")

        super().__init__(parent_tab, app, ui_queue)

        self._hsv_thread = None
        self._hsv_running = False
        self._hsv_stop_event = threading.Event()

    def _create_widgets(self) -> None:
        # Top row: auto-clicker button + interval entry
        top_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_frame.pack(pady=(30, 10), anchor="center")

        self.auto_clicker_btn = ctk.CTkButton(
            top_frame,
            text="Auto-Clicker: (off)",
            command=self.toggle_auto_clicker,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.auto_clicker_btn.pack(side="left", padx=(0, 10))

        self.interval_var = ctk.StringVar(value="0.1")
        self.interval_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.interval_var,
            width=100,
            height=40,
            justify="center",
            font=ctk.CTkFont(size=12),
            placeholder_text="Interval (sec)"
        )
        self.interval_entry.pack(side="left")
        self.interval_entry.bind("<FocusOut>", self._update_interval)
        self.interval_entry.bind("<Return>", self._update_interval)

        # HSV row: button + live label
        hsv_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        hsv_frame.pack(pady=10, anchor="center")

        self.hsv_btn = ctk.CTkButton(
            hsv_frame,
            text="Read HSV @ Mouse: (off)",
            command=self.toggle_hsv_read,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268",
            state="normal" if (self._dxcam_available and self._pynput_available) else "disabled"
        )
        self.hsv_btn.pack(side="left", padx=(0, 10))

        self.hsv_label = ctk.CTkLabel(
            hsv_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        self.hsv_label.pack(side="left")

        # Placeholder B remains
        self.mouse_placeholder2 = ctk.CTkButton(
            self.frame,
            text="Placeholder B",
            command=lambda: self._placeholder_action("Placeholder B"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.mouse_placeholder2.pack(pady=6, anchor="center")

    # ------------------ Auto-Clicker ------------------
    def toggle_auto_clicker(self) -> None:
        try:
            worker_name = 'auto_clicker'
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Processing auto-clicker...'})
            if self.app.is_worker_running(worker_name):
                success = self.app.stop_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'auto_clicker', 'state': False})
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Auto-clicker: STOPPED'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to stop auto-clicker'})
            else:
                success = self.app.start_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'auto_clicker', 'state': True})
                    interval = self.interval_var.get()
                    self.ui_queue.put_nowait({'type': 'status', 'message': f'Auto-clicker: RUNNING ({interval}s interval)'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to start auto-clicker'})
        except Exception as e:
            logging.error(f"Toggle auto-clicker error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def _update_interval(self, event=None) -> None:
        try:
            value = self.interval_var.get().strip()
            if not value:
                value = "0.1"
                self.interval_var.set(value)
            interval = float(value)
            interval = max(0.01, min(10.0, interval))
            if self.app.is_worker_running('auto_clicker'):
                worker = self.app.workers['auto_clicker']
                if hasattr(worker, 'set_interval'):
                    worker.set_interval(interval)
                    self.ui_queue.put_nowait({'type': 'status', 'message': f'Interval updated: {interval}s'})
        except ValueError as e:
            logging.error(f"Invalid interval: {e}")
            self.interval_var.set("0.1")
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Invalid interval, reset to 0.1s'})

    # ------------------ HSV Reader ------------------
    def toggle_hsv_read(self) -> None:
        if not (self._dxcam_available and self._pynput_available):
            self.ui_queue.put_nowait({'type': 'status', 'message': 'HSV reader: dxcam or pynput missing'})
            return

        if self._hsv_running:
            # Stop
            self._hsv_running = False
            self._hsv_stop_event.set()
            self.hsv_btn.configure(text="Read HSV @ Mouse: (off)", fg_color="#6c757d", hover_color="#5a6268")
            self.ui_queue.put_nowait({'type': 'status', 'message': 'HSV reader: stopped'})
        else:
            # Start
            self._hsv_running = True
            self._hsv_stop_event.clear()
            self.hsv_btn.configure(text="Read HSV @ Mouse: (on)", fg_color="#28a745", hover_color="#218838")
            self._hsv_thread = threading.Thread(target=self._hsv_read_loop, daemon=True, name="HSVReader")
            self._hsv_thread.start()
            self.ui_queue.put_nowait({'type': 'status', 'message': 'HSV reader: running'})

    def _hsv_read_loop(self) -> None:
        """
        Background thread: captures a single pixel at the mouse cursor,
        converts it to HSV, and sends the values to the UI.
        OpenCV's native HSV scale:
            H: 0-179 (maps to 0-360°)
            S: 0-255
            V: 0-255
        The displayed values are converted to the common 360°/100%/100% scale
        for intuitive interpretation.
        Uses dxcam with RGB output to avoid channel‑swap issues.
        """
        import dxcam
        import cv2
        import numpy as np
        from pynput.mouse import Controller as MouseCtrl

        mouse = MouseCtrl()
        # Note: dxcam.create(output_color="RGB") may still return BGR on some systems.
        # We will convert using BGR2HSV to be safe (common for screen capture libraries).
        camera = dxcam.create(output_color="RGB")
        if not camera:
            logging.error("HSV reader: failed to create dxcam camera")
            self._hsv_running = False
            return

        logging.info("HSV reader thread started")
        while not self._hsv_stop_event.is_set():
            try:
                x, y = mouse.position
                region = (x, y, x + 1, y + 1)
                frame = camera.grab(region=region)
                if frame is not None and frame.size > 0:
                    # frame[0,0] is a 3-element array. dxcam claims RGB but often gives BGR.
                    # Using BGR2HSV because that matches the actual order on most Windows setups.
                    pixel_bgr = frame[0, 0]           # (B, G, R) or (R, G, B) – we don't know.
                    # Reshape for cvtColor: 1x1 image with 3 channels
                    bgr_reshaped = np.array([[pixel_bgr]], dtype=np.uint8)
                    # Convert BGR to HSV (most reliable for dxcam)
                    hsv_pixel = cv2.cvtColor(bgr_reshaped, cv2.COLOR_BGR2HSV)[0, 0]

                    # Convert to user‑friendly ranges
                    h_deg = int(hsv_pixel[0] * 2)          # 0-179 → 0-358 (≈0-360)
                    s_pct = int(hsv_pixel[1] / 255 * 100)  # 0-255 → 0-100%
                    v_pct = int(hsv_pixel[2] / 255 * 100)  # 0-255 → 0-100%

                    # Debug: log raw pixel and HSV for verification (optional, can be removed)
                    # logging.debug(f"Raw pixel: {pixel_bgr}, HSV(OpenCV): {hsv_pixel}")

                    try:
                        self.ui_queue.put_nowait({'type': 'hsv_update', 'hsv': (h_deg, s_pct, v_pct)})
                    except Exception as qe:
                        logging.debug(f"HSV reader queue full: {qe}")
                else:
                    logging.debug("HSV reader: frame grab failed or empty")
            except Exception as e:
                logging.error(f"HSV reader loop error: {e}")
            time.sleep(0.05)  # ~20 updates per second

        logging.info("HSV reader thread stopped")
        try:
            del camera
        except:
            pass

    def update_hsv_display(self, h: int, s: int, v: int) -> None:
        # called from main thread to update the HSV label (360°, %, %)."""
        self.hsv_label.configure(text=f"HSV: ({h}°, {s}%, {v}%)")

    # ------------------ Worker state update ------------------
    def update_worker_button(self, worker: str, is_running: bool) -> None:
        if worker == 'auto_clicker':
            if is_running:
                self.auto_clicker_btn.configure(text="Auto-Clicker: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.auto_clicker_btn.configure(text="Auto-Clicker: (off)", fg_color="#dc3545", hover_color="#c82333")

    def _placeholder_action(self, name: str) -> None:
        logging.info(f"Placeholder '{name}' clicked")