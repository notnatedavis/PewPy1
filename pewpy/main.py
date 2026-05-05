#   pewpy/main.py
#   PewPy Main Entry Point

# ----- Imports ----- #
import sys
import signal
import logging
# import traceback #not necessary ?
from pathlib import Path

# ----- Main Classes ----- #
def setup_logging() -> None :
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def signal_handler(signum, frame) :
    logging.info("Received shutdown signal")
    sys.exit(0)

def check_dependencies() -> bool :
    required = ['customtkinter', 'pynput', 'numpy', 'yaml']
    missing = []
    for dep in required :
        try :
            __import__(dep)
        except ImportError :
            missing.append(dep)
    if missing :
        logging.error(f"Missing dependencies: {', '.join(missing)}")
        logging.error("Install with: pip install -r requirements.txt")
        return False
    return True

def main() -> int :
    try :
        setup_logging()
        logging.info("PewPy Starting")
        logging.info(f"Python: {sys.version}")
        
        if not check_dependencies() :
            return 1
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Import after path setup (package installed or run from root)
        from pewpy.core.app_manager import PewPyApplication
        from pewpy.core.config import Config
        from pewpy.ui.main_window import MainWindow
        
        # Load configuration
        config = Config()
        
        app = PewPyApplication(config)
        window = MainWindow(app)
        window.run()
        
        return 0
    except KeyboardInterrupt :
        logging.info("Interrupted by user")
        return 0
    except Exception as e :
        logging.critical(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__" :
    sys.exit(main())