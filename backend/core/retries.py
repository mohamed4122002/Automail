import asyncio
import functools
import logging
import random
from typing import Type, Union, Tuple, Callable, Any

logger = logging.getLogger(__name__)

def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
):
    """
    Standardized retry decorator with exponential backoff and jitter.
    
    Args:
        max_attempts: Maximum number of attempts before giving up.
        initial_delay: Delay before the first retry in seconds.
        exponential_base: Base for exponential backoff (e.g., 2.0 for 2, 4, 8...).
        jitter: Whether to add random jitter to the delay.
        exceptions: Exception type(s) to catch and retry on.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    delay = initial_delay * (exponential_base ** (attempts - 1))
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"Retry {attempts}/{max_attempts-1} for {func.__name__} in {delay:.2f}s due to: {e}"
                    )
                    await asyncio.sleep(delay)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
