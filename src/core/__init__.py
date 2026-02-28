#   src/core/__init__.py
#   Core application management and threading components

__version__ = "1.0.0"
__author__ = "@notnatedavis"

# ----- Imports ----- #
from .app_manager import PewPyApplication
from .thread_manager import ThreadManager
from .frame_pipeline import FramePipeline
from .config import Config
from .executors import ExecutorBackend, ThreadExecutor, ProcessExecutor
from .resource_manager import ResourceManager

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