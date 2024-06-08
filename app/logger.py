# logger.py
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

# File handler
file_handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=5)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
