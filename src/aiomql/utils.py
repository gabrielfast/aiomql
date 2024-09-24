"""Utility functions for aiomql."""
import decimal
import random
from functools import wraps, partial
import asyncio
from logging import getLogger

logger = getLogger(__name__)


def dict_to_string(data: dict, multi=False) -> str:
    """Convert a dict to a string. Useful for logging.

    Args:
        data (dict): The dict to convert.
        multi (bool, optional): If True, each key-value pair will be on a new line. Defaults to False.

    Returns:
        str: The string representation of the dict.
    """
    sep = '\n' if multi else ', '
    return f"{sep}".join(f"{key}: {value}" for key, value in data.items())


def backoff_decorator(func=None, *, max_retries: int = 5, retries: int = 0, error='') -> callable:
    if func is None:
        return partial(backoff_decorator, max_retries=max_retries, retries=retries, error=error)

    @wraps(func)
    async def wrapper(*args, **kwargs):
        nonlocal retries
        if max_retries == retries:
            retries = 0
            await func(*args, **kwargs)
        try:
            retries += 1
            res = await func(*args, **kwargs)
            if error != '' and res == error:
                raise TypeError('Invalid return type')
            return res
        except Exception as err:
             logger.error(f'Error in {func.__name__}: {err}')
             await asyncio.sleep(retries + random.randint(1, max_retries))
             await wrapper(*args, **kwargs)

    return wrapper


def error_handler(func=None, *, msg='', exe = Exception):
    if func is None:
        return partial(error_handler, msg=msg, exe=exe)

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            res = await func(*args, **kwargs)
            return res
        except exe as err:
            logger.error(f'Error in {func.__name__}: {msg or err}')

    return wrapper

def error_handler_sync(func=None, *, msg='', exe=Exception):
    if func is None:
        return partial(error_handler, msg=msg, exe=exe)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            return res
        except exe as err:
            logger.error(f'Error in {func.__name__}: {msg or err}')

    return wrapper

def round_down(value: int, base: int) -> int:
    return value if value % base == 0 else value  - (value % base)


def round_up(value: int, base: int) -> int:
    return value if value % base == 0 else value + base - (value % base)


def round_off(value: float, step: float, round_down: bool = False) -> float:
    """Round off a number to the nearest step."""
    with decimal.localcontext() as ctx:
        ctx.rounding = decimal.ROUND_DOWN if round_down else decimal.ROUND_UP
        return float(decimal.Decimal(str(value)).quantize(decimal.Decimal(str(step))))


def async_cache(fun):
    @wraps(fun)
    async def wrapper(*args, **kwargs):
        key = (args, frozenset(kwargs.items()))
        async with wrapper.lock:
            if key not in wrapper.cache:
                wrapper.cache[key] = await fun(*args, **kwargs)
        return wrapper.cache[key]

    wrapper.lock = asyncio.Lock()
    wrapper.cache = {}
    return wrapper
