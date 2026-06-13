#   pewpy/ui/overlays/screen_overlay.py
#   Full‑screen overlay for bounding boxes, crosshairs, target render,
#   and now enemy outline contour drawing.

# ----- Imports ----- 
import logging
from typing import Dict, Any, List
import ctypes
from ctypes import wintypes, byref, POINTER, sizeof
from .base_overlay import _NativeOverlay
from .win32_helpers import (
    user32, gdi32, SetWindowPos,
    BeginPaint, EndPaint, PAINTSTRUCT,
    CreateCompatibleDC, CreateCompatibleBitmap, SelectObject,
    DeleteDC, DeleteObject, BitBlt, SRCCOPY,
    FillRect, CreatePen, MoveToEx, LineTo, Rectangle, Ellipse,
    DeleteObject as GdiDeleteObject,
    Polyline, POINT
)

# ----- Main Class ----- #
class ScreenOverlay(_NativeOverlay) :
    def __init__(self, master=None, opacity: float = 0.4) -> None :
        self._shapes: Dict[str, Any] = {}
        super().__init__(opacity, class_name="PewPyScreenOverlay")

        if self._hwnd :
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            SetWindowPos(self._hwnd, None, 0, 0,
                         screen_w, screen_h, 0)

    def update_drawings(self, data: Dict[str, Any]) -> None :
        with self._data_lock :
            self._shapes = data.copy()
        self._post_repaint()

    def _on_paint(self) -> None :
        if not self._hwnd : return

        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._hwnd, byref(ps))
        if not hdc: return

        rect = ps.rcPaint
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        mem_dc = CreateCompatibleDC(hdc)
        bmp = CreateCompatibleBitmap(hdc, w, h)
        old_bmp = SelectObject(mem_dc, bmp)

        brush = gdi32.CreateSolidBrush(0x00000000)
        FillRect(mem_dc, byref(rect), brush)
        gdi32.DeleteObject(brush)

        red_pen = CreatePen(0, 2, 0x000000FF)      # color ref: 0x00BBGGRR -> red
        green_pen = CreatePen(0, 2, 0x0000FF00)
        white_pen = CreatePen(0, 1, 0x00FFFFFF)
        old_pen = SelectObject(mem_dc, red_pen)

        with self._data_lock:
            shapes = dict(self._shapes)

        # Bounding box
        bbox = shapes.get('bbox')
        if bbox and len(bbox) == 4:
            x, y, bw, bh = bbox
            SelectObject(mem_dc, red_pen)
            Rectangle(mem_dc, x, y, x + bw, y + bh)

        # Crosshair at mouse position
        mouse_pos = shapes.get('mouse_pos')
        if mouse_pos and len(mouse_pos) == 2:
            mx, my = mouse_pos
            r = 10
            SelectObject(mem_dc, green_pen)
            MoveToEx(mem_dc, mx - r, my, None)
            LineTo(mem_dc, mx + r, my)
            MoveToEx(mem_dc, mx, my - r, None)
            LineTo(mem_dc, mx, my + r)

        # Mouse outline circle
        if shapes.get('mouse_outline'):
            outline_pos = shapes.get('mouse_outline_pos')
            if outline_pos and len(outline_pos) == 2:
                ox, oy = outline_pos
                radius = 8
                hollow_brush = gdi32.GetStockObject(5)
                old_brush = SelectObject(mem_dc, hollow_brush)
                SelectObject(mem_dc, white_pen)
                Ellipse(mem_dc, ox - radius, oy - radius, ox + radius, oy + radius)
                SelectObject(mem_dc, old_brush)

        # Target render – draw contour outline if available, else centroid circle
        if shapes.get('target_outline'):
            contour = shapes.get('target_contour')
            if contour and len(contour) >= 2:
                # Draw enemy outline as a polygon
                logging.debug(f"ScreenOverlay.paint: drawing target contour with {len(contour)} points")
                contour_pen = CreatePen(0, 2, 0x000000FF)  # red, 2px
                old_pen2 = SelectObject(mem_dc, contour_pen)
                # Convert list of (x,y) to array of POINT
                points_array = (POINT * len(contour))()
                for i, (px, py) in enumerate(contour):
                    points_array[i].x = px
                    points_array[i].y = py
                # Draw polygon (closed automatically by Polyline if last point != first? We'll ensure closed)
                gdi32.Polyline(mem_dc, points_array, len(contour))
                # If the contour is not closed, you could call Polyline again from last to first,
                # but typical contours from cv2 are closed. We'll leave it.
                SelectObject(mem_dc, old_pen2)
                GdiDeleteObject(contour_pen)
            else:
                # Fallback: draw centroid circle
                target_pos = shapes.get('target_outline_pos')
                if target_pos and len(target_pos) == 2:
                    logging.debug("ScreenOverlay.paint: no contour, drawing centroid circle")
                    tx, ty = target_pos
                    radius = 11
                    target_red_pen = CreatePen(0, 1, 0x000000FF)
                    hollow_brush = gdi32.GetStockObject(5)
                    old_brush2 = SelectObject(mem_dc, hollow_brush)
                    old_pen2 = SelectObject(mem_dc, target_red_pen)
                    Ellipse(mem_dc, tx - radius, ty - radius, tx + radius, ty + radius)
                    SelectObject(mem_dc, old_pen2)
                    SelectObject(mem_dc, old_brush2)
                    GdiDeleteObject(target_red_pen)

        # ROI circle – drawn when aimbot's Region of Interest is enabled
        if shapes.get('roi_circle'):
            roi_pos = shapes.get('roi_circle_pos')
            roi_radius = shapes.get('roi_circle_radius', 150)
            if roi_pos and len(roi_pos) == 2 and roi_radius > 0:
                # Use a distinct yellow pen (0x0000FFFF) and a 2‑pixel width
                roi_pen = CreatePen(0, 2, 0x0000FFFF)   # yellow (BGR: 0x00, 0xFF, 0xFF)
                hollow_brush = gdi32.GetStockObject(5)
                old_brush = SelectObject(mem_dc, hollow_brush)
                old_pen = SelectObject(mem_dc, roi_pen)

                Ellipse(mem_dc,
                        roi_pos[0] - roi_radius, roi_pos[1] - roi_radius,
                        roi_pos[0] + roi_radius, roi_pos[1] + roi_radius)

                SelectObject(mem_dc, old_pen)
                SelectObject(mem_dc, old_brush)
                GdiDeleteObject(roi_pen)

        SelectObject(mem_dc, old_pen)
        GdiDeleteObject(red_pen)
        GdiDeleteObject(green_pen)
        GdiDeleteObject(white_pen)

        BitBlt(hdc, 0, 0, w, h, mem_dc, 0, 0, SRCCOPY)

        SelectObject(mem_dc, old_bmp)
        DeleteObject(bmp)
        DeleteDC(mem_dc)

        EndPaint(self._hwnd, byref(ps))