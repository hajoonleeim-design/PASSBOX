from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic
from typing import Callable


class LoginRateLimiter:
    """Small in-process limiter for login failures.

    This protects a local or single-process deployment. A multi-worker or
    multi-instance deployment should move the same counter to shared storage.
    """

    def __init__(self, clock: Callable[[], float] = monotonic):
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _recent_failures(
        self,
        key: str,
        *,
        now: float,
        window_seconds: int,
    ) -> deque[float]:
        failures = self._failures[key]
        cutoff = now - window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures

    def retry_after_seconds(
        self,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
    ) -> int | None:
        if max_attempts <= 0 or window_seconds <= 0:
            return None

        with self._lock:
            now = self._clock()
            failures = self._recent_failures(
                key,
                now=now,
                window_seconds=window_seconds,
            )
            if len(failures) < max_attempts:
                return None
            return max(1, ceil(failures[0] + window_seconds - now))

    def record_failure(
        self,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
    ) -> None:
        if max_attempts <= 0 or window_seconds <= 0:
            return

        with self._lock:
            now = self._clock()
            failures = self._recent_failures(
                key,
                now=now,
                window_seconds=window_seconds,
            )
            failures.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_rate_limiter = LoginRateLimiter()
