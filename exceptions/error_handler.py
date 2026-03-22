import time
import asyncio
from typing import Callable, Awaitable
from functools import wraps

from loguru import logger


def sync_error_handler(*, name: str, max_retries: int = 5):
    """
    Sync Error Handler decorator wraps any operation, and retry the operation
    at max_retries times with exponential backoff time in case of any exception occurs.

    Args:
        name (str) : Name of the operation
        max_retries (str) : Max number of retries

    Raises:
        Exception : In case of any exception
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, max_retries + 1):
                try:
                    logger.info(f"Running operation {name} attempt:{i}")
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if i < max_retries:
                        time_to_wait = pow(2, i)
                        logger.error(
                            f"Operation {name} failed, retrying... after:{time_to_wait}s"
                        )
                        time.sleep(time_to_wait)

            logger.error(
                f"Operation {name} failed, max retry limit exceed -> Max Retry Limit:{max_retries}"
            )
            raise last_exception

        return wrapper

    return decorator


def async_error_handler(*, name: str, max_retries: int = 5):
    """
    Async Error Handler decorator wraps any operation, and retry the operation
    at max_retries times with exponential backoff time in case of any exception occurs.

    Args:
        name (str) : Name of the operation
        max_retries (str) : Max number of retries

    Raises:
        Exception : In case of any exception
    """

    def decorator(func: Callable[..., Awaitable]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(1, max_retries + 1):
                try:
                    logger.info(f"Running operation {name} attempt:{i}")
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if i < max_retries:
                        time_to_wait = pow(2, i)
                        logger.error(
                            f"Operation {name} failed, retrying... after:{time_to_wait}s"
                        )
                        await asyncio.sleep(time_to_wait)

            logger.error(
                f"Operation {name} failed, max retry limit exceed -> Max Retry Limit:{max_retries}"
            )
            raise last_exception

        return wrapper

    return decorator
