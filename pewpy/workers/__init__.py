#   src/workers/__init__.py
#   Worker classes and factory for toggleable functions

# ----- Imports ----- #
import logging
from typing import Dict, Any, Tuple
from .base import BaseWorker
from ..communication.overlay_bridge import OverlayData

def create_workers(config) -> Tuple[Dict[str, Any], OverlayData]:
    """
    Create all worker instances from configuration.
    Returns:
        (workers dict, overlay_data bridge)
    """
    workers: Dict[str, Any] = {}
    overlay_data = OverlayData()

    # ----- AutoClicker -----
    try:
        from .auto_clicker import AutoClicker
        interval = config.get('workers.auto_clicker.default_interval', 0.1)
        button = config.get('workers.auto_clicker.button', 'left')
        workers['auto_clicker'] = AutoClicker(click_interval=interval, button=button)
        logging.debug("AutoClicker worker created")
    except Exception as e:
        logging.error(f"Failed to create AutoClicker worker: {e}")

    # ----- Aimbot -----
    try:
        from .aimbot import AimbotWorker
        aimbot_cfg = config.get('workers.aimbot', {})
        workers['aimbot'] = AimbotWorker(
            capture_region=aimbot_cfg.get('capture_region'),
            target_fps=aimbot_cfg.get('target_fps', 60),
            hsv_range=(
                tuple(aimbot_cfg.get('hsv_lower', [0,120,70])),
                tuple(aimbot_cfg.get('hsv_upper', [10,255,255]))
            ),
            smooth_factor=aimbot_cfg.get('smooth_factor', 0.2),
            activation_key=aimbot_cfg.get('activation_key', 'alt_l'),
            overlay_data=overlay_data
        )
        logging.info("Aimbot worker loaded")
    except ImportError:
        logging.info("Aimbot worker not available (import failed)")
    except Exception as e:
        logging.warning(f"Aimbot worker init failed: {e}")

    logging.debug("Worker factory complete")
    return workers, overlay_data

__all__ = [
    "BaseWorker",
    "create_workers"
    # Concrete workers are imported lazily by the factory or as needed
]