#   pewpy/ui/overlays.py
#   Native Win32 overlay windows – click‑through, double‑buffered, robust

#   Architecture : 
#   Instead of trying to make Tkinter windows transparent to mouse events,
#   build pure Win32 layered windows.  Each overlay has its own message
#   pump thread, so it never blocks the main GUI

#   Key design points :
#   • A single, shared window procedure (_overlay_wndproc) handles all
#     overlays via a global HWND→instance map
#   • WM_NCHITTEST returns HTTRANSPARENT – every overlay is invisible to
#     mouse clicks, solving the “click‑through” problem once and for all
#   • Painting uses the standard BeginPaint/EndPaint pair (validates the
#     update region) and a GDI memory‑DC for flicker‑free double‑buffering
#   • All GDI calls are drawn onto the memory DC and BitBlt’d to the screen
#     in one operation
#   • WPARAM / LPARAM are defined with pointer‑sized ctypes types so that
#     DefWindowProcW never receives an OverflowError on 64‑bit Windows

#   Overlay classes
#   _NativeOverlay – base class: window creation, message loop, show/hide/destroy
#   StatsOverlay   – top‑right diagnostic panel (text drawn with GDI)
#   ScreenOverlay  – full‑screen canvas for bounding boxes & crosshairs

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
    # wintypes.WPARAM / LPARAM are sometimes 32‑bit even on x64; we need
    # types that exactly match the size of a pointer so that message parameters
    # that are handles or pointers don’t cause OverflowError
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

    # WPARAM is unsigned int size of a pointer (UINT_PTR)
    # LPARAM is signed int size of a pointer (LONG_PTR)
    if ctypes.sizeof(ctypes.c_void_p) == 8 :
        WPARAM_T = ctypes.c_ulonglong
        LPARAM_T = ctypes.c_longlong
    else :
        WPARAM_T = wintypes.WPARAM
        LPARAM_T = wintypes.LPARAM

    # 2. Window styles and constants 
    CS_HREDRAW = 0x0002
    CS_VREDRAW = 0x0001
    WS_POPUP = 0x80000000                  # no title bar, borderless
    WS_EX_LAYERED = 0x00080000             # required for SetLayeredWindowAttributes
    WS_EX_TOPMOST = 0x00000008             # always on top
    WS_EX_TOOLWINDOW = 0x00000080          # doesn't appear in taskbar

    SW_SHOW = 5
    SW_HIDE = 0

    LWA_ALPHA = 0x00000002                 # set the whole window’s alpha

    # Standard messages we care about
    WM_NCHITTEST = 0x0084
    WM_PAINT = 0x000F
    WM_DESTROY = 0x0002
    WM_CLOSE = 0x0010
    WM_USER = 0x0400
    WM_OVERLAY_REPAINT = WM_USER + 1       # custom message for thread‑safe repaint

    HTTRANSPARENT = -1                     # click passes through to windows below

    # GDI constants
    SRCCOPY = 0x00CC0020                   # BitBlt raster operation
    DT_LEFT = 0x00000000
    DT_TOP = 0x00000000
    DT_NOCLIP = 0x00000100

    # 3. Window procedure type – uses the pointer‑sized parameter types
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

    # 5. Load Win32 API functions from the appropriate DLLs
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    gdi32 = ctypes.windll.gdi32

    # -- Window management --
    RegisterClassExW = user32.RegisterClassExW
    CreateWindowExW = user32.CreateWindowExW
    # Explicitly set argtypes & restype for DefWindowProcW to avoid OverflowError
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

    # FillRect lives in user32, **not** gdi32 (common pitfall)
    FillRect = user32.FillRect

    # -- GDI --
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

    # Obtain the module instance for registering the window class
    hinst = kernel32.GetModuleHandleW(None)

    # 6. Global map: HWND value → overlay instance
    #    Allows the single wndproc to dispatch to the correct overlay object
    _overlay_refs: Dict[int, object] = {}

    # 7. Shared window procedure
    #    Every overlay window uses this function (responsible for) :
    #      • making the window click‑through (WM_NCHITTEST → HTTRANSPARENT)
    #      • forwarding WM_PAINT to the overlay’s _on_paint method
    #      • translating our custom WM_OVERLAY_REPAINT into an InvalidateRect
    #      • posting WM_QUIT on WM_DESTROY / WM_CLOSE
    #    Any unexpected exception is caught to prevent the message pump from
    #    crashing, and all other messages are passed to DefWindowProcW
    @WNDPROC
    def _overlay_wndproc(hwnd, msg, wparam, lparam) :
        overlay = _overlay_refs.get(hwnd)  # None during creation
        try :
            if msg == WM_NCHITTEST :
                # The whole window is transparent to mouse input.
                return HTTRANSPARENT

            elif msg == WM_PAINT :
                if overlay :
                    try :
                        overlay._on_paint()
                    except Exception as e :
                        # paint errors are logged but must not kill the pump
                        logging.error(f"Overlay paint failed (hwnd=0x{hwnd:X}): {e}", exc_info=True)
                return 0

            elif msg == WM_OVERLAY_REPAINT :
                # thread‑safe request: invalidate the entire client area
                if hwnd :
                    InvalidateRect(hwnd, None, True)
                return 0

            elif msg in (WM_DESTROY, WM_CLOSE) :
                PostQuitMessage(0)
                return 0

        except Exception as e :
            logging.error(f"wndproc internal error (msg={msg}): {e}", exc_info=True)

        # pass everything else to the default handler
        return DefWindowProcW(hwnd, msg, wparam, lparam)

    # 8. Base class for native overlays
    class _NativeOverlay :
        # Common functionality for a Win32 overlay window
        # Creates a borderless, top‑most, layered popup with its own message loop
        # Subclasses override _on_paint() to do the actual drawing

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
            # Register the window class, create the window, and start the message loop
            wc = WNDCLASSEXW()
            wc.cbSize = sizeof(WNDCLASSEXW)
            wc.style = CS_HREDRAW | CS_VREDRAW
            wc.lpfnWndProc = _overlay_wndproc
            wc.hInstance = hinst
            wc.lpszClassName = self._class_name
            wc.hbrBackground = ctypes.cast(0, HBRUSH)  # paint everything ourselves manually
            RegisterClassExW(byref(wc))

            hwnd = CreateWindowExW(
                WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
                self._class_name,
                "",
                WS_POPUP,
                0, 0, 100, 100,           # initial size; adjusted later
                None, None, hinst, None
            )
            if not hwnd :
                logging.error(f"Failed to create overlay window ({self._class_name})")
                return
            self._hwnd = hwnd
            _overlay_refs[hwnd] = self

            # Set the whole window’s alpha to achieve the desired opacity.
            alpha_byte = int(self.opacity * 255)
            SetLayeredWindowAttributes(hwnd, 0, alpha_byte, LWA_ALPHA)

            # Launch the message pump in a daemon thread.
            self._running = True
            self._thread = threading.Thread(target=self._message_loop,
                                            name=f"Overlay-{self._class_name}",
                                            daemon=True)
            self._thread.start()
            logging.debug("Native overlay window created (HWND: 0x%X)", hwnd)

        def _message_loop(self) -> None :
            # Standard Windows message loop (runs in a background thread)
            msg = MSG()
            while self._running and GetMessageW(byref(msg), None, 0, 0) != 0:
                TranslateMessage(byref(msg))
                DispatchMessageW(byref(msg))
            # Clean up the window handle when the loop exits.
            if self._hwnd:
                hwnd = self._hwnd
                self._hwnd = None
                _overlay_refs.pop(hwnd, None)
                DestroyWindow(hwnd)
            logging.debug("Overlay message loop ended")

        def show(self) -> None :
            # Make the overlay visible
            if self._hwnd :
                ShowWindow(self._hwnd, SW_SHOW)
                self._visible = True

        def hide(self) -> None :
            # Hide the overlay
            if self._hwnd :
                ShowWindow(self._hwnd, SW_HIDE)
                self._visible = False

        def is_visible(self) -> bool :
            return self._visible

        def destroy(self) -> None :
            # Signal the message loop to exit and wait for the thread
            if self._running :
                self._running = False
                PostQuitMessage(0)
            if self._thread and self._thread.is_alive() : 
                self._thread.join(timeout=1.0)

        def _post_repaint(self) -> None :
            # Ask the message loop to schedule a WM_PAINT
            # Safe to call from any thread – it just posts our custom message
            
            if self._hwnd :
                PostMessageW(self._hwnd, WM_OVERLAY_REPAINT, 0, 0)

        def _on_paint(self) -> None :
            # Override in subclasses to perform GDI drawing
            pass

else :
    # Dummy classes for non‑Windows platforms – no‑ops so the rest of the app
    # doesn’t crash on import
    class _NativeOverlay :
        def __init__(self, opacity, class_name): pass
        def show(self): pass
        def hide(self): pass
        def destroy(self): pass
        def _post_repaint(self): pass

# 9. StatsOverlay – text‑based diagnostics panel (top‑right corner)
class StatsOverlay(_NativeOverlay) :
    # A borderless, semi‑transparent window that displays live worker and system
    # statistics using GDI text drawing.  Fully click‑through

    def __init__(self, master=None, opacity: float = 0.7,
                 position: str = "top-right", size: tuple = (300, 300)) -> None:
        self.size = size
        self.position = position
        self._lines: List[str] = []            # cached text lines
        super().__init__(opacity, class_name="PewPyStatsOverlay")

        # Position the window in the top‑right corner (10 px margin).
        if self._hwnd :
            screen_w = user32.GetSystemMetrics(0)   # SM_CXSCREEN
            x = screen_w - self.size[0] - 10
            y = 40
            SetWindowPos(self._hwnd, None, x, y,
                         self.size[0], self.size[1], 0)

    def update(self, data: Dict[str, Any]) -> None :
        # Thread‑safe update of the displayed text lines
        lines = []
        # Worker summary
        w = data.get('workers', {})
        lines.append(f"--- Workers ({w.get('running_workers', 0)}/{w.get('total_workers', 0)}) ---")
        for name, info in w.get('worker_details', {}).items():
            state = info.get('state', '?')
            alive = "alive" if info.get('thread_alive') else "dead"
            runtime = info.get('runtime_seconds', 0)
            errors = info.get('error_count', 0)
            lines.append(f"  {name}: {state} ({alive})")
            lines.append(f"    up {runtime:.1f}s | err:{errors}")

        lines.append(f"CPU: {data.get('cpu', 'N/A')}%")
        lines.append(f"RAM: {data.get('mem', 'N/A')}%")
        lines.append(f"ResMgr: {'ON' if data.get('rm_running') else 'OFF'}")

        if 'error' in data :
            lines.append(f"ERROR: {data['error']}")

        with self._data_lock :
            self._lines = lines
        self._post_repaint()

    def _on_paint(self) -> None :
        # GDI paint handler
        # Uses BeginPaint/EndPaint to properly validate the update region,
        # and double‑buffering through a memory DC to eliminate flicker
        
        if not self._hwnd : 
            return

        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._hwnd, byref(ps))
        if not hdc :
            return

        # ----- Double‑buffer setup -----
        rect = ps.rcPaint
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        mem_dc = CreateCompatibleDC(hdc)
        bmp = CreateCompatibleBitmap(hdc, w, h)
        old_bmp = SelectObject(mem_dc, bmp)

        # ----- Clear background -----
        brush = gdi32.CreateSolidBrush(0x00000000)  # black
        FillRect(mem_dc, byref(rect), brush)        # FillRect is from user32 (correct)
        gdi32.DeleteObject(brush)

        # ----- Text setup -----
        SetBkMode(mem_dc, 1)                         # TRANSPARENT
        SetTextColor(mem_dc, 0x00FFFFFF)             # white
        font = gdi32.GetStockObject(11)              # SYSTEM_FIXED_FONT
        old_font = SelectObject(mem_dc, font)

        with self._data_lock:
            lines = list(self._lines)

        # ----- Draw each line -----
        line_height = 16
        y_pos = 4
        for line in lines:
            text_rect = wintypes.RECT()
            text_rect.left = 4
            text_rect.top = y_pos
            text_rect.right = w - 4
            text_rect.bottom = y_pos + line_height
            DrawTextW(mem_dc, line, -1, byref(text_rect),
                      DT_LEFT | DT_TOP | DT_NOCLIP)
            y_pos += line_height

        # ----- Blit to screen -----
        SelectObject(mem_dc, old_font)
        BitBlt(hdc, 0, 0, w, h, mem_dc, 0, 0, SRCCOPY)

        # ----- Clean up double‑buffer -----
        SelectObject(mem_dc, old_bmp)
        DeleteObject(bmp)
        DeleteDC(mem_dc)

        # ----- Validate the update region -----
        EndPaint(self._hwnd, byref(ps))

# 10. ScreenOverlay – full‑screen drawing canvas
class ScreenOverlay(_NativeOverlay) :
    # Full‑screen, semi‑transparent overlay that can draw bounding boxes,
    # crosshairs, and other visual indicators.  All mouse events pass through
    # to the windows underneath
    def __init__(self, master=None, opacity: float = 0.4) -> None :
        self._shapes: Dict[str, Any] = {}
        super().__init__(opacity, class_name="PewPyScreenOverlay")

        # Size to the full virtual screen
        if self._hwnd :
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            SetWindowPos(self._hwnd, None, 0, 0,
                         screen_w, screen_h, 0)

    def update_drawings(self, data: Dict[str, Any]) -> None :
        # Thread‑safe update of the drawing commands (bbox, mouse position, etc.)

        with self._data_lock :
            self._shapes = data.copy()
        self._post_repaint()

    def _on_paint(self) -> None :
        # GDI paint handler
        # Clears the background to black, then draws a red bounding box and a
        # green crosshair based on the latest shape data
        # Uses double‑buffering and BeginPaint/EndPaint just like StatsOverlay
        
        if not self._hwnd :
            return

        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._hwnd, byref(ps))
        if not hdc:
            return

        # ----- Double‑buffer -----
        rect = ps.rcPaint
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        mem_dc = CreateCompatibleDC(hdc)
        bmp = CreateCompatibleBitmap(hdc, w, h)
        old_bmp = SelectObject(mem_dc, bmp)

        # ----- Clear -----
        brush = gdi32.CreateSolidBrush(0x00000000)
        FillRect(mem_dc, byref(rect), brush)          # user32.FillRect
        gdi32.DeleteObject(brush)

        # ----- Pens -----
        red_pen = CreatePen(0, 2, 0x000000FF)         # PS_SOLID, red
        green_pen = CreatePen(0, 2, 0x0000FF00)       # PS_SOLID, green
        old_pen = SelectObject(mem_dc, red_pen)

        with self._data_lock:
            shapes = dict(self._shapes)

        # ----- Bounding box -----
        bbox = shapes.get('bbox')
        if bbox and len(bbox) == 4:
            x, y, bw, bh = bbox
            SelectObject(mem_dc, red_pen)
            Rectangle(mem_dc, x, y, x + bw, y + bh)

        # ----- Crosshair at mouse position -----
        mouse_pos = shapes.get('mouse_pos')
        if mouse_pos and len(mouse_pos) == 2:
            mx, my = mouse_pos
            r = 10
            SelectObject(mem_dc, green_pen)
            MoveToEx(mem_dc, mx - r, my, None)
            LineTo(mem_dc, mx + r, my)
            MoveToEx(mem_dc, mx, my - r, None)
            LineTo(mem_dc, mx, my + r)

        # ----- Restore and blit -----
        SelectObject(mem_dc, old_pen)
        DeleteObject(red_pen)
        DeleteObject(green_pen)

        BitBlt(hdc, 0, 0, w, h, mem_dc, 0, 0, SRCCOPY)

        SelectObject(mem_dc, old_bmp)
        DeleteObject(bmp)
        DeleteDC(mem_dc)

        EndPaint(self._hwnd, byref(ps))