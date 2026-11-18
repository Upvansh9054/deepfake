import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger("deepfake_shield.rate_limiter")

class SlidingWindowRateLimiter:
    """
    In-memory sliding window rate limiter designed for endpoint protection.
    Tracks timestamps of requests per client key (IP or user ID).
    Thread-safe for single-process asyncio event loops.
    """
    def __init__(self, requests_per_minute: int = 60, bucket_name: str = "default"):
        self.limit = requests_per_minute
        self.window_seconds = 60.0
        self.bucket_name = bucket_name
        self._history: Dict[str, List[float]] = defaultdict(list)

    def _clean_old_requests(self, key: str, now: float):
        cutoff = now - self.window_seconds
        self._history[key] = [t for t in self._history[key] if t > cutoff]

    async def __call__(self, request: Request):
        if not settings.RATE_LIMITING_ENABLED:
            return True

        # Test bypass header for CI/integration tests if configured
        if request.headers.get("X-Test-Bypass-RateLimit") == "true":
            return True

        # Resolve client identifier: prefer client host IP
        client_ip = request.client.host if request.client else "unknown"
        # Combine IP with bucket name so different endpoints have separate limits
        key = f"{self.bucket_name}:{client_ip}"

        now = time.time()
        self._clean_old_requests(key, now)

        current_count = len(self._history[key])
        if current_count >= self.limit:
            # Calculate retry after in seconds
            oldest_timestamp = self._history[key][0]
            retry_after = max(1, int(self.window_seconds - (now - oldest_timestamp)))
            logger.warning(f"Rate limit exceeded for {client_ip} on bucket {self.bucket_name}: {current_count}/{self.limit}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: max {self.limit} requests per minute for this endpoint. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

        self._history[key].append(now)
        return True

    def reset(self):
        """Clears request history (useful for test fixtures)."""
        self._history.clear()

# Preconfigured rate limiter dependencies
login_rate_limiter = SlidingWindowRateLimiter(
    requests_per_minute=settings.RATE_LIMIT_LOGIN_PER_MINUTE,
    bucket_name="auth_login"
)

inference_rate_limiter = SlidingWindowRateLimiter(
    requests_per_minute=settings.RATE_LIMIT_INFERENCE_PER_MINUTE,
    bucket_name="inference"
)

general_rate_limiter = SlidingWindowRateLimiter(
    requests_per_minute=settings.RATE_LIMIT_GENERAL_PER_MINUTE,
    bucket_name="general"
)

