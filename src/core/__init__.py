#   src/core/__init__.py
__version__ = "1.0.0"
__author__ = "@notnatedavis"

from .frame_pipeline import FramePipeline
from .performance_monitor import PerformanceMonitor, PerformanceOptimizer
from .resource_manager import ResourceManager
from .task_dispatcher import AdaptiveTaskDispatcher

__all__ = [
    "FramePipeline",
    "PerformanceMonitor", 
    "PerformanceOptimizer",
    "ResourceManager",
    "AdaptiveTaskDispatcher"
]