#   pewpy/ui/tabs/general_tab.py
#   General tab: title, placeholders, status bar

# ----- Imports ----- #
import customtkinter as ctk
import logging
from .base_tab import BaseTab

# ----- Main Class ----- #
class GeneralTab(BaseTab):
    def __init__(self, parent_tab, app, ui_queue):
        super().__init__(parent_tab, app, ui_queue)

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

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _placeholder_action(self, name: str) -> None:
        logging.info(f"Placeholder '{name}' clicked")