#   src/utils/system_utils.py
#   system-specific utility functions

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
    logging.warning("psutil not available - some system functions disabled")

def get_platform_info() -> Dict[str, Any] :
    # Get detailed platform information for optimization
    
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cores": psutil.cpu_count() if PSUTIL_AVAILABLE else None,
        "memory": psutil.virtual_memory().total if PSUTIL_AVAILABLE else None
    }

    # add psutil metrics if available
    if PSUTIL_AVAILABLE :
        info.update({
            "cores": psutil.cpu_count(),
            "memory": psutil.virtual_memory().total
        })
    
    return info

def optimize_process_priority() -> bool :
    # optimize process priority for performance with safe fallbacks
    if not PSUTIL_AVAILABLE :
        logging.debug("psutil unavailable - skipping priority optimization")
        return False
        
    try :
        current_process = psutil.Process()
        system = platform.system()
        
        if system == "Windows" :
            current_process.nice(psutil.HIGH_PRIORITY_CLASS)
        else :  # Linux, Darwin, etc.
            current_process.nice(-10)  # Lower nice value = higher priority
            
        logging.info("Process priority optimized successfully")

        return True
        
    except Exception as e :
        logging.warning(f"Process priority optimization failed: {e}")
        return False

def check_system_compatibility() -> Tuple[bool, str] :
    # Check if system meets requirements

    python_version = sys.version_info
    
    if python_version < (3, 13) :
        return False, f"Python 3.13+ required, found {python_version[0]}.{python_version[1]}"
    
    if platform.system() not in ["Windows", "Linux", "Darwin"]:
        return False, f"Unsupported platform: {platform.system()}"
    
    return True, "System compatible"