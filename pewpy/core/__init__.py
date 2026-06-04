#   pewpy/core/__init__.py
#   Core application management and threading components

__version__ = "1.0.0"
__author__ = "@notnatedavis"

# ----- Imports ----- #
from .application import PewPyApplication
from .thread_manager import ThreadManager
from .config import Config
from .executors import ExecutorBackend, ThreadExecutor, ProcessExecutor
from .resource_manager import ResourceManager

__all__ = [
    "PewPyApplication",
    "ThreadManager",
    "Config",
    "ExecutorBackend",
    "ThreadExecutor",
    "ProcessExecutor",
    "ResourceManager"
]
# Note: FramePipeline is now in pewpy.pipeline