#   pewpy/ui/tabs/general_tab.py
#   General tab: title, placeholders, status bar, and live debug panel

# ----- Imports ----- #
import customtkinter as ctk
import logging
import threading
import time
from .base_tab import BaseTab

# ----- Main Class ----- #
class GeneralTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        super().__init__(parent_tab, app, ui_queue)
        self._diagnostics_running = False
        self._diagnostics_thread = None

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

        # ------------------ Debug Panel ------------------
        self.debug_visible = False
        self.debug_toggle_btn = ctk.CTkButton(
            self.frame,
            text="Show Debug",
            command=self._toggle_debug_panel,
            width=120,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.debug_toggle_btn.pack(pady=(0, 5), anchor="center")

        # Debug frame (initially hidden)
        self.debug_frame = ctk.CTkFrame(self.frame, fg_color="#2b2b2b")
        self.debug_text = ctk.CTkTextbox(
            self.debug_frame,
            width=380,
            height=200,
            fg_color="#1e1e1e",
            text_color="#cccccc",
            font=ctk.CTkFont(size=10, family="Courier"),
            state="disabled"
        )
        self.debug_text.pack(fill="both", expand=True, padx=5, pady=5)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _placeholder_action(self, name: str) -> None:
        logging.info(f"Placeholder '{name}' clicked")

    # --- Debug panel toggling ---
    def _toggle_debug_panel(self) -> None:
        self.debug_visible = not self.debug_visible
        if self.debug_visible:
            self.debug_frame.pack(pady=(0, 10), anchor="center", fill="both", expand=True)
            self.debug_toggle_btn.configure(text="Hide Debug")
            self._start_diagnostics()
        else:
            self.debug_frame.pack_forget()
            self.debug_toggle_btn.configure(text="Show Debug")
            self._stop_diagnostics()

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

    def _stop_diagnostics(self) -> None :
        self._diagnostics_running = False
        if self._diagnostics_thread and self._diagnostics_thread.is_alive():
            self._diagnostics_thread.join(timeout=1.0)

    def _diagnostics_loop(self) -> None :
        while self._diagnostics_running : 
            data = {}
            try :
                # Worker stats
                data['workers'] = self.app.thread_manager.get_worker_stats()

                # System stats
                try :
                    import psutil
                    data['cpu'] = psutil.cpu_percent(interval=0.1)
                    data['mem'] = psutil.virtual_memory().percent
                except Exception :
                    data['cpu'] = 'N/A'
                    data['mem'] = 'N/A'

                # Resource manager status
                data['rm_running'] = self.app.resource_manager.running

            except Exception as e:
                data['error'] = str(e)

            self.ui_queue.put_nowait({'type': 'debug_data', 'data': data})
            time.sleep(2)

    def update_debug_info(self, data: dict) -> None :
        # Format the collected diagnostics and display in the textbox
        if not self.debug_visible:
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

        # Update the widget in a thread‑safe manner
        self.debug_text.configure(state="normal")
        self.debug_text.delete("1.0", "end")
        self.debug_text.insert("1.0", text)
        self.debug_text.configure(state="disabled")