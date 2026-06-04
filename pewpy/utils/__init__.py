#   pewpy/utils/__init__.py
#   Helper functions and utilities for performance and efficiency

# ----- Imports ----- #
from .logging_setup import setup_logging
from .platform import (
    get_platform_info,
    optimize_process_priority,
    check_system_compatibility,
    get_cpu_count
)

__all__ = [
    "setup_logging",
    "get_platform_info", 
    "optimize_process_priority",
    "check_system_compatibility",
    "get_cpu_count"
]