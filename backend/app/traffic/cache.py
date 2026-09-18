"""Minimal in-process TTL cache (CLAUDE.md traffic master-prompt #24 - Redis is the
target production infra per CLAUDE.md's stack, but no Redis client exists anywhere in
this codebase yet; adding one just for this cache would be new infrastructure this
feature doesn't itself require - CLAUDE.md #46. A Redis-backed cache with the same
interface is a documented, straightforward follow-up once that infra exists.
"""

import time


class TTLCache:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[object, tuple[float, object]] = {}

    def get(self, key: object):
        entry = self._store.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > self._ttl_seconds:
            del self._store[key]
            return None
        return value

    def set(self, key: object, value: object) -> None:
        self._store[key] = (time.monotonic(), value)
