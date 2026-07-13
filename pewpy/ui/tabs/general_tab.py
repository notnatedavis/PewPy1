#   pewpy/ui/tabs/general_tab.py
#   General tab: title, placeholders, status bar, and a separate debug window
#   with live logging and diagnostics, plus detection debug tab.
#   Extended with Hue Detection and Avoid Colors tabs

# ----- Imports ----- #
import customtkinter as ctk
import logging
import threading
import time
import queue
from .base_tab import BaseTab
from .debug_window import DebugWindow, DebugWindowHandler

# ----- Main General Tab ----- #
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

            try:
                self.ui_queue.put_nowait({'type': 'debug_data', 'data': data})
            except queue.Full:
                logging.warning("UI queue full, dropping diagnostic data")
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