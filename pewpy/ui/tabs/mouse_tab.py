#   pewpy/ui/tabs/mouse_tab.py
#   Mouse tab: auto-clicker toggle, interval entry, placeholders

# ----- Imports ----- #
import customtkinter as ctk
import logging
from .base_tab import BaseTab

# ----- Main Class ----- #
class MouseTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        super().__init__(parent_tab, app, ui_queue)

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

        # Placeholder buttons
        self.mouse_placeholder1 = ctk.CTkButton(
            self.frame,
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

    def update_worker_button(self, worker: str, is_running: bool) -> None:
        if worker == 'auto_clicker':
            if is_running:
                self.auto_clicker_btn.configure(text="Auto-Clicker: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.auto_clicker_btn.configure(text="Auto-Clicker: (off)", fg_color="#dc3545", hover_color="#c82333")

    def _placeholder_action(self, name: str) -> None:
        logging.info(f"Placeholder '{name}' clicked")