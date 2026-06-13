# pewpy/utils/color.py
# HSV conversion helpers between user-friendly (0-360°,0-100%,0-100%)
# and OpenCV (0-179,0-255,0-255) scales.

import colorsys
from typing import Tuple

def user_hsv_to_opencv(h: int, s: int, v: int) -> Tuple[int, int, int]:
    # convert user HSV (0-360°,0-100%,0-100%) to OpenCV HSV (0-179,0-255,0-255)."""
    h_cv = max(0, min(179, h // 2))
    s_cv = max(0, min(255, int(s * 255 / 100)))
    v_cv = max(0, min(255, int(v * 255 / 100)))
    return h_cv, s_cv, v_cv

def opencv_hsv_to_user(h: int, s: int, v: int) -> Tuple[int, int, int]:
    # convert OpenCV HSV (0-179,0-255,0-255) to user HSV (0-360°,0-100%,0-100%)."""
    h_deg = int(h) * 2
    s_pct = int(s) * 100 // 255
    v_pct = int(v) * 100 // 255
    return h_deg, s_pct, v_pct

def user_hsv_to_rgb_hex(h: int, s: int, v: int) -> str:
    # return hex colour string (e.g., '#ff0000') from user HSV values."""
    h_norm = (h % 360) / 360.0
    s_norm = min(max(s, 0), 100) / 100.0
    v_norm = min(max(v, 0), 100) / 100.0
    r, g, b = colorsys.hsv_to_rgb(h_norm, s_norm, v_norm)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"