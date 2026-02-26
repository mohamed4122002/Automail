import time
import logging
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

def task_metrics(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to track task execution time and success/failure rates.
    Logs duration and raises exceptions after logging.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        task_name = func.__name__
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Task '{task_name}' succeeded in {duration:.4f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Task '{task_name}' failed after {duration:.4f}s: {e}")
            raise
    return wrapper
