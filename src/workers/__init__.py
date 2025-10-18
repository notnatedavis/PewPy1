#   src/workers/__init__.py
#   Worker classes for toggleable functions

# ----- Imports ----- #
from .function_worker import BaseWorker
from .auto_clicker import AutoClicker

__all__ = [
    "BaseWorker",
    "AutoClicker"
]