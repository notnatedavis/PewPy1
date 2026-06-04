#   pewpy/ui/tabs/aimbot_tab.py
#   Aimbot tab: compact, sectioned layout with direct HSV text entry
#   and live colour preview for both lower and upper bounds.
#   HSV values are displayed and entered in the standard colour-picker
#   scale (H: 0‑360°, S: 0‑100%, V: 0‑100%) and converted to OpenCV's
#   internal scale (H: 0‑179, S: 0‑255, V: 0‑255) when applied.

# ----- Imports ----- #
import customtkinter as ctk
import logging
from .base_tab import BaseTab
import tkinter as tk

# ----- Main Class ----- #
class AimbotTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        # Colour preview canvases (created later)
        self.lower_color_canvas = None
        self.upper_color_canvas = None

        # HSV entry variables – standard 360°/100%/100% scale
        self.lower_h_var = ctk.StringVar(value="0")    # 0°
        self.lower_s_var = ctk.StringVar(value="47")   # 47%
        self.lower_v_var = ctk.StringVar(value="27")   # 27%
        self.upper_h_var = ctk.StringVar(value="20")   # 20°
        self.upper_s_var = ctk.StringVar(value="100")  # 100%
        self.upper_v_var = ctk.StringVar(value="100")  # 100%

        super().__init__(parent_tab, app, ui_queue)

    def _create_widgets(self) -> None:
        # ----- Aimbot toggle button (standalone) -----
        self.aimbot_btn = ctk.CTkButton(
            self.frame,
            text="Aimbot: (off)",
            command=self.toggle_aimbot,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.aimbot_btn.pack(pady=(20, 10), anchor="center")

        # ====== Detection Settings section ======
        detect_header = ctk.CTkLabel(self.frame, text="Detection Settings",
                                     font=ctk.CTkFont(size=13, weight="bold"))
        detect_header.pack(pady=(5, 5), anchor="center")

        detect_frame = ctk.CTkFrame(self.frame)
        detect_frame.pack(pady=5, fill="x", padx=20)

        # ---- Lower HSV row ----
        lower_row = ctk.CTkFrame(detect_frame, fg_color="transparent")
        lower_row.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(lower_row, text="Lower HSV", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,2))

        entry_row_l = ctk.CTkFrame(lower_row, fg_color="transparent")
        entry_row_l.pack(fill="x", pady=2)

        ctk.CTkLabel(entry_row_l, text="H", width=15).pack(side="left")
        self.lower_h_entry = ctk.CTkEntry(
            entry_row_l, textvariable=self.lower_h_var, width=40,
            justify="center", font=ctk.CTkFont(size=11)
        )
        self.lower_h_entry.pack(side="left", padx=(2,5))

        ctk.CTkLabel(entry_row_l, text="S", width=15).pack(side="left")
        self.lower_s_entry = ctk.CTkEntry(
            entry_row_l, textvariable=self.lower_s_var, width=40,
            justify="center", font=ctk.CTkFont(size=11)
        )
        self.lower_s_entry.pack(side="left", padx=(2,5))

        ctk.CTkLabel(entry_row_l, text="V", width=15).pack(side="left")
        self.lower_v_entry = ctk.CTkEntry(
            entry_row_l, textvariable=self.lower_v_var, width=40,
            justify="center", font=ctk.CTkFont(size=11)
        )
        self.lower_v_entry.pack(side="left", padx=(2,5))

        # Colour preview canvas
        self.lower_color_canvas = tk.Canvas(
            entry_row_l, width=30, height=20, bg="black", highlightthickness=0
        )
        self.lower_color_canvas.pack(side="left", padx=(5,0))

        # Attach live preview updates to all three variables
        for var in (self.lower_h_var, self.lower_s_var, self.lower_v_var):
            var.trace_add('write', lambda *args: self._update_lower_preview())

        # ---- Upper HSV row ----
        upper_row = ctk.CTkFrame(detect_frame, fg_color="transparent")
        upper_row.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(upper_row, text="Upper HSV", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,2))

        entry_row_u = ctk.CTkFrame(upper_row, fg_color="transparent")
        entry_row_u.pack(fill="x", pady=2)

        ctk.CTkLabel(entry_row_u, text="H", width=15).pack(side="left")
        self.upper_h_entry = ctk.CTkEntry(
            entry_row_u, textvariable=self.upper_h_var, width=40,
            justify="center", font=ctk.CTkFont(size=11)
        )
        self.upper_h_entry.pack(side="left", padx=(2,5))

        ctk.CTkLabel(entry_row_u, text="S", width=15).pack(side="left")
        self.upper_s_entry = ctk.CTkEntry(
            entry_row_u, textvariable=self.upper_s_var, width=40,
            justify="center", font=ctk.CTkFont(size=11)
        )
        self.upper_s_entry.pack(side="left", padx=(2,5))

        ctk.CTkLabel(entry_row_u, text="V", width=15).pack(side="left")
        self.upper_v_entry = ctk.CTkEntry(
            entry_row_u, textvariable=self.upper_v_var, width=40,
            justify="center", font=ctk.CTkFont(size=11)
        )
        self.upper_v_entry.pack(side="left", padx=(2,5))

        self.upper_color_canvas = tk.Canvas(
            entry_row_u, width=30, height=20, bg="black", highlightthickness=0
        )
        self.upper_color_canvas.pack(side="left", padx=(5,0))

        for var in (self.upper_h_var, self.upper_s_var, self.upper_v_var):
            var.trace_add('write', lambda *args: self._update_upper_preview())

        # Initial preview updates
        self._update_lower_preview()
        self._update_upper_preview()

        # ====== Aim Settings section ======
        aim_header = ctk.CTkLabel(self.frame, text="Aim Settings",
                                  font=ctk.CTkFont(size=13, weight="bold"))
        aim_header.pack(pady=(15, 5), anchor="center")

        aim_frame = ctk.CTkFrame(self.frame)
        aim_frame.pack(pady=5, fill="x", padx=20)

        # Smooth factor
        smooth_row = ctk.CTkFrame(aim_frame, fg_color="transparent")
        smooth_row.pack(fill="x", pady=3)
        ctk.CTkLabel(smooth_row, text="Smooth", width=60).pack(side="left")
        self.smooth_var = ctk.DoubleVar(value=0.2)
        self.smooth_slider = ctk.CTkSlider(smooth_row, from_=0.01, to=1.0,
                                           variable=self.smooth_var, number_of_steps=100)
        self.smooth_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.smooth_value_label = ctk.CTkLabel(smooth_row, width=35, text="0.20")
        self.smooth_value_label.pack(side="left")
        self.smooth_slider.configure(command=self._update_smooth_label)

        # Confidence
        conf_row = ctk.CTkFrame(aim_frame, fg_color="transparent")
        conf_row.pack(fill="x", pady=3)
        ctk.CTkLabel(conf_row, text="Confidence", width=60).pack(side="left")
        self.confidence_var = ctk.IntVar(value=80)
        self.confidence_slider = ctk.CTkSlider(
            conf_row, from_=0, to=100, number_of_steps=100,
            variable=self.confidence_var, command=self._update_confidence_label
        )
        self.confidence_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.confidence_value_label = ctk.CTkLabel(conf_row, width=30, text="80%")
        self.confidence_value_label.pack(side="left")

        # Activation key
        key_row = ctk.CTkFrame(aim_frame, fg_color="transparent")
        key_row.pack(fill="x", pady=3)
        ctk.CTkLabel(key_row, text="Act. Key", width=60).pack(side="left")
        self.activation_key_var = ctk.StringVar(value="alt_l")
        self.activation_key_entry = ctk.CTkEntry(
            key_row,
            textvariable=self.activation_key_var,
            width=80
        )
        self.activation_key_entry.pack(side="left", padx=5)

        # ====== Region of Interest section ======
        roi_header = ctk.CTkLabel(self.frame, text="Region of Interest",
                                  font=ctk.CTkFont(size=13, weight="bold"))
        roi_header.pack(pady=(15, 5), anchor="center")

        roi_frame = ctk.CTkFrame(self.frame)
        roi_frame.pack(pady=5, fill="x", padx=20)

        self.roi_enabled_var = ctk.BooleanVar(value=False)
        self.roi_checkbox = ctk.CTkCheckBox(
            roi_frame,
            text="Enable ROI (search around mouse)",
            variable=self.roi_enabled_var,
            command=self._toggle_roi
        )
        self.roi_checkbox.pack(pady=(5, 0))

        radius_row = ctk.CTkFrame(roi_frame, fg_color="transparent")
        radius_row.pack(fill="x", pady=5)
        ctk.CTkLabel(radius_row, text="Radius", width=50).pack(side="left")
        self.roi_radius_var = ctk.IntVar(value=150)
        self.roi_radius_slider = ctk.CTkSlider(
            radius_row, from_=20, to=500, number_of_steps=480,
            variable=self.roi_radius_var, command=self._update_roi_radius_label
        )
        self.roi_radius_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.roi_radius_label = ctk.CTkLabel(radius_row, width=40, text="150")
        self.roi_radius_label.pack(side="left")

        # ====== Action buttons ======
        button_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        button_row.pack(pady=(15, 5), anchor="center")

        self.aimbot_apply_btn = ctk.CTkButton(
            button_row,
            text="Apply Settings",
            command=self.apply_aimbot_settings,
            width=120,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.aimbot_apply_btn.pack(side="left", padx=(0, 10))

        self.reset_defaults_btn = ctk.CTkButton(
            button_row,
            text="Reset to Defaults",
            command=self._reset_to_defaults,
            width=140,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.reset_defaults_btn.pack(side="left")

    # --- Preview helpers (standard scale → RGB) ---
    def _hsv_to_hex(self, h: int, s: int, v: int) -> str:
        """
        Convert HSV from standard colour-picker ranges
        (H: 0-360°, S: 0-100%, V: 0-100%) to a hex RGB colour.
        """
        import colorsys
        h_norm = (h % 360) / 360.0
        s_norm = min(max(s, 0), 100) / 100.0
        v_norm = min(max(v, 0), 100) / 100.0
        r, g, b = colorsys.hsv_to_rgb(h_norm, s_norm, v_norm)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def _update_lower_preview(self) -> None:
        if self.lower_color_canvas:
            try:
                h = int(self.lower_h_var.get())
                s = int(self.lower_s_var.get())
                v = int(self.lower_v_var.get())
                color = self._hsv_to_hex(h, s, v)
                self.lower_color_canvas.configure(bg=color)
            except (ValueError, AttributeError):
                self.lower_color_canvas.configure(bg="black")

    def _update_upper_preview(self) -> None:
        if self.upper_color_canvas:
            try:
                h = int(self.upper_h_var.get())
                s = int(self.upper_s_var.get())
                v = int(self.upper_v_var.get())
                color = self._hsv_to_hex(h, s, v)
                self.upper_color_canvas.configure(bg=color)
            except (ValueError, AttributeError):
                self.upper_color_canvas.configure(bg="black")

    # --- Standard → OpenCV conversion helpers ---
    @staticmethod
    def _to_opencv_hsv(h_std: int, s_pct: int, v_pct: int):
        """
        Convert standard HSV (0-360, 0-100%, 0-100%) to OpenCV's
        internal ranges: H [0-179], S [0-255], V [0-255].
        """
        h_cv = max(0, min(179, int(h_std) // 2))
        s_cv = max(0, min(255, int(s_pct * 255 / 100)))
        v_cv = max(0, min(255, int(v_pct * 255 / 100)))
        return h_cv, s_cv, v_cv

    def _update_smooth_label(self, value) -> None:
        self.smooth_value_label.configure(text=f"{float(value):.2f}")

    def _update_confidence_label(self, value) -> None:
        self.confidence_value_label.configure(text=f"{int(float(value))}%")

    def _update_roi_radius_label(self, value) -> None:
        self.roi_radius_label.configure(text=str(int(float(value))))

    def _toggle_roi(self) -> None:
        enabled = self.roi_enabled_var.get()
        if 'aimbot' in self.app.workers:
            try:
                self.app.workers['aimbot'].set_roi_enabled(enabled)
                if enabled:
                    radius = self.roi_radius_var.get()
                    self.app.workers['aimbot'].set_roi_radius(radius)
                self.ui_queue.put_nowait({'type': 'status', 'message': f'ROI mode {"ON" if enabled else "OFF"}'})
            except Exception as e:
                logging.error(f"Failed to toggle ROI: {e}")

    def toggle_aimbot(self) -> None:
        try:
            worker_name = 'aimbot'
            if worker_name not in self.app.workers:
                self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot worker not available'})
                return
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Processing aimbot...'})
            if self.app.is_worker_running(worker_name):
                success = self.app.stop_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'aimbot', 'state': False})
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot: STOPPED'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to stop aimbot'})
            else:
                success = self.app.start_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'aimbot', 'state': True})
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot: RUNNING'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to start aimbot'})
        except Exception as e:
            logging.error(f"Toggle aimbot error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def apply_aimbot_settings(self) -> None:
        """
        Gather all settings, convert HSV from standard to OpenCV scale,
        and push to the aimbot worker.
        """
        try:
            if 'aimbot' not in self.app.workers:
                self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot module not loaded'})
                return
            aimbot = self.app.workers['aimbot']

            # Parse and validate HSV entries (standard scale)
            try:
                lower_h = int(self.lower_h_var.get())
                lower_s = int(self.lower_s_var.get())
                lower_v = int(self.lower_v_var.get())
                upper_h = int(self.upper_h_var.get())
                upper_s = int(self.upper_s_var.get())
                upper_v = int(self.upper_v_var.get())

                # Clamp to standard ranges
                lower_h = max(0, min(360, lower_h))
                lower_s = max(0, min(100, lower_s))
                lower_v = max(0, min(100, lower_v))
                upper_h = max(0, min(360, upper_h))
                upper_s = max(0, min(100, upper_s))
                upper_v = max(0, min(100, upper_v))
            except ValueError:
                self.ui_queue.put_nowait({'type': 'status', 'message': 'Invalid HSV values (must be integers)'})
                return

            # Convert to OpenCV scale
            lower_cv = self._to_opencv_hsv(lower_h, lower_s, lower_v)
            upper_cv = self._to_opencv_hsv(upper_h, upper_s, upper_v)

            if hasattr(aimbot, 'set_hsv_range'):
                aimbot.set_hsv_range(lower_cv, upper_cv)

            if hasattr(aimbot, 'set_smooth_factor'):
                aimbot.set_smooth_factor(self.smooth_var.get())

            if hasattr(aimbot, 'set_confidence'):
                conf = self.confidence_var.get() / 100.0
                aimbot.set_confidence(conf)

            if hasattr(aimbot, 'set_activation_key'):
                aimbot.set_activation_key(self.activation_key_var.get())

            if hasattr(aimbot, 'set_roi_enabled'):
                aimbot.set_roi_enabled(self.roi_enabled_var.get())
            if hasattr(aimbot, 'set_roi_radius'):
                aimbot.set_roi_radius(self.roi_radius_var.get())

            logging.info(f"Aimbot settings applied (standard HSV: "
                         f"lower=({lower_h}°, {lower_s}%, {lower_v}%), "
                         f"upper=({upper_h}°, {upper_s}%, {upper_v}%)")
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot settings applied'})
        except Exception as e:
            logging.error(f"Apply aimbot settings error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def _reset_to_defaults(self) -> None:
        """Reset HSV to defaults in standard scale and apply."""
        try:
            self.lower_h_var.set("0")
            self.lower_s_var.set("47")
            self.lower_v_var.set("27")
            self.upper_h_var.set("20")
            self.upper_s_var.set("100")
            self.upper_v_var.set("100")
            # Previews update automatically via trace
            self.apply_aimbot_settings()
            self.ui_queue.put_nowait({'type': 'status', 'message': 'HSV reset to defaults and applied'})
        except Exception as e:
            logging.error(f"Reset to defaults error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Reset error: {str(e)[:50]}'})

    def update_worker_button(self, worker: str, is_running: bool) -> None:
        if worker == 'aimbot':
            if is_running:
                self.aimbot_btn.configure(text="Aimbot: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.aimbot_btn.configure(text="Aimbot: (off)", fg_color="#dc3545", hover_color="#c82333")