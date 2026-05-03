"""Utility decorators for resource‑aware task execution.

The :func:`ensure_memory` decorator checks the available system memory before the
wrapped function runs. If the free memory is below the ``threshold_mb`` (default
500 MiB), the decorator will pause execution, re‑checking periodically (every 5 s)
until enough memory is available. This helps avoid out‑of‑memory crashes on the
2 CPU/2 GiB build server.

The implementation prefers :pypi:`psutil` for cross‑platform memory queries. If
psutil is not installed, a very simple fallback based on ``os.sysconf`` is used
on Unix; on Windows the fallback always returns ``True`` (assuming memory is
adequate) because precise free‑memory stats are not readily available without
additional dependencies.
"""

from __future__ import annotations

import os
import time
from functools import wraps
from typing import Callable, Any

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover – psutil may be missing in the env
    psutil = None


def _available_memory_mb() -> int:
    """Return free memory in MiB.

    Uses ``psutil.virtual_memory().available`` when possible. If psutil is not
    available and the platform provides ``os.sysconf('SC_PAGE_SIZE')`` and
    ``os.sysconf('SC_AVPHYS_PAGES')`` (Unix), those are used. Otherwise, on
    Windows, we conservatively return a large number to avoid false negatives.
    """
    if psutil:
        return int(psutil.virtual_memory().available / (1024 * 1024))
    # Fallback for Unix‑like systems without psutil
    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_AVPHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return int(pages * page_size / (1024 * 1024))
        except (ValueError, OSError):
            pass
    # Default: assume plenty of memory (e.g., Windows without psutil)
    return 1024 * 1024


def ensure_memory(threshold_mb: int = 500, check_interval: int = 5) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that blocks function execution until free memory exceeds ``threshold_mb``.

    Parameters
    ----------
    threshold_mb: int
        Minimum free memory required to proceed (MiB).
    check_interval: int
        Seconds to wait between memory checks.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            while True:
                free_mb = _available_memory_mb()
                if free_mb >= threshold_mb:
                    break
                # Not enough memory – wait and retry
                print(f"[ensure_memory] Free memory {free_mb} MiB < {threshold_mb} MiB – sleeping {check_interval}s")
                time.sleep(check_interval)
            return func(*args, **kwargs)

        return wrapper

    return decorator
