#   pewpy/ui/overlays/base_overlay.py
#   Base class for native Win32 layered overlay windows

# ----- Imports ----- 
import threading
import logging
import platform
from typing import Optional
import ctypes            # <--- ADDED
from .win32_helpers import (
    user32, kernel32, gdi32, hinst,
    WNDCLASSEXW, CreateWindowExW, SetLayeredWindowAttributes,
    ShowWindow, DestroyWindow, PostQuitMessage, GetMessageW,
    TranslateMessage, DispatchMessageW, MSG, _overlay_refs, _overlay_wndproc,
    SW_SHOW, SW_HIDE, WS_POPUP, WS_EX_LAYERED, WS_EX_TOPMOST,
    WS_EX_TOOLWINDOW, WS_EX_TRANSPARENT, LWA_ALPHA,
    WM_OVERLAY_REPAINT, PostMessageW, InvalidateRect,
    DefWindowProcW
)

# ----- Base Class ----- #
class _NativeOverlay :
    def __init__(self, opacity: float, class_name: str) -> None :
        self.opacity = max(0.0, min(1.0, opacity))
        self._class_name = class_name
        self._hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._visible = False
        self._data_lock = threading.Lock()
        self._create_window()

    def _create_window(self) -> None : 
        if platform.system() != "Windows":
            return
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)        # now works
        wc.style = 0x0002 | 0x0001  # CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = _overlay_wndproc
        wc.hInstance = hinst
        wc.lpszClassName = self._class_name
        wc.hbrBackground = ctypes.cast(0, ctypes.c_void_p)
        user32.RegisterClassExW(ctypes.byref(wc))

        hwnd = CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT,
            self._class_name,
            "",
            WS_POPUP,
            0, 0, 100, 100,
            None, None, hinst, None
        )
        if not hwnd :
            logging.error(f"Failed to create overlay window ({self._class_name})")
            return
        self._hwnd = hwnd
        _overlay_refs[hwnd] = self

        alpha_byte = int(self.opacity * 255)
        SetLayeredWindowAttributes(hwnd, 0, alpha_byte, LWA_ALPHA)

        self._running = True
        self._thread = threading.Thread(target=self._message_loop,
                                        name=f"Overlay-{self._class_name}",
                                        daemon=True)
        self._thread.start()
        logging.debug("Native overlay window created (HWND: 0x%X)", hwnd)

    def _message_loop(self) -> None :
        msg = MSG()
        while self._running and GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            TranslateMessage(ctypes.byref(msg))
            DispatchMessageW(ctypes.byref(msg))
        if self._hwnd:
            hwnd = self._hwnd
            self._hwnd = None
            _overlay_refs.pop(hwnd, None)
            DestroyWindow(hwnd)
        logging.debug("Overlay message loop ended")

    def show(self) -> None :
        if self._hwnd :
            ShowWindow(self._hwnd, SW_SHOW)
            self._visible = True

    def hide(self) -> None :
        if self._hwnd :
            ShowWindow(self._hwnd, SW_HIDE)
            self._visible = False

    def is_visible(self) -> bool :
        return self._visible

    def destroy(self) -> None :
        if self._running :
            self._running = False
            PostQuitMessage(0)
        if self._thread and self._thread.is_alive() : 
            self._thread.join(timeout=1.0)

    def _post_repaint(self) -> None :
        if self._hwnd :
            PostMessageW(self._hwnd, WM_OVERLAY_REPAINT, 0, 0)

    def _on_paint(self) -> None :
        pass