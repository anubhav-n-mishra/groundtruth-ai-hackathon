"""
Logging configuration for the Automated Insight Engine.

This module provides a centralized logging setup with consistent
formatting and level configuration.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "insight_engine",
    level: str = "INFO",
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up and configure a logger instance.
    
    Args:
        name: Logger name (typically module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string (optional)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Set logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Default format
    if log_format is None:
        log_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = "insight_engine") -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    logger = logging.getLogger(name)
    
    # If no handlers configured, set up with defaults
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


# Pre-configured module loggers
def get_ingest_logger() -> logging.Logger:
    """Get logger for data ingestion module."""
    return get_logger("insight_engine.ingest")


def get_metrics_logger() -> logging.Logger:
    """Get logger for metrics calculation module."""
    return get_logger("insight_engine.metrics")


def get_insights_logger() -> logging.Logger:
    """Get logger for insights generation module."""
    return get_logger("insight_engine.insights")


def get_narrative_logger() -> logging.Logger:
    """Get logger for narrative generation module."""
    return get_logger("insight_engine.narrative")


def get_report_logger() -> logging.Logger:
    """Get logger for report generation module."""
    return get_logger("insight_engine.report")


def get_api_logger() -> logging.Logger:
    """Get logger for API module."""
    return get_logger("insight_engine.api")
