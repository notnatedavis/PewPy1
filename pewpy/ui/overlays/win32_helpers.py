#   pewpy/ui/overlays/win32_helpers.py
#   Win32 definitions, constants, and the shared window procedure
#   for native layered overlay windows.

# ----- Imports ----- 
import threading
import logging
import platform
import struct
from typing import Dict, Any, Optional, List, Tuple
import ctypes
from ctypes import wintypes, byref, sizeof, c_void_p

# ===== Platform‑specific Win32 helpers (Windows only) =====
if platform.system() == "Windows" :
    # 1. Ensure pointer‑sized integer types exist
    if not hasattr(wintypes, "LONG_PTR") :
        if struct.calcsize("P") == 8:
            LONG_PTR = ctypes.c_longlong
        else :
            LONG_PTR = ctypes.c_long
    else :
        LONG_PTR = wintypes.LONG_PTR

    if not hasattr(wintypes, "LRESULT") :
        LRESULT = LONG_PTR
    else :
        LRESULT = wintypes.LRESULT

    # HBRUSH is just a handle; declare as void pointer
    HBRUSH = ctypes.c_void_p

    # WPARAM / LPARAM sized for pointer width
    if ctypes.sizeof(ctypes.c_void_p) == 8 :
        WPARAM_T = ctypes.c_ulonglong
        LPARAM_T = ctypes.c_longlong
    else :
        WPARAM_T = wintypes.WPARAM
        LPARAM_T = wintypes.LPARAM

    # 2. Window styles and constants 
    CS_HREDRAW = 0x0002
    CS_VREDRAW = 0x0001
    WS_POPUP = 0x80000000
    WS_EX_LAYERED = 0x00080000
    WS_EX_TOPMOST = 0x00000008
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_TRANSPARENT = 0x00000020

    SW_SHOW = 5
    SW_HIDE = 0

    LWA_ALPHA = 0x00000002

    WM_NCHITTEST = 0x0084
    WM_PAINT = 0x000F
    WM_DESTROY = 0x0002
    WM_CLOSE = 0x0010
    WM_USER = 0x0400
    WM_OVERLAY_REPAINT = WM_USER + 1

    HTTRANSPARENT = -1

    SRCCOPY = 0x00CC0020
    DT_LEFT = 0x00000000
    DT_TOP = 0x00000000
    DT_NOCLIP = 0x00000100

    # 3. Window procedure type
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT,
                                 wintypes.HWND,
                                 wintypes.UINT,
                                 WPARAM_T,
                                 LPARAM_T)

    # 4. Structures
    class PAINTSTRUCT(ctypes.Structure):
        _fields_ = [("hdc", wintypes.HDC),
                    ("fErase", wintypes.BOOL),
                    ("rcPaint", wintypes.RECT),
                    ("fRestore", wintypes.BOOL),
                    ("fIncUpdate", wintypes.BOOL),
                    ("rgbReserved", wintypes.BYTE * 32)]

    class MSG(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND),
                    ("message", wintypes.UINT),
                    ("wParam", WPARAM_T),
                    ("lParam", LPARAM_T),
                    ("time", wintypes.DWORD),
                    ("pt", wintypes.POINT)]

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HCURSOR),
            ("hbrBackground", HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
            ("hIconSm", wintypes.HICON),
        ]

    # 5. Load Win32 API functions
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    gdi32 = ctypes.windll.gdi32

    RegisterClassExW = user32.RegisterClassExW
    CreateWindowExW = user32.CreateWindowExW
    DefWindowProcW = user32.DefWindowProcW
    DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM_T, LPARAM_T]
    DefWindowProcW.restype = LRESULT

    GetMessageW = user32.GetMessageW
    TranslateMessage = user32.TranslateMessage
    DispatchMessageW = user32.DispatchMessageW
    PostQuitMessage = user32.PostQuitMessage
    ShowWindow = user32.ShowWindow
    DestroyWindow = user32.DestroyWindow
    SetLayeredWindowAttributes = user32.SetLayeredWindowAttributes
    InvalidateRect = user32.InvalidateRect
    PostMessageW = user32.PostMessageW
    GetDC = user32.GetDC
    ReleaseDC = user32.ReleaseDC
    BeginPaint = user32.BeginPaint
    EndPaint = user32.EndPaint
    SetWindowPos = user32.SetWindowPos
    FillRect = user32.FillRect

    CreateCompatibleDC = gdi32.CreateCompatibleDC
    CreateCompatibleBitmap = gdi32.CreateCompatibleBitmap
    SelectObject = gdi32.SelectObject
    DeleteDC = gdi32.DeleteDC
    DeleteObject = gdi32.DeleteObject
    BitBlt = gdi32.BitBlt
    SetBkMode = gdi32.SetBkMode
    SetTextColor = gdi32.SetTextColor
    DrawTextW = user32.DrawTextW
    MoveToEx = gdi32.MoveToEx
    LineTo = gdi32.LineTo
    CreatePen = gdi32.CreatePen
    Rectangle = gdi32.Rectangle
    Ellipse = gdi32.Ellipse
    StretchDIBits = gdi32.StretchDIBits          # <--- ADDED: needed by MaskOverlay

    hinst = kernel32.GetModuleHandleW(None)

    # 6. Global map: HWND value → overlay instance
    _overlay_refs: Dict[int, object] = {}

    # 7. Shared window procedure
    @WNDPROC
    def _overlay_wndproc(hwnd, msg, wparam, lparam) :
        overlay = _overlay_refs.get(hwnd)
        try :
            if msg == WM_NCHITTEST :
                return HTTRANSPARENT

            elif msg == WM_PAINT :
                if overlay :
                    try :
                        overlay._on_paint()
                    except Exception as e :
                        logging.error(f"Overlay paint failed (hwnd=0x{hwnd:X}): {e}", exc_info=True)
                return 0

            elif msg == WM_OVERLAY_REPAINT :
                if hwnd :
                    InvalidateRect(hwnd, None, True)
                return 0

            elif msg in (WM_DESTROY, WM_CLOSE) :
                PostQuitMessage(0)
                return 0

        except Exception as e :
            logging.error(f"wndproc internal error (msg={msg}): {e}", exc_info=True)

        return DefWindowProcW(hwnd, msg, wparam, lparam)

else :
    # Dummy placeholders for non‑Windows platforms
    user32 = None
    kernel32 = None
    gdi32 = None
    hinst = None
    _overlay_refs = {}
    def _overlay_wndproc(hwnd, msg, wparam, lparam) : return 0
    # Other symbols can be set to None as needed
    WNDPROC = None
    WNDCLASSEXW = None
    PAINTSTRUCT = None
    MSG = None