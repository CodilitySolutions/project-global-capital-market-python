import os
import logging

# Ensure log directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'log')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),  # log to console
        logging.FileHandler(LOG_FILE_PATH)  # log to log/app.log
    ]
)

logger = logging.getLogger(__name__)
