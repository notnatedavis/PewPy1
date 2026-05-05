#   pewpy/ui/tabs/aimbot_tab.py
#   Aimbot tab: toggle, HSV range, smooth slider, activation key, apply

# ----- Imports ----- #
import customtkinter as ctk
import logging
from .base_tab import BaseTab

# ----- Main Class ----- #
class AimbotTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        super().__init__(parent_tab, app, ui_queue)

    def _create_widgets(self) -> None:
        # Toggle button
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

        # HSV Lower
        hsv_lower_frame = ctk.CTkFrame(self.frame, width=300)
        hsv_lower_frame.pack(pady=5, anchor="center")
        ctk.CTkLabel(hsv_lower_frame, text="HSV Lower (H,S,V)").pack(side="left", padx=5)
        self.hsv_lower_h = ctk.CTkEntry(hsv_lower_frame, width=50, placeholder_text="H")
        self.hsv_lower_s = ctk.CTkEntry(hsv_lower_frame, width=50, placeholder_text="S")
        self.hsv_lower_v = ctk.CTkEntry(hsv_lower_frame, width=50, placeholder_text="V")
        self.hsv_lower_h.pack(side="left", padx=2)
        self.hsv_lower_s.pack(side="left", padx=2)
        self.hsv_lower_v.pack(side="left", padx=2)
        self.hsv_lower_h.insert(0, "0")
        self.hsv_lower_s.insert(0, "120")
        self.hsv_lower_v.insert(0, "70")

        # HSV Upper
        hsv_upper_frame = ctk.CTkFrame(self.frame, width=300)
        hsv_upper_frame.pack(pady=5, anchor="center")
        ctk.CTkLabel(hsv_upper_frame, text="HSV Upper (H,S,V)").pack(side="left", padx=5)
        self.hsv_upper_h = ctk.CTkEntry(hsv_upper_frame, width=50, placeholder_text="H")
        self.hsv_upper_s = ctk.CTkEntry(hsv_upper_frame, width=50, placeholder_text="S")
        self.hsv_upper_v = ctk.CTkEntry(hsv_upper_frame, width=50, placeholder_text="V")
        self.hsv_upper_h.pack(side="left", padx=2)
        self.hsv_upper_s.pack(side="left", padx=2)
        self.hsv_upper_v.pack(side="left", padx=2)
        self.hsv_upper_h.insert(0, "10")
        self.hsv_upper_s.insert(0, "255")
        self.hsv_upper_v.insert(0, "255")

        # Smooth factor slider
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

        # Activation key entry
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

        # Apply button
        self.aimbot_apply_btn = ctk.CTkButton(
            self.frame,
            text="Apply Settings",
            command=self.apply_aimbot_settings,
            width=120,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.aimbot_apply_btn.pack(pady=(15, 5), anchor="center")

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
        try:
            if 'aimbot' not in self.app.workers:
                self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot module not loaded'})
                return
            aimbot = self.app.workers['aimbot']
            # HSV
            try:
                l_h = int(self.hsv_lower_h.get() or 0)
                l_s = int(self.hsv_lower_s.get() or 0)
                l_v = int(self.hsv_lower_v.get() or 0)
                u_h = int(self.hsv_upper_h.get() or 0)
                u_s = int(self.hsv_upper_s.get() or 0)
                u_v = int(self.hsv_upper_v.get() or 0)
                if hasattr(aimbot, 'set_hsv_range'):
                    aimbot.set_hsv_range((l_h, l_s, l_v), (u_h, u_s, u_v))
            except ValueError:
                pass
            # Smooth factor
            if hasattr(aimbot, 'set_smooth_factor'):
                aimbot.set_smooth_factor(self.smooth_var.get())
            # Activation key (now wired to worker)
            if hasattr(aimbot, 'set_activation_key'):
                aimbot.set_activation_key(self.activation_key_var.get())
            logging.info(f"Aimbot settings applied: activation key {self.activation_key_var.get()}")
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot settings applied'})
        except Exception as e:
            logging.error(f"Apply aimbot settings error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def _update_smooth_label(self, value) -> None:
        self.smooth_value_label.configure(text=f"{float(value):.2f}")

    def update_worker_button(self, worker: str, is_running: bool) -> None:
        if worker == 'aimbot':
            if is_running:
                self.aimbot_btn.configure(text="Aimbot: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.aimbot_btn.configure(text="Aimbot: (off)", fg_color="#dc3545", hover_color="#c82333")