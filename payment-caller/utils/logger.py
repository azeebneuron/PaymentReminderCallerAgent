"""
Logging configuration using loguru.
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings


def setup_logger():
    """Configure logger with file and console output."""
    
    # Remove default logger
    logger.remove()
    
    # Create logs directory if it doesn't exist
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # File logging (with rotation)
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level
    )
    
    logger.info("Logger initialized successfully")


# Initialize logger on import
setup_logger()