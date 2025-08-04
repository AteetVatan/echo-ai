"""
Structured logging configuration for EchoAI voice chat system.

This module provides centralized logging setup with timestamps, structured
error handling, and performance monitoring for the AI pipeline components.
"""

import logging
import sys
import time
from typing import Any, Dict, Optional
from functools import wraps
from src.utils.config import get_settings


def setup_logging() -> None:
    """Configure structured logging with timestamps and formatting."""
    settings = get_settings()
    
    # Create formatter with timestamp
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for persistent logs
    file_handler = logging.FileHandler('echoai.log')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def log_performance(func):
    """
    Decorator to log function execution time and performance metrics.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function with performance logging
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    
    # Return appropriate wrapper based on function type
    if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
        return async_wrapper
    return sync_wrapper


class PerformanceMonitor:
    """Monitor and log performance metrics for AI pipeline components."""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = get_logger(f"performance.{component_name}")
        self.metrics: Dict[str, list] = {}
    
    def record_metric(self, metric_name: str, value: float) -> None:
        """
        Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
        
        self.logger.info(f"{self.component_name}.{metric_name}: {value:.3f}s")
    
    def get_average_metric(self, metric_name: str) -> Optional[float]:
        """
        Get average value for a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Optional[float]: Average value or None if no data
        """
        if metric_name in self.metrics and self.metrics[metric_name]:
            return sum(self.metrics[metric_name]) / len(self.metrics[metric_name])
        return None
    
    def log_summary(self) -> None:
        """Log summary of all recorded metrics."""
        summary = []
        for metric_name, values in self.metrics.items():
            if values:
                avg = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                summary.append(f"{metric_name}: avg={avg:.3f}s, min={min_val:.3f}s, max={max_val:.3f}s")
        
        if summary:
            self.logger.info(f"{self.component_name} performance summary: {' | '.join(summary)}")


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