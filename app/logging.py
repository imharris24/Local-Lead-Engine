import logging
import sys
from pathlib import Path
from typing import Optional

from .config import settings

BASE_DIR = Path(__file__).parent.parent
DEFAULT_LOG_DIR = BASE_DIR / "data" / "logs"
DEFAULT_LOG_PATH = DEFAULT_LOG_DIR / "engine.log"

def setup_logging(
    level: str = "INFO",
    log_file: str = str(DEFAULT_LOG_PATH),
    format_string: Optional[str] = None,
) -> logging.Logger:
    if format_string is None:
        format_string = "%(asctime)s %(levelname)s %(name)s - %(message)s"

    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("local_lead_engine")
    logger.setLevel(numeric_level)

    logger.handlers = []

    formatter = logging.Formatter(format_string)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

logger = setup_logging(level=settings.log_level)