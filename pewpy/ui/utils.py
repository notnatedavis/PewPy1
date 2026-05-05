#   pewpy/ui/utils.py
#   Reusable helpers for the CustomTkinter UI

# ----- Imports ----- #
import customtkinter as ctk

# ----- Main ----- #
def create_centered_frame(parent) -> ctk.CTkFrame :
    # Create a frame that centers its content horizontally and vertically
    # inside the given parent.

    # Returns the inner (content) frame where widgets should be placed
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.grid(row=0, column=0, sticky="nsew")
    outer.grid_rowconfigure(0, weight=1)   # top stretch
    outer.grid_columnconfigure(0, weight=1)

    center_frame = ctk.CTkFrame(outer, fg_color="transparent")
    center_frame.grid(row=0, column=0, sticky="")

    # Additional weight rows to keep center_frame centered
    outer.grid_rowconfigure(0, weight=1)
    outer.grid_rowconfigure(2, weight=1)

    return center_frame