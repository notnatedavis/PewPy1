#   src/main.py
#   PewPy Main Application Entry Point

# ----- Imports ----- #
import sys
import signal
import logging
import traceback
from pathlib import Path

# setup imports first
sys.path.insert(0, str(Path(__file__).parent.parent))

def setup_logging() -> None :
    # setup application logging
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_date_format = '%Y-%m-%d %H:%M:%S'
    
    # console handler only for simplicity
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    # configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler],
        format=log_format,
        datefmt=log_date_format
    )

def signal_handler(signum, frame) :
    # handle shutdown signals
    logging.info("Received shutdown signal")
    sys.exit(0)

def check_dependencies() -> bool :
    # check for required dependencies
    required = ['customtkinter', 'pynput', 'pygame', 'numpy']
    missing = []
    
    for dep in required :
        try :
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing :
        logging.error(f"Missing required dependencies: {', '.join(missing)}")
        logging.error("Install with: pip install -r requirements.txt")
        return False
    
    return True

def main() -> int :
    # Main entry point
    try :
        # setup logging
        setup_logging()
        logging.info("=" * 50)
        logging.info("PewPy Application Starting")
        logging.info(f"Python Version: {sys.version}")
        logging.info("=" * 50)
        
        # check dependencies
        if not check_dependencies() : 
            return 1
        
        # setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # import after path setup
        from src.core.app_manager import PewPyApplication
        from src.ui.main_window import MainWindow
        
        # initialize application
        logging.info("Initializing PewPyApplication...")
        app = PewPyApplication()
        
        # create and run UI
        logging.info("Creating main window...")
        window = MainWindow(app)
        
        logging.info("Starting UI main loop...")
        window.run()
        
        logging.info("PewPy application exited normally")
        return 0
        
    except KeyboardInterrupt :
        logging.info("Application interrupted by user")
        return 0
        
    except Exception as e :
        logging.critical(f"Fatal error: {e}")
        logging.critical(traceback.format_exc())
        return 1

if __name__ == "__main__" :
    sys.exit(main())