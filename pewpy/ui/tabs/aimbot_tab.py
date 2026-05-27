#   pewpy/ui/tabs/aimbot_tab.py
#   Aimbot tab: toggle, full HSV range sliders (H, S, V) with preview
#   smooth factor, confidence, activation key, ROI mode & radius, apply,
#   and a reset‑to‑defaults button that restores permissive config ranges

# ----- Imports ----- #
import customtkinter as ctk
import logging
from .base_tab import BaseTab
import tkinter as tk

# ----- Main Class ----- #
class AimbotTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        # Internal colour preview canvases will be created inside _create_widgets
        self.lower_color_canvas = None
        self.upper_color_canvas = None
        super().__init__(parent_tab, app, ui_queue)

    def _create_widgets(self) -> None:
        # Toggle button (existing)
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
        self.aimbot_btn.pack(pady=(20, 20), anchor="center")

        # ----- Lower Bound Color (hue slider + preview) -----
        lower_frame = ctk.CTkFrame(self.frame, width=300)
        lower_frame.pack(pady=5, anchor="center")

        ctk.CTkLabel(lower_frame, text="Lower Hue").pack(side="left", padx=5)
        self.lower_hue_var = ctk.IntVar(value=0)
        self.lower_hue_slider = ctk.CTkSlider(
            lower_frame, from_=0, to=180, number_of_steps=180,
            variable=self.lower_hue_var, command=self._update_lower_preview
        )
        self.lower_hue_slider.pack(side="left", fill="x", expand=True, padx=5)

        # Small canvas to show the chosen colour (hue only, full sat & val assumed)
        self.lower_color_canvas = tk.Canvas(
            lower_frame, width=30, height=20, bg="black", highlightthickness=0
        )
        self.lower_color_canvas.pack(side="left", padx=(5, 0))

        # ----- Upper Bound Color (hue slider + preview) -----
        upper_frame = ctk.CTkFrame(self.frame, width=300)
        upper_frame.pack(pady=5, anchor="center")

        ctk.CTkLabel(upper_frame, text="Upper Hue").pack(side="left", padx=5)
        self.upper_hue_var = ctk.IntVar(value=10)
        self.upper_hue_slider = ctk.CTkSlider(
            upper_frame, from_=0, to=180, number_of_steps=180,
            variable=self.upper_hue_var, command=self._update_upper_preview
        )
        self.upper_hue_slider.pack(side="left", fill="x", expand=True, padx=5)

        self.upper_color_canvas = tk.Canvas(
            upper_frame, width=30, height=20, bg="black", highlightthickness=0
        )
        self.upper_color_canvas.pack(side="left", padx=(5, 0))

        # Trigger initial preview
        self._update_lower_preview(self.lower_hue_var.get())
        self._update_upper_preview(self.upper_hue_var.get())

        # ----- Lower Saturation -----
        lower_sat_frame = ctk.CTkFrame(self.frame, width=300)
        lower_sat_frame.pack(pady=5, anchor="center")
        ctk.CTkLabel(lower_sat_frame, text="Lower Sat").pack(side="left", padx=5)
        self.lower_sat_var = ctk.IntVar(value=120)
        self.lower_sat_slider = ctk.CTkSlider(
            lower_sat_frame, from_=0, to=255, number_of_steps=256,
            variable=self.lower_sat_var
        )
        self.lower_sat_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.lower_sat_label = ctk.CTkLabel(lower_sat_frame, width=40, text="120")
        self.lower_sat_label.pack(side="left", padx=5)
        # Wire label update after creation (no factory call)
        self.lower_sat_slider.configure(command=self._update_lower_sat_label)

        # ----- Lower Value -----
        lower_val_frame = ctk.CTkFrame(self.frame, width=300)
        lower_val_frame.pack(pady=5, anchor="center")
        ctk.CTkLabel(lower_val_frame, text="Lower Val").pack(side="left", padx=5)
        self.lower_val_var = ctk.IntVar(value=70)
        self.lower_val_slider = ctk.CTkSlider(
            lower_val_frame, from_=0, to=255, number_of_steps=256,
            variable=self.lower_val_var
        )
        self.lower_val_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.lower_val_label = ctk.CTkLabel(lower_val_frame, width=40, text="70")
        self.lower_val_label.pack(side="left", padx=5)
        self.lower_val_slider.configure(command=self._update_lower_val_label)

        # ----- Upper Saturation -----
        upper_sat_frame = ctk.CTkFrame(self.frame, width=300)
        upper_sat_frame.pack(pady=5, anchor="center")
        ctk.CTkLabel(upper_sat_frame, text="Upper Sat").pack(side="left", padx=5)
        self.upper_sat_var = ctk.IntVar(value=255)
        self.upper_sat_slider = ctk.CTkSlider(
            upper_sat_frame, from_=0, to=255, number_of_steps=256,
            variable=self.upper_sat_var
        )
        self.upper_sat_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.upper_sat_label = ctk.CTkLabel(upper_sat_frame, width=40, text="255")
        self.upper_sat_label.pack(side="left", padx=5)
        self.upper_sat_slider.configure(command=self._update_upper_sat_label)

        # ----- Upper Value -----
        upper_val_frame = ctk.CTkFrame(self.frame, width=300)
        upper_val_frame.pack(pady=5, anchor="center")
        ctk.CTkLabel(upper_val_frame, text="Upper Val").pack(side="left", padx=5)
        self.upper_val_var = ctk.IntVar(value=255)
        self.upper_val_slider = ctk.CTkSlider(
            upper_val_frame, from_=0, to=255, number_of_steps=256,
            variable=self.upper_val_var
        )
        self.upper_val_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.upper_val_label = ctk.CTkLabel(upper_val_frame, width=40, text="255")
        self.upper_val_label.pack(side="left", padx=5)
        self.upper_val_slider.configure(command=self._update_upper_val_label)

        # ----- Smooth factor slider (existing) -----
        smooth_frame = ctk.CTkFrame(self.frame, width=300)
        smooth_frame.pack(pady=10, anchor="center")
        ctk.CTkLabel(smooth_frame, text="Smooth Factor:").pack(side="left", padx=5)
        self.smooth_var = ctk.DoubleVar(value=0.2)
        self.smooth_slider = ctk.CTkSlider(smooth_frame, from_=0.01, to=1.0,
                                           variable=self.smooth_var, number_of_steps=100)
        self.smooth_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.smooth_value_label = ctk.CTkLabel(smooth_frame, width=40, text="0.20")
        self.smooth_value_label.pack(side="left", padx=5)
        self.smooth_slider.configure(command=self._update_smooth_label)

        # ----- Confidence slider (new) -----
        confidence_frame = ctk.CTkFrame(self.frame, width=300)
        confidence_frame.pack(pady=10, anchor="center")
        ctk.CTkLabel(confidence_frame, text="Confidence:").pack(side="left", padx=5)
        self.confidence_var = ctk.IntVar(value=80)
        self.confidence_slider = ctk.CTkSlider(
            confidence_frame, from_=0, to=100, number_of_steps=100,
            variable=self.confidence_var, command=self._update_confidence_label
        )
        self.confidence_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.confidence_value_label = ctk.CTkLabel(confidence_frame, width=40, text="80%")
        self.confidence_value_label.pack(side="left", padx=5)

        # ----- Activation key entry (existing) -----
        activation_frame = ctk.CTkFrame(self.frame, width=300)
        activation_frame.pack(pady=10, anchor="center")
        ctk.CTkLabel(activation_frame, text="Activation Key:").pack(side="left", padx=5)
        self.activation_key_var = ctk.StringVar(value="alt_l")
        self.activation_key_entry = ctk.CTkEntry(
            activation_frame,
            textvariable=self.activation_key_var,
            width=80
        )
        self.activation_key_entry.pack(side="left", padx=5)

        # ----- ROI (Region of Interest) controls -----
        roi_frame = ctk.CTkFrame(self.frame, width=300)
        roi_frame.pack(pady=10, anchor="center")

        self.roi_enabled_var = ctk.BooleanVar(value=False)
        self.roi_checkbox = ctk.CTkCheckBox(
            roi_frame,
            text="ROI Mode (search around mouse)",
            variable=self.roi_enabled_var,
            command=self._toggle_roi
        )
        self.roi_checkbox.pack(pady=(5, 0))

        radius_frame = ctk.CTkFrame(roi_frame, fg_color="transparent")
        radius_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(radius_frame, text="ROI Radius (px):").pack(side="left", padx=5)
        self.roi_radius_var = ctk.IntVar(value=150)
        self.roi_radius_slider = ctk.CTkSlider(
            radius_frame, from_=20, to=500, number_of_steps=480,
            variable=self.roi_radius_var, command=self._update_roi_radius_label
        )
        self.roi_radius_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.roi_radius_label = ctk.CTkLabel(radius_frame, width=50, text="150")
        self.roi_radius_label.pack(side="left", padx=5)

        # ----- Button row: Apply Settings + Reset to Defaults -----
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

    # --- Color preview helpers (hue only) ---
    def _hue_to_hex(self, hue: int) -> str:
        # Convert an OpenCV hue (0-180) to a fully saturated RGB hex string for preview.
        # OpenCV hue is half of standard 0-360, so multiply by 2.
        import colorsys
        # normalize to 0-1, convert to RGB 0-255
        r, g, b = colorsys.hsv_to_rgb(hue / 360.0 * 2, 1.0, 1.0)  # hue/180*360 = hue*2
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def _update_lower_preview(self, value=None):
        if self.lower_color_canvas:
            hue = int(self.lower_hue_var.get()) if value is None else int(float(value))
            self.lower_color_canvas.configure(bg=self._hue_to_hex(hue))

    def _update_upper_preview(self, value=None):
        if self.upper_color_canvas:
            hue = int(self.upper_hue_var.get()) if value is None else int(float(value))
            self.upper_color_canvas.configure(bg=self._hue_to_hex(hue))

    # --- Label updaters for S/V sliders ---
    def _update_lower_sat_label(self, value):
        self.lower_sat_label.configure(text=str(int(float(value))))

    def _update_lower_val_label(self, value):
        self.lower_val_label.configure(text=str(int(float(value))))

    def _update_upper_sat_label(self, value):
        self.upper_sat_label.configure(text=str(int(float(value))))

    def _update_upper_val_label(self, value):
        self.upper_val_label.configure(text=str(int(float(value))))

    def _update_smooth_label(self, value) -> None:
        self.smooth_value_label.configure(text=f"{float(value):.2f}")

    def _update_confidence_label(self, value) -> None:
        self.confidence_value_label.configure(text=f"{int(float(value))}%")

    def _update_roi_radius_label(self, value) -> None:
        self.roi_radius_label.configure(text=str(int(float(value))))

    def _toggle_roi(self) -> None:
        enabled = self.roi_enabled_var.get()
        # Apply immediately if aimbot worker exists
        if 'aimbot' in self.app.workers:
            try:
                self.app.workers['aimbot'].set_roi_enabled(enabled)
                if enabled:
                    radius = self.roi_radius_var.get()
                    self.app.workers['aimbot'].set_roi_radius(radius)
                self.ui_queue.put_nowait({'type': 'status', 'message': f'ROI mode {"ON" if enabled else "OFF"}'})
            except Exception as e:
                logging.error(f"Failed to toggle ROI: {e}")

    # --- methods ---
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
        """Gather all HSV parameters (now including saturation and value) and apply to the aimbot worker."""
        try:
            if 'aimbot' not in self.app.workers:
                self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot module not loaded'})
                return
            aimbot = self.app.workers['aimbot']

            # Full HSV tuples
            lower = (
                int(self.lower_hue_var.get()),
                int(self.lower_sat_var.get()),
                int(self.lower_val_var.get())
            )
            upper = (
                int(self.upper_hue_var.get()),
                int(self.upper_sat_var.get()),
                int(self.upper_val_var.get())
            )
            if hasattr(aimbot, 'set_hsv_range'):
                aimbot.set_hsv_range(lower, upper)

            # Smooth factor
            if hasattr(aimbot, 'set_smooth_factor'):
                aimbot.set_smooth_factor(self.smooth_var.get())

            # Confidence
            if hasattr(aimbot, 'set_confidence'):
                conf = self.confidence_var.get() / 100.0
                aimbot.set_confidence(conf)

            # Activation key
            if hasattr(aimbot, 'set_activation_key'):
                aimbot.set_activation_key(self.activation_key_var.get())

            # ROI settings
            if hasattr(aimbot, 'set_roi_enabled'):
                aimbot.set_roi_enabled(self.roi_enabled_var.get())
            if hasattr(aimbot, 'set_roi_radius'):
                aimbot.set_roi_radius(self.roi_radius_var.get())

            logging.info("Aimbot settings applied")
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot settings applied'})
        except Exception as e:
            logging.error(f"Apply aimbot settings error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def _reset_to_defaults(self) -> None:
        """Reset all HSV sliders to the original permissive defaults from config/default.yaml
        (H: 0‑10, S: 120‑255, V: 70‑255) and apply them immediately."""
        try:
            # Set sliders
            self.lower_hue_var.set(0)
            self.upper_hue_var.set(10)
            self.lower_sat_var.set(120)
            self.lower_val_var.set(70)
            self.upper_sat_var.set(255)
            self.upper_val_var.set(255)

            # Update labels (hue preview already triggered by setter? hue canvases need manual call)
            self._update_lower_preview(0)
            self._update_upper_preview(10)
            self._update_lower_sat_label(120)
            self._update_lower_val_label(70)
            self._update_upper_sat_label(255)
            self._update_upper_val_label(255)

            # Apply to worker
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