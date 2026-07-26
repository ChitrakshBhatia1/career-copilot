import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "career_copilot.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


def setup_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return  # already configured; avoid duplicate handlers on repeated calls (e.g. in tests)

    root_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    LOG_DIR.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
