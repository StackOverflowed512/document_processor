"""
Error handling utilities with retry logic, fallbacks, and custom exceptions
"""

import asyncio
import functools
from typing import Callable, TypeVar, Optional, Dict, Any, Tuple
from loguru import logger
from fastapi import HTTPException, status
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

# Type variable for generic function return types
T = TypeVar('T')


class ProcessingError(Exception):
    """Base exception for document processing errors"""
    def __init__(self, message: str, stage: str = "unknown", details: Optional[Dict] = None):
        self.message = message
        self.stage = stage
        self.details = details or {}
        super().__init__(self.message)


class ExtractionError(ProcessingError):
    """Error during Phase 1 extraction"""
    pass


class CleansingError(ProcessingError):
    """Error during Phase 2 agentic cleansing"""
    pass


class StructuringError(ProcessingError):
    """Error during Phase 3 structuring"""
    pass


class ValidationError(ProcessingError):
    """Error during schema validation"""
    pass


class LLMProviderError(ProcessingError):
    """Error calling LLM provider"""
    pass


class OCRProcessingError(ProcessingError):
    """Error during OCR processing"""
    pass


def handle_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for handling errors in API endpoints
    Converts exceptions to appropriate HTTP responses
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ProcessingError as e:
            logger.error(f"Processing error at stage {e.stage}: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": e.message,
                    "stage": e.stage,
                    "details": e.details
                }
            )
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )
    return wrapper


def retry_on_failure(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_exceptions: Tuple[Exception, ...] = (Exception,)
):
    """
    Decorator for retrying failed operations with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        retry_exceptions: Exception types to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, logger.level("WARNING").name)
        )
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, logger.level("WARNING").name)
        )
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


class ErrorHandler:
    """Centralized error handling with fallback strategies"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.fallback_strategies: Dict[type, Callable] = {}
    
    def register_fallback(self, exception_type: type, fallback_func: Callable):
        """Register a fallback strategy for specific exception type"""
        self.fallback_strategies[exception_type] = fallback_func
    
    async def handle_with_fallback(
        self, 
        func: Callable[..., T], 
        *args, 
        fallback_value: Optional[T] = None,
        **kwargs
    ) -> T:
        """
        Execute function with fallback on failure
        
        Args:
            func: Function to execute
            fallback_value: Value to return if all retries fail
            *args, **kwargs: Arguments to pass to func
        
        Returns:
            Function result or fallback value
        """
        try:
            return await self._execute_with_retry(func, *args, **kwargs)
        except Exception as e:
            # Try registered fallback for this exception type
            for exc_type, fallback_func in self.fallback_strategies.items():
                if isinstance(e, exc_type):
                    logger.warning(f"Using fallback for {exc_type.__name__}: {str(e)}")
                    return await fallback_func(*args, **kwargs)
            
            # Use provided fallback value
            if fallback_value is not None:
                logger.warning(f"Using fallback value after error: {str(e)}")
                return fallback_value
            
            # Re-raise if no fallback
            raise
    
    async def _execute_with_retry(
        self, 
        func: Callable[..., T], 
        *args, 
        max_retries: int = 3,
        **kwargs
    ) -> T:
        """Execute function with retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {str(e)}. "
                    f"Retrying in {wait_time}s..."
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
        
        raise last_error


def safe_execute(func: Callable[..., T], default_value: Optional[T] = None, log_error: bool = True) -> T:
    """
    Execute a function safely, returning default value on error
    
    Args:
        func: Function to execute
        default_value: Value to return if function fails
        log_error: Whether to log the error
    
    Returns:
        Function result or default value
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"Error executing {func.__name__}: {str(e)}")
        return default_value


async def safe_execute_async(func: Callable[..., T], default_value: Optional[T] = None, log_error: bool = True) -> T:
    """
    Execute an async function safely, returning default value on error
    
    Args:
        func: Async function to execute
        default_value: Value to return if function fails
        log_error: Whether to log the error
    
    Returns:
        Function result or default value
    """
    try:
        return await func()
    except Exception as e:
        if log_error:
            logger.error(f"Error executing {func.__name__}: {str(e)}")
        return default_value


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent repeated calls to failing services
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to func
        
        Returns:
            Function result
        
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_recovery():
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker is HALF_OPEN - attempting recovery")
            else:
                raise Exception(f"Circuit breaker is OPEN. Service unavailable until {self.last_failure_time + self.recovery_timeout}")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Success - reset on half-open or reduce count
            if self.state == "HALF_OPEN":
                self._reset()
                logger.info("Circuit breaker reset to CLOSED - recovery successful")
            elif self.state == "CLOSED" and self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)
            
            return result
            
        except Exception as e:
            self._record_failure()
            raise e
    
    def _record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")
    
    def _reset(self):
        """Reset the circuit breaker"""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        
        current_time = asyncio.get_event_loop().time()
        return current_time - self.last_failure_time >= self.recovery_timeout


# Global error handler instance
global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    return global_error_handler