# pewpy/ui/tabs/debug_window.py
# Debug console window with live logs, detection debug, hue detection and avoid colors

# ----- Imports -----
import customtkinter as ctk
import logging
import threading
import time
import tkinter as tk
from datetime import datetime
import queue

# ----- Helper -----
class DebugWindowHandler(logging.Handler):
    # ... (unchanged)

# ----- Main -----
class DebugWindow(ctk.CTkToplevel):
    def __init__(self, master=None, ui_queue=None, aimbot_ref=None):
        # ... (unchanged)
    # ... all methods (_setup_detection_tab, _scan_colors, etc.)