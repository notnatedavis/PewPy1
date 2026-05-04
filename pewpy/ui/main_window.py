#   pewpy/ui/main_window.py
#   Modern CustomTkinter UI for PewPy - Three-tab interface

# ----- Imports ----- #
import threading
import time
import queue
import customtkinter as ctk
import logging
from typing import Optional, Dict, Any

# ----- Main Class ----- #
class ModernMainWindow :
    # Main application window with 3 tabs: (General, Aimbot, Mouse)

    def __init__(self, app) -> None :
        self.app = app

        # setup appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # create main window
        self.root = ctk.CTk()
        self.root.title("PewPy Control Panel")
        self.root.geometry("500x480")
        self.root.minsize(460, 380)

        # thread-safe communication
        self._ui_queue = queue.Queue(maxsize=50)
        self._update_thread: Optional[threading.Thread] = None
        self._running = True

        # setup UI
        self._setup_layout()
        self._create_widgets()

        # start UI updater
        self._start_ui_updater()

        # handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _setup_layout(self) -> None :
        # The whole window is a single CTkTabview
        self.tab_view = ctk.CTkTabview(self.root)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.general_tab = self.tab_view.add("General")
        self.aimbot_tab = self.tab_view.add("Aimbot")
        self.mouse_tab = self.tab_view.add("Mouse")

        # Configure each tab to allow a centered content frame
        for tab in (self.general_tab, self.aimbot_tab, self.mouse_tab):
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

    def _create_widgets(self) -> None :
        self._create_general_tab()
        self._create_aimbot_tab()
        self._create_mouse_tab()

    # Helper: creates a centered container frame inside a tab
    def _center_content_frame(self, parent) -> ctk.CTkFrame:
        # Outer frame fills the whole tab
        outer = ctk.CTkFrame(parent, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # Inner frame that will hold the actual widgets (centered)
        center_frame = ctk.CTkFrame(outer, fg_color="transparent")
        center_frame.grid(row=0, column=0, sticky="")

        # Add stretch rows/cols to keep the inner frame centered
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_rowconfigure(2, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        return center_frame

    def _create_general_tab(self) -> None :
        center_frame = self._center_content_frame(self.general_tab)

        # Title
        self.title_label = ctk.CTkLabel(
            center_frame,
            text="PewPy",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(pady=(0, 10), anchor="center")

        # Overlay toggle
        self.overlay_btn = ctk.CTkButton(
            center_frame,
            text="Overlay: OFF",
            command=self.toggle_overlay,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.overlay_btn.pack(pady=10, anchor="center")

        # placeholder buttons here (update future)
        self.placeholder_btn1 = ctk.CTkButton(
            center_frame,
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
            center_frame,
            text="Placeholder 2",
            command=lambda: self._placeholder_action("Placeholder 2"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.placeholder_btn2.pack(pady=6, anchor="center")

        # Status bar at the bottom
        self.status_var = ctk.StringVar(value="Ready - PewPy Online")
        self.status_bar = ctk.CTkLabel(
            center_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_bar.pack(pady=(20, 10), anchor="center")

    def _placeholder_action(self, name: str) -> None:
        """Placeholder action for the new buttons."""
        self._ui_queue.put_nowait({'type': 'status', 'message': f'{name} clicked (not implemented)'})

    def _create_aimbot_tab(self) -> None :
        center_frame = self._center_content_frame(self.aimbot_tab)

        # aimbot toggle button
        self.aimbot_btn = ctk.CTkButton(
            center_frame,
            text="Aimbot: OFF",
            command=self.toggle_aimbot,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.aimbot_btn.pack(pady=(20, 20), anchor="center")

        # HSV Lower
        hsv_lower_frame = ctk.CTkFrame(center_frame, width=300)
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
        hsv_upper_frame = ctk.CTkFrame(center_frame, width=300)
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
        smooth_frame = ctk.CTkFrame(center_frame, width=300)
        smooth_frame.pack(pady=10, anchor="center")
        ctk.CTkLabel(smooth_frame, text="Smooth Factor:").pack(side="left", padx=5)
        self.smooth_var = ctk.DoubleVar(value=0.2)
        self.smooth_slider = ctk.CTkSlider(smooth_frame, from_=0.01, to=1.0, variable=self.smooth_var, number_of_steps=100)
        self.smooth_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.smooth_value_label = ctk.CTkLabel(smooth_frame, width=40, text="0.20")
        self.smooth_value_label.pack(side="left", padx=5)
        self.smooth_slider.configure(command=self._update_smooth_label)

        # Activation key entry
        key_frame = ctk.CTkFrame(center_frame, width=300)
        key_frame.pack(pady=5, anchor="center")
        ctk.CTkLabel(key_frame, text="Activation Key:").pack(side="left", padx=5)
        self.activation_key_var = ctk.StringVar(value="alt_l")
        self.activation_key_entry = ctk.CTkEntry(key_frame, textvariable=self.activation_key_var, width=120)
        self.activation_key_entry.pack(side="left", padx=5)

        # Apply button
        self.aimbot_apply_btn = ctk.CTkButton(
            center_frame,
            text="Apply Settings",
            command=self.apply_aimbot_settings,
            width=120,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.aimbot_apply_btn.pack(pady=(15, 5), anchor="center")

    def _create_mouse_tab(self) -> None :
        center_frame = self._center_content_frame(self.mouse_tab)

        # Horizontal frame for Auto-Clicker button + interval entry
        top_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        top_frame.pack(pady=(30, 10), anchor="center")

        self.auto_clicker_btn = ctk.CTkButton(
            top_frame,
            text="Auto-Clicker: OFF",
            command=self.toggle_auto_clicker,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.auto_clicker_btn.pack(side="left", padx=(0, 10))

        # Interval entry (now to the right)
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

        # Two placeholder buttons below
        self.mouse_placeholder1 = ctk.CTkButton(
            center_frame,
            text="Placeholder A",
            command=lambda: self._placeholder_action("Placeholder A"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.mouse_placeholder1.pack(pady=10, anchor="center")

        self.mouse_placeholder2 = ctk.CTkButton(
            center_frame,
            text="Placeholder B",
            command=lambda: self._placeholder_action("Placeholder B"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.mouse_placeholder2.pack(pady=6, anchor="center")

    # ---------- (All original methods below remain unchanged) ----------

    def _start_ui_updater(self) -> None :
        self._update_thread = threading.Thread(
            target=self._process_ui_updates,
            name="UI-Updater",
            daemon=True
        )
        self._update_thread.start()

    def _process_ui_updates(self) -> None :
        while self._running :
            try :
                update = self._ui_queue.get(timeout=0.5)
                self.root.after(0, self._apply_ui_update, update)
            except queue.Empty :
                continue
            except Exception as e :
                logging.error(f"UI update error: {e}")

    def _apply_ui_update(self, update: Dict[str, Any]) -> None :
        try :
            update_type = update.get('type')
            if update_type == 'status' :
                self.status_var.set(update.get('message', ''))
            elif update_type == 'worker_state' :
                worker = update.get('worker')
                state = update.get('state')
                self._update_worker_button(worker, state)
        except Exception as e :
            logging.error(f"Failed to apply UI update: {e}")

    def toggle_auto_clicker(self) -> None :
        try :
            worker_name = 'auto_clicker'
            self._ui_queue.put_nowait({'type': 'status', 'message': 'Processing auto-clicker...'})
            if self.app.is_worker_running(worker_name) :
                success = self.app.stop_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({'type': 'worker_state', 'worker': 'auto_clicker', 'state': False})
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Auto-clicker: STOPPED'})
                else :
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to stop auto-clicker'})
            else :
                success = self.app.start_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({'type': 'worker_state', 'worker': 'auto_clicker', 'state': True})
                    interval = self.interval_var.get()
                    self._ui_queue.put_nowait({'type': 'status', 'message': f'Auto-clicker: RUNNING ({interval}s interval)'})
                else :
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to start auto-clicker'})
        except Exception as e :
            logging.error(f"Toggle auto-clicker error: {e}")
            self._ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def toggle_overlay(self) -> None :
        try :
            worker_name = 'overlay'
            self._ui_queue.put_nowait({'type': 'status', 'message': 'Processing overlay...'})
            if self.app.is_worker_running(worker_name) :
                success = self.app.stop_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({'type': 'worker_state', 'worker': 'overlay', 'state': False})
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Overlay: STOPPED'})
                else :
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to stop overlay'})
            else :
                success = self.app.start_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({'type': 'worker_state', 'worker': 'overlay', 'state': True})
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Overlay: RUNNING'})
                else :
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to start overlay'})
        except Exception as e :
            logging.error(f"Toggle overlay error: {e}")
            self._ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def toggle_aimbot(self) -> None :
        try :
            worker_name = 'aimbot'
            if worker_name not in self.app.workers :
                self._ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot worker not available'})
                return
            self._ui_queue.put_nowait({'type': 'status', 'message': 'Processing aimbot...'})
            if self.app.is_worker_running(worker_name) :
                success = self.app.stop_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({'type': 'worker_state', 'worker': 'aimbot', 'state': False})
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot: STOPPED'})
                else :
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to stop aimbot'})
            else :
                success = self.app.start_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({'type': 'worker_state', 'worker': 'aimbot', 'state': True})
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot: RUNNING'})
                else :
                    self._ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to start aimbot'})
        except Exception as e :
            logging.error(f"Toggle aimbot error: {e}")
            self._ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def apply_aimbot_settings(self) -> None :
        try :
            if 'aimbot' not in self.app.workers :
                self._ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot module not loaded'})
                return
            aimbot = self.app.workers['aimbot']
            try:
                l_h = int(self.hsv_lower_h.get() or 0)
                l_s = int(self.hsv_lower_s.get() or 0)
                l_v = int(self.hsv_lower_v.get() or 0)
                u_h = int(self.hsv_upper_h.get() or 0)
                u_s = int(self.hsv_upper_s.get() or 0)
                u_v = int(self.hsv_upper_v.get() or 0)
                if hasattr(aimbot, 'set_hsv_range'):
                    aimbot.set_hsv_range((l_h,l_s,l_v), (u_h,u_s,u_v))
            except ValueError:
                pass
            if hasattr(aimbot, 'set_smooth_factor'):
                aimbot.set_smooth_factor(self.smooth_var.get())
            logging.info(f"Aimbot settings applied: activation key {self.activation_key_var.get()}")
            self._ui_queue.put_nowait({'type': 'status', 'message': 'Aimbot settings applied'})
        except Exception as e :
            logging.error(f"Apply aimbot settings error: {e}")
            self._ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def _update_worker_button(self, worker: str, is_running: bool) -> None:
        try :
            if worker == 'auto_clicker' :
                if is_running :
                    self.auto_clicker_btn.configure(text="Auto-Clicker: ON", fg_color="#28a745", hover_color="#218838")
                else :
                    self.auto_clicker_btn.configure(text="Auto-Clicker: OFF", fg_color="#dc3545", hover_color="#c82333")
            elif worker == 'overlay' :
                if is_running :
                    self.overlay_btn.configure(text="Overlay: ON", fg_color="#28a745", hover_color="#218838")
                else :
                    self.overlay_btn.configure(text="Overlay: OFF", fg_color="#6c757d", hover_color="#5a6268")
            elif worker == 'aimbot' :
                if is_running :
                    self.aimbot_btn.configure(text="Aimbot: ON", fg_color="#28a745", hover_color="#218838")
                else :
                    self.aimbot_btn.configure(text="Aimbot: OFF", fg_color="#dc3545", hover_color="#c82333")
        except Exception as e :
            logging.error(f"Failed to update button: {e}")

    def _update_smooth_label(self, value) -> None :
        self.smooth_value_label.configure(text=f"{float(value):.2f}")

    def _update_interval(self, event=None) -> None :
        try :
            value = self.interval_var.get().strip()
            if not value :
                value = "0.1"
                self.interval_var.set(value)
            interval = float(value)
            interval = max(0.01, min(10.0, interval))
            if self.app.is_worker_running('auto_clicker') :
                worker = self.app.workers['auto_clicker']
                if hasattr(worker, 'set_interval') :
                    worker.set_interval(interval)
                    self._ui_queue.put_nowait({'type': 'status', 'message': f'Interval updated: {interval}s'})
        except ValueError as e :
            logging.error(f"Invalid interval: {e}")
            self.interval_var.set("0.1")
            self._ui_queue.put_nowait({'type': 'status', 'message': 'Invalid interval, reset to 0.1s'})

    def run(self) -> None :
        try :
            logging.info("Starting PewPy UI")
            self.root.mainloop()
        except Exception as e :
            logging.error(f"UI error: {e}")
            self.shutdown()

    def shutdown(self) -> None :
        logging.info("Shutting down PewPy UI")
        self._running = False
        self.app.stop_all()
        try :
            self.root.quit()
            self.root.destroy()
        except Exception as e :
            logging.debug(f"Window destruction: {e}")

# maintain backward compatibility
MainWindow = ModernMainWindow