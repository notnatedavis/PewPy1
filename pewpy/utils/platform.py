#   pewpy/utils/platform.py
#   System compatibility checks and process priority optimisation

# ----- Imports ----- #
import platform
import sys
import logging
from typing import Tuple, Dict, Any
try :
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError :
    PSUTIL_AVAILABLE = False

# ----- Main Functions ----- #
def get_platform_info() -> Dict[str, Any] :
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    if PSUTIL_AVAILABLE :
        info.update({
            "cores": psutil.cpu_count(),
            "memory": psutil.virtual_memory().total
        })
    return info

def optimize_process_priority() -> bool : 
    if not PSUTIL_AVAILABLE :
        logging.debug("psutil unavailable - skipping priority optimization")
        return False
    try :
        current_process = psutil.Process()
        system = platform.system()
        if system == "Windows" :
            current_process.nice(psutil.HIGH_PRIORITY_CLASS)
        else :
            current_process.nice(-10)
        logging.info("Process priority optimized")
        return True
    except Exception as e :
        logging.warning(f"Process priority optimization failed: {e}")
        return False

def check_system_compatibility() -> Tuple[bool, str] :
    if sys.version_info < (3, 13) :
        return False, f"Python 3.13+ required, found {sys.version_info.major}.{sys.version_info.minor}"
    if platform.system() not in ["Windows", "Linux", "Darwin"] :
        return False, f"Unsupported platform: {platform.system()}"
    return True, "System compatible"

def get_cpu_count() -> int :
    # Return number of CPU cores (physical if possible)
    if PSUTIL_AVAILABLE :
        return psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True) or 1
    return 1