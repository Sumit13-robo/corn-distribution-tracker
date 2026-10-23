"""Process-local sliding-window rate limiting for sensitive endpoints.

Suitable for a single API process/node. For horizontally scaled deployments use
a shared cache/backend; this limitation is documented in the runbook. The
implementation is deliberately dependency-free and thread-safe.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_events: dict[str, deque[float]] = defaultdict(deque)

POLICIES: dict[str, tuple[int, int]] = {
    "auth.login": (10, 300),
    "auth.password_reset": (5, 900),
    "auth.invite_accept": (5, 900),
    "evidence.upload_intent": (60, 300),
    "deliveries.create": (30, 300),
}


def _prune(events: deque[float], now: float, window: int) -> None:
    while events and now - events[0] > window:
        events.popleft()


def _retry_after(events: deque[float], now: float, window: int) -> int:
    return max(int(window - (now - events[0])) + 1, 1)


def hit(scope: str, key: str) -> tuple[bool, int]:
    """Atomically check and record an attempt (for actions that always count)."""
    policy = POLICIES.get(scope)
    if policy is None:
        return True, 0
    limit, window = policy
    bucket = f"{scope}:{key}"
    now = time.monotonic()
    with _lock:
        events = _events[bucket]
        _prune(events, now, window)
        if len(events) >= limit:
            return False, _retry_after(events, now, window)
        events.append(now)
        return True, 0


def check(scope: str, key: str) -> tuple[bool, int]:
    """Check the window without recording; pair with record() on failure.

    Used for sign-in so that successful logins from a shared/NAT address do not
    consume the failure budget. The check stays before password verification so
    a blocked caller cannot force expensive password hashing.
    """
    policy = POLICIES.get(scope)
    if policy is None:
        return True, 0
    limit, window = policy
    bucket = f"{scope}:{key}"
    now = time.monotonic()
    with _lock:
        events = _events[bucket]
        _prune(events, now, window)
        if len(events) >= limit:
            return False, _retry_after(events, now, window)
        return True, 0


def record(scope: str, key: str) -> None:
    """Record one failed attempt for a scope checked with check()."""
    policy = POLICIES.get(scope)
    if policy is None:
        return
    _, window = policy
    bucket = f"{scope}:{key}"
    now = time.monotonic()
    with _lock:
        events = _events[bucket]
        _prune(events, now, window)
        events.append(now)


def reset_for_tests() -> None:
    with _lock:
        _events.clear()
