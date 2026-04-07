from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import ceil
from time import monotonic

from sanic import Request

from app.errors import ApiError


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(allowed=True, remaining=0, retry_after_seconds=0)

        now = monotonic()
        bucket = self._buckets.setdefault(key, deque())
        window_start = now - window_seconds

        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after_seconds = max(1, ceil(bucket[0] + window_seconds - now))
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after_seconds=retry_after_seconds,
            )

        bucket.append(now)
        remaining = max(0, limit - len(bucket))
        return RateLimitResult(allowed=True, remaining=remaining, retry_after_seconds=0)


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> None:
    if limit <= 0:
        return

    client_ip = _client_ip(request)
    result = request.app.ctx.rate_limiter.check(
        f"{scope}:{client_ip}",
        limit=limit,
        window_seconds=window_seconds,
    )
    if result.allowed:
        return

    raise ApiError(
        status=429,
        message="Rate limit exceeded",
        details={
            "scope": scope,
            "retry_after_seconds": result.retry_after_seconds,
        },
    )


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.ip or "unknown"
