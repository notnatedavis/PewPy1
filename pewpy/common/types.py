# pewpy/common/types.py
# TypedDicts and shared type aliases for improved type safety

# ----- Imports ----- #
from typing import TypedDict, Optional, Tuple, Dict, Any
import numpy as np

# ----- TypedDicts ----- #
class DetectionResult(TypedDict, total=False):
    center: Tuple[int, int]
    bounding_box: Tuple[int, int, int, int]
    confidence: float
    screen_position: Tuple[float, float]

class OverlayUpdateData(TypedDict, total=False):
    target: Optional[Tuple[float, float]]
    target_center: Optional[Tuple[int, int]]
    bbox: Optional[Tuple[int, int, int, int]]
    frame_dims: Optional[Tuple[int, int]]
    mouse_pos: Optional[Tuple[int, int]]
    mask: Optional[np.ndarray]
    # additional drawing flags
    mouse_outline: bool
    mouse_outline_pos: Optional[Tuple[int, int]]
    target_outline: bool
    target_outline_pos: Optional[Tuple[int, int]]
    target_outline_radius: int
    target_outline_color: str

class ResourceUpdateChanges(TypedDict, total=False):
    target_fps: int