import threading
from collections.abc import Callable
from functools import cache, wraps


def once[T](func: Callable[[], T]) -> Callable[[], T]:
    """
    Decorator that ensures a function is only executed once.

    Thread-safe: concurrent callers block until the first execution completes,
    then all receive the cached result. Guaranteed single execution.
    """
    lock = threading.RLock()

    @cache
    @wraps(func)
    def wrapper() -> T:
        with lock:
            if wrapper.cache_info().currsize:
                return wrapper()
            return func()

    return wrapper
