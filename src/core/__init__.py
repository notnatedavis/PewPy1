#   src/core/__init__.py
#   core application management and threading components
__version__ = "1.0.0"
__author__ = "@notnatedavis"

from .app_manager import PewPyApplication
from .thread_manager import ThreadManager

__all__ = [
    "PewPyApplication",
    "ThreadManager"
]