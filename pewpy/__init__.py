#   pewpy/__init__.py
#   Core application management and threading components

__version__ = "1.0.0"
__author__ = "@notnatedavis"

# ----- Imports ----- #
from .core.app_manager import PewPyApplication
from .core.thread_manager import ThreadManager
from .core.frame_pipeline import FramePipeline
from .core.config import Config
from .core.executors import ExecutorBackend, ThreadExecutor, ProcessExecutor
from .core.resource_manager import ResourceManager

__all__ = [
    "PewPyApplication",
    "ThreadManager",
    "FramePipeline",
    "Config",
    "ExecutorBackend",
    "ThreadExecutor",
    "ProcessExecutor",
    "ResourceManager"
]