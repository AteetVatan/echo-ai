"""
Logging configuration for EchoAI voice chat system.

This module provides structured logging setup, performance monitoring,
and error handling utilities for the application.
"""

import logging
import time
import functools
from typing import Dict, Any, Optional, Callable
from src.utils.config import get_settings
import asyncio


settings = get_settings()


def setup_logging() -> None:
    """Setup structured logging for the application."""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


def log_performance(func: Callable) -> Callable:
    """Decorator to log function performance metrics."""
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        logger = get_logger(func.__module__)
        
        try:
            result = func(*args, **kwargs)
            latency = time.time() - start_time
            logger.info(f"{func.__name__} completed in {latency:.3f}s")
            return result
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"{func.__name__} failed after {latency:.3f}s: {str(e)}")
            raise
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        logger = get_logger(func.__module__)
        
        try:
            result = await func(*args, **kwargs)
            latency = time.time() - start_time
            logger.info(f"{func.__name__} completed in {latency:.3f}s")
            return result
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"{func.__name__} failed after {latency:.3f}s: {str(e)}")
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None) -> None:
    """
    Log error with additional context information.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context information
    """
    error_msg = f"Error: {str(error)}"
    if context:
        context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
        error_msg += f" | Context: {context_str}"
    
    logger.error(error_msg, exc_info=True) 