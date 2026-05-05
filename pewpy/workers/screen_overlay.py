# pewpy/workers/screen_overlay.py
#   Full‑screen semi‑transparent overlay for visualisation / debugging

# ----- Imports ----- #
import threading
import logging
import tkinter as tk
from typing import Tuple

from .function_worker import BaseWorker

# ----- Main Class ----- #
class ScreenOverlay(BaseWorker) :
    # Covers the entire screen with a configurable colour and opacity
    
    def __init__(self,
                 color: str = "red",
                 opacity: float = 0.5):
        super().__init__(name="ScreenOverlay")
        self.color = color
        self.opacity = max(0.0, min(1.0, opacity))
        self._root: tk.Tk | None = None
        self._canvas: tk.Canvas | None = None
        self._running = False

    def _initialize_overlay(self) -> None :
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes('-topmost', True)
        self._root.attributes('-alpha', self.opacity)
        # Cover all monitors (span the virtual screen)
        self._root.geometry(f"{self._root.winfo_screenwidth()}x{self._root.winfo_screenheight()}+0+0")
        # Make the window click‑through (Windows only; macOS/Linux may need alternative)
        import platform
        if platform.system() == "Windows":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
                ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                ex_style |= 0x00000020  # WS_EX_TRANSPARENT
                ex_style |= 0x00080000  # WS_EX_LAYERED
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style)
            except Exception as e:
                logging.warning(f"Click‑through setup failed: {e}")

        self._canvas = tk.Canvas(self._root, bg=self.color, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self, stop_event: threading.Event, pause_event: threading.Event) -> None:
        self._running = True
        self._initialize_overlay()
        try:
            while self._running and not stop_event.is_set():
                pause_event.wait()
                # Keep the tkinter event loop alive
                try:
                    self._root.update_idletasks()
                    self._root.update()
                except tk.TclError:
                    break
                threading.Event().wait(0.05)
        finally:
            self._cleanup()

    def _on_close(self):
        self._running = False

    def _cleanup(self):
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
        self._running = False
        logging.debug("ScreenOverlay cleaned up")