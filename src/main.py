#   src/main.py
#   PewPy Main Application
#   High-performance Python aimbot with modern concurrency

# ----- Imports ----- #
import sys
import signal
import logging
from pathlib import Path

# ----- Setup ----- #
# Add the project root to Python path to allow proper imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# import modules
from core.app_manager import PewPyApplication
from ui.main_window import MainWindow

def setup_logging() :
    # setup application logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pewpy.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def signal_handler(signum, frame):
    logging.info("Received shutdown signal")
    sys.exit(0)

def main() :
    # main entry point
    setup_logging()

    # setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try :
        # initialize application
        app = PewPyApplication()
        
        # create and run UI
        window = MainWindow(app)
        window.run()
        
    except Exception as e :
        logging.critical(f"Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__" : 
    sys.exit(main())