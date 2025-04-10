import logging

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),  # log to console
        # You can add logging.FileHandler("logfile.log") here too
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)
