"""
Logging utilities for the crawler system.
"""
import sys
from loguru import logger
from config.settings import LOG_LEVEL, LOG_FILE


def setup_logger():
    """Configure loguru logger with file and console output."""
    logger.remove()

    # Console output with colors
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # File output
    logger.add(
        LOG_FILE,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="1 week",
    )

    return logger


log = setup_logger()
