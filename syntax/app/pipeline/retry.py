import asyncio
import random
import logging
from functools import wraps
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)

def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.1,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    A custom asynchronous retry decorator implementing exponential backoff with jitter.
    
    Args:
        max_retries: Maximum number of times to retry before raising the exception.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        backoff_factor: Multiplier for the delay upon each subsequent retry.
        jitter: Maximum random seconds to add to delay to prevent thundering herd.
        exceptions: Tuple of exceptions to catch and retry (defaults to all Exceptions).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries. Error: {e}")
                        raise e
                    
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    actual_delay = delay + random.uniform(0, jitter)
                    
                    logger.warning(f"Attempt {attempt}/{max_retries} for {func.__name__} failed: {e}. Retrying in {actual_delay:.2f}s...")
                    await asyncio.sleep(actual_delay)
        return wrapper
    return decorator
