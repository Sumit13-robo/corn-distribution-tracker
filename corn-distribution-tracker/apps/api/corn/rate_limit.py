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


def hit(scope: str, key: str) -> tuple[bool, int]:
    policy = POLICIES.get(scope)
    if policy is None:
        return True, 0
    limit, window = policy
    bucket = f"{scope}:{key}"
    now = time.monotonic()
    with _lock:
        events = _events[bucket]
        while events and now - events[0] > window:
            events.popleft()
        if len(events) >= limit:
            retry_after = int(window - (now - events[0])) + 1
            return False, max(retry_after, 1)
        events.append(now)
        return True, 0


def reset_for_tests() -> None:
    with _lock:
        _events.clear()
