#   pewpy/ui/overlays/stats_overlay.py
#   Stats overlay – top‑right diagnostic panel (text drawn with GDI)

# ----- Imports ----- 
import logging
from typing import Dict, Any, List
import ctypes
from ctypes import wintypes, byref
from .base_overlay import _NativeOverlay
from .win32_helpers import (
    user32, gdi32, SetWindowPos,
    BeginPaint, EndPaint, PAINTSTRUCT,
    CreateCompatibleDC, CreateCompatibleBitmap, SelectObject,
    DeleteDC, DeleteObject, BitBlt, SRCCOPY,
    FillRect, SetBkMode, SetTextColor, DrawTextW,
    DT_LEFT, DT_TOP, DT_NOCLIP
)

# ----- Main Class ----- #
class StatsOverlay(_NativeOverlay) :
    def __init__(self, master=None, opacity: float = 0.7,
                 position: str = "top-right", size: tuple = (300, 300)) -> None:
        self.size = size
        self.position = position
        self._lines: List[str] = []
        super().__init__(opacity, class_name="PewPyStatsOverlay")

        if self._hwnd :
            screen_w = user32.GetSystemMetrics(0)
            x = screen_w - self.size[0] - 10
            y = 40
            SetWindowPos(self._hwnd, None, x, y,
                         self.size[0], self.size[1], 0)

    def update(self, data: Dict[str, Any]) -> None :
        lines = []
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
        if not self._hwnd : return

        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._hwnd, byref(ps))
        if not hdc : return

        rect = ps.rcPaint
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        mem_dc = CreateCompatibleDC(hdc)
        bmp = CreateCompatibleBitmap(hdc, w, h)
        old_bmp = SelectObject(mem_dc, bmp)

        brush = gdi32.CreateSolidBrush(0x00000000)
        FillRect(mem_dc, byref(rect), brush)
        gdi32.DeleteObject(brush)

        SetBkMode(mem_dc, 1)
        SetTextColor(mem_dc, 0x00FFFFFF)
        font = gdi32.GetStockObject(11)
        old_font = SelectObject(mem_dc, font)

        with self._data_lock:
            lines = list(self._lines)

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

        SelectObject(mem_dc, old_font)
        BitBlt(hdc, 0, 0, w, h, mem_dc, 0, 0, SRCCOPY)

        SelectObject(mem_dc, old_bmp)
        DeleteObject(bmp)
        DeleteDC(mem_dc)

        EndPaint(self._hwnd, byref(ps))