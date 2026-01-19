"""
Logging configuration module using Loguru.

This module provides centralized logging with:
- File rotation and retention policies
- Structured JSON logging for production
- Console output for development
- Django integration
- Exception capture with full context
"""

import sys
import os
import logging
from pathlib import Path
from loguru import logger


def configure_logging():
    """
    Configure Loguru for the HRMS application.

    Sets up:
    - Console handler with colored output (development)
    - File handlers with rotation and compression
    - JSON structured logging for production analysis
    - Error-specific log file with backtrace
    """
    # Remove default handler
    logger.remove()

    # Get settings from environment
    debug = os.environ.get("DEBUG", "True").lower() == "true"
    log_level = os.environ.get("LOG_LEVEL", "DEBUG" if debug else "INFO")

    # Log directory - use _logs in project root for Docker compatibility
    base_dir = Path(__file__).resolve().parent.parent
    log_dir = Path(os.environ.get("LOG_DIR", base_dir / "_logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    # Common format for file logs
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | {extra[request_id]} | {message}"
    )

    # Console handler - colored output for development
    if debug:
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level="DEBUG",
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Production console - simpler format
        logger.add(
            sys.stderr,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="WARNING",
            colorize=False,
        )

    # Main application log - rotates at 50MB, keeps 10 days
    logger.add(
        log_dir / "hrms.log",
        format=file_format,
        level=log_level,
        rotation="50 MB",
        retention="10 days",
        compression="zip",
        enqueue=True,  # Thread-safe async writing
        backtrace=True,
        diagnose=not debug,  # Only in production to avoid sensitive data exposure in dev
    )

    # Error-specific log with full backtrace
    logger.add(
        log_dir / "errors.log",
        format=file_format,
        level="ERROR",
        rotation="20 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # Structured JSON log for production analysis and log aggregation
    logger.add(
        log_dir / "hrms_structured.json",
        serialize=True,  # JSON format
        level="INFO",
        rotation="100 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )

    # Access/audit log - separate file for request tracking
    logger.add(
        log_dir / "access.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[request_id]} | {extra[user]} | {extra[method]} {extra[path]} | {extra[status]} | {extra[duration]}ms",
        level="INFO",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        filter=lambda record: record["extra"].get("access_log", False),
    )

    # Configure default extra fields
    logger.configure(
        extra={
            "request_id": "-",
            "user": "anonymous",
            "method": "-",
            "path": "-",
            "status": "-",
            "duration": "-",
            "access_log": False,
        }
    )

    logger.info(
        "Logging configured successfully", log_level=log_level, log_dir=str(log_dir)
    )

    return logger


def get_logger(name: str = None):
    """
    Get a logger instance with optional name binding.

    Args:
        name: Optional module name to bind to the logger

    Returns:
        Logger instance with name bound
    """
    if name:
        return logger.bind(name=name)
    return logger


# Intercept standard logging module
class InterceptHandler(logging.Handler):
    """
    Handler to intercept standard logging calls and redirect to Loguru.

    This ensures all Django internal logging also goes through Loguru.
    """

    def emit(self, record):
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_django_logging():
    """
    Configure Django to use Loguru for all logging.

    This intercepts Django's standard logging and routes it through Loguru.
    """

    # Intercept all standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Suppress noisy loggers
    for logger_name in [
        "django.server",
        "django.request",
        "django.template",
        "django.db.backends",
        "urllib3",
        "requests",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# Track if logging has been configured to avoid duplicate initialization
_logging_configured = False


def initialize_logging():
    """Initialize logging only once."""
    global _logging_configured
    if not _logging_configured:
        configure_logging()
        _logging_configured = True
