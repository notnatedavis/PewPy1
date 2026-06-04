# pewpy/communication/__init__.py
# Thread‑safe data bridges for inter‑worker communication

from .overlay_bridge import OverlayData

__all__ = ["OverlayData"]