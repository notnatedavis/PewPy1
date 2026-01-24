#   src/workers/__init__.py
#   Worker classes for toggleable functions - Simplified to avoid circular imports

# Import only BaseWorker here, import specific workers lazily
from .function_worker import BaseWorker

__all__ = [
    "BaseWorker"
    # Note: Other workers are imported lazily to avoid circular imports
]