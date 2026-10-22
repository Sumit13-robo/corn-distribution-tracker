"""Process-local sliding-window rate limiting for sensitive endpoints.

Suitable for a single API process/node. For horizontally scaled deployments
configure RATE_LIMIT_BACKEND_URL (e.g. Redis); see docs/ops/ENVIRONMENT_VARIABLES.md
and the deployment runbook for the documented limitation.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_events: dict[str, deque[float]] = defaultdict(deque)

# Scope policies (name -> (max_events, window_seconds)) - explicit, not hidden.
POLICIES: dict[str, tuple[int, int]] = {
    "auth.login": (10, 300),
    "auth.password_reset": (5, 900),
    "auth.invite_accept": (5, 900),
    "evidence.upload_intent": (60, 300),
    "deliveries.create": (30, 300),
}


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Rate limit exceeded")


def _evict_expired(events: deque[float], now: float, window: float) -> None:
    while events and now - events[0] > window:
        events.popleft()


def hit(scope: str, key: str) -> tuple[bool, int]:
    """Register one event for scope/key. Returns (allowed, retry_after_seconds)."""
    policy = POLICIES.get(scope)
    if policy is None:
        return True, 0
    limit, window = policy
    bucket = f"{scope}:{key}"
    now = time.monotonic()
    with _lock:
        events = _events[bucket]
        _evict_expired(events, now, window)
        if len(events) >= limit:
            retry_after = int(window - (now - events[0])) + 1
            return False, max(retry_after, 1)
        events.append(now)
        if len(events) == 1:
            # opportunistically prune other buckets to bound memory
            stale = [b for b, evs in _events.items() if not evs]
            for b in stale:
                _events.pop(b, None)
        return True, 0


def reset_for_tests() -> None:
    with _lock:
        _events.clear()
