import logging
import sys
import os

def setup_logging():
    """
    Configure the root logger for the application.
    Output: Standard Error (stderr) - best for container logs.
    Format: [Timestamp] [Level] [Module] Message
    """
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplication
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Add console handler (stderr)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set libraries (like httpx/uvicorn) to WARNING to reduce noise unless DEBUG is on
    if log_level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("watchdog").setLevel(logging.WARNING)

    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
