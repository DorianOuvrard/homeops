import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Sliding-window rate limiter keyed by Telegram user ID.

    Tracks message timestamps per user within a 60-second window. When a user
    exceeds the allowed count, `is_allowed` returns False without mutating state,
    so the counter is not consumed by a rejected message.
    """

    def __init__(self, max_per_minute: int) -> None:
        self._max = max_per_minute
        self._windows: dict[int, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, user_id: int) -> bool:
        now = time.monotonic()
        cutoff = now - 60.0

        with self._lock:
            window = self._windows[user_id]

            # Drop timestamps outside the 60-second window.
            while window and window[0] < cutoff:
                window.popleft()

            if len(window) >= self._max:
                return False

            window.append(now)
            return True
