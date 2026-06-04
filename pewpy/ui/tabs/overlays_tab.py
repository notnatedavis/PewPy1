# pewpy/ui/tabs/overlays_tab.py
#   Overlays tab: stats overlay toggle, screen overlay toggle,
#   mouse outline toggle, target render toggle, and placeholder.

# ----- Imports ----- 
import customtkinter as ctk
import logging
import queue
from .base_tab import BaseTab

# ----- Main Class ----- 
class OverlaysTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue: queue.Queue, main_window=None):
        self.main_window = main_window  # reference to ModernMainWindow
        super().__init__(parent_tab, app, ui_queue)

    def _create_widgets(self) -> None:
        # Stats Overlay button
        self.overlay_btn = ctk.CTkButton(
            self.frame,
            text="Stats Overlay: (off)",
            command=self.toggle_stats_overlay,
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

        # Mouse Outline button
        self.mouse_outline_btn = ctk.CTkButton(
            self.frame,
            text="Mouse Outline: (off)",
            command=self.toggle_mouse_outline,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.mouse_outline_btn.pack(pady=6, anchor="center")

        # Target Render toggle button
        self.target_render_btn = ctk.CTkButton(
            self.frame,
            text="Target Render: (off)",
            command=self.toggle_target_render,
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.target_render_btn.pack(pady=6, anchor="center")

        # Placeholder button
        self.placeholder_btn = ctk.CTkButton(
            self.frame,
            text="Placeholder Button",
            command=lambda: self._placeholder_action("Placeholder B"),
            width=180,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.placeholder_btn.pack(pady=6, anchor="center")

    # --- toggle methods ---
    def toggle_stats_overlay(self) -> None:
        if not self.main_window:
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Main window reference missing'})
            return
        try:
            self.main_window.toggle_stats_overlay()
        except Exception as e:
            logging.error(f"Toggle stats overlay error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def toggle_screen_overlay(self) -> None:
        if not self.main_window:
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Main window reference missing'})
            return
        try:
            self.main_window.toggle_screen_overlay()
        except Exception as e:
            logging.error(f"Toggle screen overlay error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def toggle_mouse_outline(self) -> None:
        if not self.main_window:
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Main window reference missing'})
            return
        try:
            self.main_window.toggle_mouse_outline()
        except Exception as e:
            logging.error(f"Toggle mouse outline error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def toggle_target_render(self) -> None:
        if not self.main_window:
            self.ui_queue.put_nowait({'type': 'status', 'message': 'Main window reference missing'})
            return
        try:
            self.main_window.toggle_target_render()
        except Exception as e:
            logging.error(f"Toggle target render error: {e}")
            self.ui_queue.put_nowait({'type': 'status', 'message': f'Error: {str(e)[:50]}'})

    def set_overlay_button_state(self, overlay_type: str, is_active: bool) -> None:
        if overlay_type == 'stats':
            if is_active:
                self.overlay_btn.configure(text="Stats Overlay: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.overlay_btn.configure(text="Stats Overlay: (off)", fg_color="#6c757d", hover_color="#5a6268")
        elif overlay_type == 'screen':
            if is_active:
                self.screen_overlay_btn.configure(text="Screen Overlay: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.screen_overlay_btn.configure(text="Screen Overlay: (off)", fg_color="#6c757d", hover_color="#5a6268")
        elif overlay_type == 'mouse_outline':
            if is_active:
                self.mouse_outline_btn.configure(text="Mouse Outline: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.mouse_outline_btn.configure(text="Mouse Outline: (off)", fg_color="#6c757d", hover_color="#5a6268")
        elif overlay_type == 'target_render':
            if is_active:
                self.target_render_btn.configure(text="Target Render: (on)", fg_color="#28a745", hover_color="#218838")
            else:
                self.target_render_btn.configure(text="Target Render: (off)", fg_color="#6c757d", hover_color="#5a6268")

    def _placeholder_action(self, name: str) -> None:
        logging.info(f"Placeholder '{name}' clicked")