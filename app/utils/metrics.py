"""
Metrics collection and monitoring utilities
"""

import time
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import asyncio
from loguru import logger


@dataclass
class Metric:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collect and aggregate application metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        self.counters[name] += value
        self._record_metric(name, float(value), tags)
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a gauge metric (current value)"""
        self.gauges[name] = value
        self._record_metric(name, value, tags)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram metric (distribution)"""
        self.histograms[name].append(value)
        self._record_metric(name, value, tags)
    
    def record_timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric"""
        self.record_histogram(f"{name}_duration_ms", duration_ms, tags)
    
    def _record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Internal method to record metric"""
        metric = Metric(name=name, value=value, tags=tags or {})
        self.metrics[name].append(metric)
        
        # Keep only last 1000 data points per metric
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def get_counter(self, name: str) -> int:
        """Get current counter value"""
        return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> Optional[float]:
        """Get current gauge value"""
        return self.gauges.get(name)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for histogram metric"""
        values = self.histograms.get(name, [])
        if not values:
            return {}
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            "count": count,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p90": sorted_values[int(count * 0.9)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)]
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                name: self.get_histogram_stats(name) 
                for name in self.histograms
            },
            "timestamps": {
                name: [m.timestamp.isoformat() for m in metrics[-10:]]  # Last 10
                for name, metrics in self.metrics.items()
            }
        }
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, metric_name: str, collector: MetricsCollector, tags: Optional[Dict[str, str]] = None):
        self.metric_name = metric_name
        self.collector = collector
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.collector.record_timing(self.metric_name, duration_ms, self.tags)
        
        if exc_type:
            self.collector.increment_counter(f"{self.metric_name}_errors", tags=self.tags)


@contextmanager
def measure_time(metric_name: str, collector: MetricsCollector, **tags):
    """Context manager for measuring operation time"""
    timer = Timer(metric_name, collector, tags)
    with timer:
        yield


class ProcessingMetrics:
    """Specialized metrics for document processing pipeline"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.request_id = None
    
    def set_request_id(self, request_id: str):
        """Set current request ID for metrics"""
        self.request_id = request_id
    
    def record_extraction(self, method: str, duration_ms: float, text_length: int):
        """Record extraction phase metrics"""
        tags = {"method": method}
        self.collector.record_timing("extraction_duration_ms", duration_ms, tags)
        self.collector.record_histogram("extraction_text_length", text_length, tags)
        
        if self.request_id:
            logger.bind(metrics=True).info(
                f"Extraction metrics - Request: {self.request_id}, Method: {method}, "
                f"Duration: {duration_ms:.2f}ms, Text length: {text_length}"
            )
    
    def record_cleansing(self, confidence: float, duration_ms: float, fields_extracted: int):
        """Record cleansing phase metrics"""
        tags = {"confidence_level": str(int(confidence * 100))}
        self.collector.record_timing("cleansing_duration_ms", duration_ms, tags)
        self.collector.record_gauge("cleansing_confidence", confidence)
        self.collector.record_histogram("cleansing_fields_extracted", fields_extracted)
        
        if self.request_id:
            logger.bind(metrics=True).info(
                f"Cleansing metrics - Request: {self.request_id}, Confidence: {confidence:.2f}, "
                f"Duration: {duration_ms:.2f}ms, Fields: {fields_extracted}"
            )
    
    def record_structuring(self, validation_passed: bool, duration_ms: float):
        """Record structuring phase metrics"""
        status = "passed" if validation_passed else "failed"
        tags = {"validation_status": status}
        self.collector.record_timing("structuring_duration_ms", duration_ms, tags)
        
        if validation_passed:
            self.collector.increment_counter("structuring_success")
        else:
            self.collector.increment_counter("structuring_failures")
        
        if self.request_id:
            logger.bind(metrics=True).info(
                f"Structuring metrics - Request: {self.request_id}, Validation: {status}, "
                f"Duration: {duration_ms:.2f}ms"
            )
    
    def record_llm_call(self, provider: str, model: str, duration_ms: float, success: bool):
        """Record LLM API call metrics"""
        tags = {"provider": provider, "model": model, "success": str(success)}
        self.collector.record_timing("llm_call_duration_ms", duration_ms, tags)
        
        if success:
            self.collector.increment_counter("llm_call_success", tags=tags)
        else:
            self.collector.increment_counter("llm_call_failures", tags=tags)
    
    def record_ocr_call(self, engine: str, duration_ms: float, text_length: int):
        """Record OCR call metrics"""
        tags = {"engine": engine}
        self.collector.record_timing("ocr_duration_ms", duration_ms, tags)
        self.collector.record_histogram("ocr_text_length", text_length, tags)


# Global metrics instances
metrics_collector = MetricsCollector()
processing_metrics = ProcessingMetrics(metrics_collector)