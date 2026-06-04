#   pewpy/utils/logging_setup.py
#   Centralised logging configuration

# ----- Imports ----- #
import sys
import logging
from pathlib import Path

# ----- Setup Function ----- #
def setup_logging() -> None :
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )