from functools import wraps
from typing import Callable, Awaitable

from typing_extensions import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def cached(f: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Decorator to cache the result of an async function"""

    cache: R | None = None

    @wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        nonlocal cache

        if cache is not None:
            return cache

        cache = await f(*args, **kwargs)
        return cache

    return wrapper
