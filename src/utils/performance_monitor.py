from typing import Dict, Optional
from src.utils import get_logger


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