#   src/workers/overlay.py
#   Overlay worker using tkinter (no pygame dependency)

import threading
import logging
import tkinter as tk
from typing import Dict, Any, Tuple

from .function_worker import BaseWorker

class Overlay(BaseWorker):
    def __init__(self,
                 position: Tuple[int, int] = (0, 0),
                 size: Tuple[int, int] = (300, 200),
                 opacity: float = 0.7):     # 0.0 (transparent) to 1.0 (opaque)
        super().__init__(name="Overlay")
        self.position = position
        self.size = size
        self.opacity = max(0.0, min(1.0, opacity))
        self._data_lock = threading.RLock()
        self.display_data: Dict[str, Any] = {}
        self._root = None
        self._label = None
        self._running = False   # local flag for the tk mainloop

    def _initialize_overlay(self) -> None:
        self._root = tk.Tk()
        self._root.overrideredirect(True)         # no window decorations
        self._root.attributes('-topmost', True)    # always on top
        self._root.attributes('-alpha', self.opacity)  # transparency (Windows & macOS)
        self._root.geometry(f"{self.size[0]}x{self.size[1]}+{self.position[0]}+{self.position[1]}")
        self._root.configure(bg='black')
        self._root.lift()

        # Make the window click‑through (Windows only)
        import platform
        if platform.system() == "Windows":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
                ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                ex_style |= 0x00000020  # WS_EX_TRANSPARENT
                ex_style |= 0x00080000  # WS_EX_LAYERED
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style)
            except Exception as e:
                logging.warning(f"Click‑through setup failed: {e}")

        self._label = tk.Label(
            self._root,
            text="PewPy Overlay",
            fg="white",
            bg="black",
            font=("Arial", 12)
        )
        self._label.pack(pady=10)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _render_frame(self) -> None:
        if not self._label:
            return
        with self._data_lock:
            data = self.display_data.copy() if self.display_data else {"Status": "Running", "FPS": "60"}
        text = "\n".join(f"{k}: {v}" for k, v in data.items())
        self._label.config(text=text)

    def _work_cycle(self) -> None:
        # The tkinter mainloop must run in the thread; we only need to process events.
        # This method is called repeatedly by BaseWorker, but we handle everything in run().
        pass

    def run(self, stop_event: threading.Event, pause_event: threading.Event) -> None:
        self._running = True
        self._initialize_overlay()
        # Process tkinter events until stop_event is set
        while self._running and not stop_event.is_set():
            pause_event.wait()   # respect pause
            try:
                self._root.update_idletasks()
                self._root.update()
                self._render_frame()
                # Sleep a tiny bit to avoid spinning the CPU
                threading.Event().wait(0.01)
            except tk.TclError:
                logging.info("Overlay window closed")
                break
        self._cleanup()

    def update_data(self, new_data: Dict[str, Any]) -> None:
        with self._data_lock:
            self.display_data.update(new_data)

    def clear_data(self) -> None:
        with self._data_lock:
            self.display_data.clear()

    def _on_close(self) -> None:
        self._running = False

    def _cleanup(self) -> None:
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
        self._running = False
        logging.debug("Overlay cleaned up")