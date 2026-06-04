#   pewpy/ui/overlays/mask_overlay.py
#   Mask overlay – debug preview of the detection mask

# ----- Imports ----- 
import logging
import numpy as np
import cv2
import ctypes
from ctypes import wintypes, byref
from .base_overlay import _NativeOverlay
from .win32_helpers import (
    user32, gdi32, SetWindowPos,
    BeginPaint, EndPaint, PAINTSTRUCT,
    CreateCompatibleDC, CreateCompatibleBitmap, SelectObject,
    DeleteDC, DeleteObject, BitBlt, SRCCOPY,
    FillRect, StretchDIBits
)

# ----- Main Class ----- #
class MaskOverlay(_NativeOverlay) :
    """Small overlay that displays the binary detection mask."""

    def __init__(self, master=None, opacity: float = 0.8,
                 size: tuple = (200, 200)) -> None:
        self.size = size
        self._mask_image: Optional[np.ndarray] = None
        super().__init__(opacity, class_name="PewPyMaskOverlay")

        if self._hwnd :
            screen_h = user32.GetSystemMetrics(1)
            x = 10
            y = screen_h - self.size[1] - 60
            SetWindowPos(self._hwnd, None, x, y,
                         self.size[0], self.size[1], 0)

    def update_mask(self, mask: np.ndarray) -> None:
        if mask is None:
            return
        resized = cv2.resize(mask, self.size, interpolation=cv2.INTER_NEAREST)
        with self._data_lock:
            self._mask_image = resized
        self._post_repaint()

    def _on_paint(self) -> None:
        if not self._hwnd:
            return

        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._hwnd, byref(ps))
        if not hdc:
            return

        rect = ps.rcPaint
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        mem_dc = CreateCompatibleDC(hdc)
        bmp = CreateCompatibleBitmap(hdc, w, h)
        old_bmp = SelectObject(mem_dc, bmp)

        brush = gdi32.CreateSolidBrush(0x00000000)
        FillRect(mem_dc, byref(rect), brush)
        gdi32.DeleteObject(brush)

        with self._data_lock:
            mask = self._mask_image.copy() if self._mask_image is not None else None

        if mask is not None:
            try:
                color_mask = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
                color_mask[mask > 0] = [255, 255, 255]

                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [("biSize", wintypes.DWORD),
                                ("biWidth", ctypes.c_long),
                                ("biHeight", ctypes.c_long),
                                ("biPlanes", wintypes.WORD),
                                ("biBitCount", wintypes.WORD),
                                ("biCompression", wintypes.DWORD),
                                ("biSizeImage", wintypes.DWORD),
                                ("biXPelsPerMeter", ctypes.c_long),
                                ("biYPelsPerMeter", ctypes.c_long),
                                ("biClrUsed", wintypes.DWORD),
                                ("biClrImportant", wintypes.DWORD)]
                bmi = BITMAPINFOHEADER()
                bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.biWidth = self.size[0]
                bmi.biHeight = -self.size[1]
                bmi.biPlanes = 1
                bmi.biBitCount = 24
                bmi.biCompression = 0

                gdi32.StretchDIBits(
                    mem_dc, 0, 0, self.size[0], self.size[1],
                    0, 0, self.size[0], self.size[1],
                    color_mask.ctypes.data_as(ctypes.POINTER(ctypes.c_byte)),
                    ctypes.byref(bmi), 0, SRCCOPY
                )
            except Exception as e:
                logging.error(f"Mask paint error: {e}")

        BitBlt(hdc, 0, 0, w, h, mem_dc, 0, 0, SRCCOPY)

        SelectObject(mem_dc, old_bmp)
        DeleteObject(bmp)
        DeleteDC(mem_dc)
        EndPaint(self._hwnd, byref(ps))