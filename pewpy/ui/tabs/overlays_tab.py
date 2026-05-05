# pewpy/ui/tabs/overlays_tab.py
#   Overlays tab: stats overlay toggle, screen overlay toggle, placeholders

# ----- Imports ----- 
import customtkinter as ctk
import logging
import queue
from .base_tab import BaseTab

# ----- Main Class ----- 
class OverlaysTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue: queue.Queue):
        super().__init__(parent_tab, app, ui_queue)

    def _create_widgets(self) -> None:
        # Stats Overlay button
        self.overlay_btn = ctk.CTkButton(
            self.frame,
            text="Stats Overlay: (off)",
            command=self.toggle_overlay,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.overlay_btn.pack(pady=(20, 10), anchor="center")

        # Screen Overlay button
        self.screen_overlay_btn = ctk.CTkButton(
            self.frame,
            text="Screen Overlay: (off)",
            command=self.toggle_screen_overlay,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.screen_overlay_btn.pack(pady=6, anchor="center")

        # Placeholder button
        self.overlay_placeholder2 = ctk.CTkButton(
            self.frame,
            text="Placeholder B",
            command=lambda: self._placeholder_action("Placeholder B"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.overlay_placeholder2.pack(pady=6, anchor="center")

    # --- toggle methods ---
    def toggle_overlay(self) -> None:
        try:
            worker_name = 'overlay'
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Processing overlay...'})
            if self.app.is_worker_running(worker_name):
                success = self.app.stop_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'overlay', 'state': False})
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Overlay: STOPPED'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to stop overlay'})
            else:
                success = self.app.start_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'overlay', 'state': True})
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Overlay: RUNNING'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to start overlay'})
        except Exception as e:
            logging.error(f"Toggle overlay error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def toggle_screen_overlay(self) -> None:
        try:
            worker_name = 'screen_overlay'
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Processing screen overlay...'})
            if self.app.is_worker_running(worker_name):
                success = self.app.stop_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'screen_overlay', 'state': False})
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Screen overlay: STOPPED'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to stop screen overlay'})
            else:
                success = self.app.start_worker(worker_name)
                if success:
                    self.ui_queue.put_nowait({'type': 'worker_state', 'worker': 'screen_overlay', 'state': True})
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Screen overlay: RUNNING'})
                else:
                    self.ui_queue.put_nowait({'type': 'status', 'message': 'Error: Failed to start screen overlay'})
        except Exception as e:
            logging.error(f"Toggle screen overlay error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def update_worker_button(self, worker: str, is_running: bool) -> None:
        if worker == 'overlay':
            if is_running:
                self.overlay_btn.configure(text="Stats Overlay: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.overlay_btn.configure(text="Stats Overlay: (off)", fg_color="#6c757d", hover_color="#5a6268")
        elif worker == 'screen_overlay':
            if is_running:
                self.screen_overlay_btn.configure(text="Screen Overlay: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.screen_overlay_btn.configure(text="Screen Overlay: (off)", fg_color="#6c757d", hover_color="#5a6268")

    def _placeholder_action(self, name: str) -> None:
        logging.info(f"Placeholder '{name}' clicked")