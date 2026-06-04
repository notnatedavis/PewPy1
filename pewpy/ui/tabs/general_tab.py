#   pewpy/ui/tabs/general_tab.py
#   General tab: title, placeholders, status bar, and a separate debug window
#   with live logging and diagnostics.

# ----- Imports ----- #
import customtkinter as ctk
import logging
import threading
import time
import tkinter as tk
from .base_tab import BaseTab

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
    """Standalone window that displays live diagnostics and logs from PewPy."""
    def __init__(self, master=None, ui_queue=None):
        super().__init__(master)
        self.ui_queue = ui_queue
        self.title("PewPy Debug Console")
        self.geometry("600x500")
        self.minsize(500, 400)
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

        self._closed = False
        self._log_buffer = []       # keep last 500 lines
        self._max_log_lines = 500

    def update_stats(self, data: dict) -> None:
        if self._closed:
            return
        lines = []
        # Worker summary
        w = data.get('workers', {})
        lines.append(f"--- Workers ({w.get('running_workers', 0)}/{w.get('total_workers', 0)}) ---")
        for name, info in w.get('worker_details', {}).items():
            state = info.get('state', '?')
            alive = "alive" if info.get('thread_alive') else "dead"
            runtime = info.get('runtime_seconds', 0)
            errors = info.get('error_count', 0)
            lines.append(f"  {name}: {state} ({alive}) | {runtime:.1f}s | errors:{errors}")

        # System
        lines.append(f"CPU: {data.get('cpu', 'N/A')}%")
        lines.append(f"RAM: {data.get('mem', 'N/A')}%")
        lines.append(f"Resource Manager: {'ON' if data.get('rm_running') else 'OFF'}")

        if 'error' in data:
            lines.append(f"ERROR: {data['error']}")

        text = "\n".join(lines)
        if not self._closed:
            self.after(0, self._update_text, self.stats_text, text)

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

# ----- Main General Tab -----
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
            self.debug_window = DebugWindow(self.frame.winfo_toplevel(), self.ui_queue)
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