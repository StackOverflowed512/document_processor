"""
Logging configuration for the entire application
Provides structured logging with different output formats and log rotation
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Dict, Any, Optional


class JSONFormatter:
    """Custom JSON formatter for structured logging"""
    
    def __call__(self, record: Dict[str, Any]) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record["level"].name,
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }
        
        # Add exception info if present
        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback
            }
        
        # Add extra context if present
        if record.get("extra"):
            log_entry["context"] = record["extra"]
        
        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", log_to_file: bool = True, json_format: bool = False):
    """
    Configure logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to write logs to file
        json_format: Whether to use JSON format for logs
    """
    
    # Remove default handler
    logger.remove()
    
    # Set log level
    log_level_upper = log_level.upper()
    
    # Console handler with colored output
    if json_format:
        logger.add(
            sys.stdout,
            format=JSONFormatter(),
            level=log_level_upper,
            colorize=False
        )
    else:
        # Colorful console output for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level_upper,
            colorize=True
        )
    
    # File handler with rotation
    if log_to_file:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Main log file with rotation (10MB, keep 5 files)
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=log_level_upper,
            rotation="10 MB",
            retention="30 days",
            compression="gz"
        )
        
        # Error log file for errors only
        logger.add(
            log_dir / "errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="ERROR",
            rotation="10 MB",
            retention="90 days",
            compression="gz"
        )
        
        # Performance log file for tracking processing times
        perf_log_path = log_dir / "performance.log"
        if not perf_log_path.exists():
            perf_log_path.touch()
        
        logger.add(
            perf_log_path,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            level="INFO",
            filter=lambda record: record["extra"].get("log_type") == "performance",
            rotation="50 MB"
        )
    
    logger.info(f"Logging initialized with level: {log_level_upper}")
    logger.info(f"Log to file: {log_to_file}, JSON format: {json_format}")


def get_logger(name: str):
    """
    Get a logger instance with module name context
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Logger instance bound with module name
    """
    return logger.bind(name=name)


class PerformanceLogger:
    """Context manager for logging performance metrics"""
    
    def __init__(self, operation_name: str, logger_instance=None):
        """
        Initialize performance logger
        
        Args:
            operation_name: Name of the operation being measured
            logger_instance: Logger instance to use (defaults to global logger)
        """
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start timing when entering context"""
        self.start_time = datetime.now()
        self.logger.bind(log_type="performance").info(
            f"STARTED: {self.operation_name}"
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log duration when exiting context"""
        self.end_time = datetime.now()
        duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        
        status = "FAILED" if exc_type else "COMPLETED"
        
        self.logger.bind(log_type="performance").info(
            f"{status}: {self.operation_name} | Duration: {duration_ms:.2f}ms"
        )
        
        # Log error details if present
        if exc_type:
            self.logger.error(
                f"Error in {self.operation_name}: {exc_type.__name__}: {exc_val}",
                exc_info=True
            )
    
    def log_metric(self, metric_name: str, value: Any):
        """Log additional metric"""
        self.logger.bind(log_type="performance").info(
            f"METRIC: {self.operation_name} | {metric_name}: {value}"
        )


def log_request_response(request_id: str, endpoint: str, status_code: int, duration_ms: float):
    """Log API request/response details"""
    logger.bind(
        log_type="api",
        request_id=request_id
    ).info(
        f"API Request | Endpoint: {endpoint} | Status: {status_code} | Duration: {duration_ms:.2f}ms"
    )


def log_processing_stage(request_id: str, stage: str, duration_ms: float, metadata: Optional[Dict] = None):
    """Log processing pipeline stage metrics"""
    log_data = {
        "request_id": request_id,
        "stage": stage,
        "duration_ms": duration_ms
    }
    if metadata:
        log_data.update(metadata)
    
    logger.bind(log_type="processing").info(
        f"Processing Stage: {stage} | Duration: {duration_ms:.2f}ms"
    )


def log_error(request_id: str, error: Exception, context: Optional[Dict] = None):
    """Log error with context"""
    error_data = {
        "request_id": request_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    if context:
        error_data["context"] = context
    
    logger.bind(log_type="error").error(
        f"Error in request {request_id}: {type(error).__name__}: {str(error)}",
        exc_info=True
    )