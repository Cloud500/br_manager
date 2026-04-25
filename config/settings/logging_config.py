"""
Loguru logging configuration for the BR Manager application.

Provides a centralized logging setup using loguru instead of Python's
standard logging module.
"""

import sys
from pathlib import Path

from loguru import logger

from .env_config import settings


def setup_logging(log_file: str | None = None, log_level: str | None = None) -> None:
    """
    Configure loguru logger for the application.

    Args:
        log_file: Path to log file (optional, uses settings default if not provided)
        log_level: Logging level (optional, uses settings default if not provided)
    """
    # Remove default handler
    logger.remove()

    # Use settings defaults if not provided
    level = log_level or settings.log_level
    file_path = log_file or settings.django_log_file

    # Console handler - colorized output for development
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        backtrace=True,
        diagnose=True,
    )

    # File handler - structured logging for production
    # Create parent directory if it doesn't exist
    log_path = Path(file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        file_path,
        rotation="10 MB",  # Rotate when file reaches 10 MB
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress rotated logs
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
    )

    logger.info(f"Logging configured with level: {level}")


def get_logger(name: str = __name__):
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    return logger.bind(name=name)
