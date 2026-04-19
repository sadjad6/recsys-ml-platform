"""
RecSys ML Platform — Shared Retry Utility.
"""

import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def retry_with_backoff(retries: int = 3, backoff_in_seconds: int = 1, backoff_factor: int = 2):
    """
    Retry an async function with exponential backoff.
    
    Args:
        retries: Maximum number of retries
        backoff_in_seconds: Initial backoff duration
        backoff_factor: Multiplier for backoff on subsequent retries
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_backoff = backoff_in_seconds
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i == retries - 1:
                        logger.error(f"Function {func.__name__} failed after {retries} retries. Final error: {str(e)}")
                        raise e
                    
                    logger.warning(f"Function {func.__name__} failed: {str(e)}. Retrying in {current_backoff}s... ({i+1}/{retries})")
                    await asyncio.sleep(current_backoff)
                    current_backoff *= backoff_factor
        return wrapper
    return decorator
