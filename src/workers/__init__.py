#   src/workers/__init__.py
#   Worker classes for toggleable functions - Simplified to avoid circular imports

# ----- Imports ----- #
# Import only BaseWorker here, import specific workers lazily
from .function_worker import BaseWorker

__all__ = [
    "BaseWorker"
    # note : Other workers are imported lazily to avoid circular imports
]