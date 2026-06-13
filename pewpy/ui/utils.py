#   pewpy/ui/utils.py
#   Reusable helpers for the CustomTkinter UI

# ----- Imports ----- #
import customtkinter as ctk

# ----- Main ----- #
def create_content_frame(parent) -> ctk.CTkFrame:
    """
    Create a frame that fills the entire parent area and expands with it.
    This should be used as the base container for any tab content.
    """
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.pack(fill="both", expand=True)
    return outer

# Keep old name for backward compatibility if needed, but mark as deprecated
def create_centered_frame(parent) -> ctk.CTkFrame:
    """Deprecated: use create_content_frame instead."""
    return create_content_frame(parent)