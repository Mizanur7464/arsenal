"""Retry helper using config.yaml retry block."""

import time
from typing import Callable, TypeVar

from .logger_setup import warn, info

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int,
    delay_seconds: float,
    label: str = "step",
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                info(f"Retry {attempt}/{max_attempts} for {label}...")
            return fn()
        except Exception as e:
            last_error = e
            warn(f"{label} attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error
