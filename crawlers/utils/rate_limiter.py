"""
Rate limiter utilities for the crawler system.

Provides flexible rate limiting for different services with
configurable limits, burst handling, and async support.
"""
from __future__ import annotations

import asyncio
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from config.settings import RATE_LIMITS
from utils.logger import log


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""

    calls: int  # Number of calls allowed
    period: float  # Time period in seconds
    burst: int = 0  # Additional burst allowance


@dataclass
class RateLimitState:
    """Tracks the state of rate limiting for a service."""

    timestamps: list = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


class RateLimiter:
    """
    Thread-safe rate limiter supporting multiple services.

    Usage:
        limiter = RateLimiter()

        # Synchronous usage
        with limiter.limit("github"):
            # Make API call
            pass

        # Check before calling
        if limiter.can_proceed("web_scraper"):
            limiter.record_call("web_scraper")
            # Make request

        # Wait if needed
        limiter.wait_if_needed("kaggle")
        # Make request
    """

    def __init__(self, configs: Optional[dict[str, RateLimitConfig]] = None):
        """
        Initialize rate limiter.

        Args:
            configs: Dict mapping service names to RateLimitConfig.
                    Defaults to settings.RATE_LIMITS if not provided.
        """
        self._configs: dict[str, RateLimitConfig] = {}
        self._states: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._global_lock = threading.Lock()

        # Load default configs from settings
        for service, config in RATE_LIMITS.items():
            self._configs[service] = RateLimitConfig(
                calls=config["calls"],
                period=config["period"],
            )

        # Override with custom configs
        if configs:
            self._configs.update(configs)

    def _get_config(self, service: str) -> RateLimitConfig:
        """Get config for a service, using default if not found."""
        if service not in self._configs:
            # Use web_scraper as default
            log.warning(f"No rate limit config for '{service}', using web_scraper defaults")
            return self._configs.get("web_scraper", RateLimitConfig(calls=10, period=60))
        return self._configs[service]

    def _get_state(self, service: str) -> RateLimitState:
        """Get or create state for a service."""
        with self._global_lock:
            if service not in self._states:
                self._states[service] = RateLimitState()
            return self._states[service]

    def _cleanup_old_timestamps(self, state: RateLimitState, config: RateLimitConfig) -> None:
        """Remove timestamps older than the rate limit period."""
        cutoff = time.time() - config.period
        state.timestamps = [ts for ts in state.timestamps if ts > cutoff]

    def can_proceed(self, service: str) -> bool:
        """
        Check if a call can proceed without exceeding rate limits.

        Args:
            service: The service name to check

        Returns:
            True if call can proceed, False otherwise
        """
        config = self._get_config(service)
        state = self._get_state(service)

        with state.lock:
            self._cleanup_old_timestamps(state, config)
            max_calls = config.calls + config.burst
            return len(state.timestamps) < max_calls

    def record_call(self, service: str) -> None:
        """
        Record that a call was made to a service.

        Args:
            service: The service name
        """
        state = self._get_state(service)
        with state.lock:
            state.timestamps.append(time.time())

    def get_wait_time(self, service: str) -> float:
        """
        Get time to wait before next call is allowed.

        Args:
            service: The service name

        Returns:
            Seconds to wait (0 if can proceed immediately)
        """
        config = self._get_config(service)
        state = self._get_state(service)

        with state.lock:
            self._cleanup_old_timestamps(state, config)
            max_calls = config.calls + config.burst

            if len(state.timestamps) < max_calls:
                return 0.0

            # Calculate wait time until oldest timestamp expires
            oldest = min(state.timestamps)
            wait = (oldest + config.period) - time.time()
            return max(0.0, wait)

    def wait_if_needed(self, service: str) -> float:
        """
        Wait if rate limit would be exceeded.

        Args:
            service: The service name

        Returns:
            Actual time waited in seconds
        """
        wait_time = self.get_wait_time(service)
        if wait_time > 0:
            log.debug(f"Rate limit: waiting {wait_time:.2f}s for {service}")
            time.sleep(wait_time)
        return wait_time

    @contextmanager
    def limit(self, service: str):
        """
        Context manager for rate-limited operations.

        Usage:
            with limiter.limit("github"):
                make_api_call()
        """
        self.wait_if_needed(service)
        try:
            yield
        finally:
            self.record_call(service)

    def get_stats(self, service: str) -> dict:
        """
        Get current rate limit stats for a service.

        Args:
            service: The service name

        Returns:
            Dict with calls_made, calls_remaining, reset_in
        """
        config = self._get_config(service)
        state = self._get_state(service)

        with state.lock:
            self._cleanup_old_timestamps(state, config)
            calls_made = len(state.timestamps)
            max_calls = config.calls + config.burst
            calls_remaining = max(0, max_calls - calls_made)

            reset_in = 0.0
            if state.timestamps:
                oldest = min(state.timestamps)
                reset_in = max(0.0, (oldest + config.period) - time.time())

            return {
                "service": service,
                "calls_made": calls_made,
                "calls_remaining": calls_remaining,
                "max_calls": max_calls,
                "period": config.period,
                "reset_in": reset_in,
            }

    def reset(self, service: Optional[str] = None) -> None:
        """
        Reset rate limit state for a service or all services.

        Args:
            service: Service to reset, or None to reset all
        """
        with self._global_lock:
            if service:
                if service in self._states:
                    self._states[service] = RateLimitState()
            else:
                self._states.clear()


class AsyncRateLimiter:
    """
    Async-compatible rate limiter.

    Usage:
        limiter = AsyncRateLimiter()

        async with limiter.limit("github"):
            await make_api_call()
    """

    def __init__(self, configs: Optional[dict[str, RateLimitConfig]] = None):
        self._sync_limiter = RateLimiter(configs)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def can_proceed(self, service: str) -> bool:
        """Check if a call can proceed."""
        return self._sync_limiter.can_proceed(service)

    async def record_call(self, service: str) -> None:
        """Record a call."""
        self._sync_limiter.record_call(service)

    async def get_wait_time(self, service: str) -> float:
        """Get wait time."""
        return self._sync_limiter.get_wait_time(service)

    async def wait_if_needed(self, service: str) -> float:
        """Wait if rate limit would be exceeded."""
        wait_time = self._sync_limiter.get_wait_time(service)
        if wait_time > 0:
            log.debug(f"Rate limit: waiting {wait_time:.2f}s for {service}")
            await asyncio.sleep(wait_time)
        return wait_time

    @contextmanager
    async def limit(self, service: str):
        """Async context manager for rate-limited operations."""
        async with self._locks[service]:
            await self.wait_if_needed(service)
            try:
                yield
            finally:
                await self.record_call(service)


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def rate_limited(service: str):
    """
    Decorator for rate-limited functions.

    Usage:
        @rate_limited("github")
        def fetch_repo(url):
            return requests.get(url)
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            with limiter.limit(service):
                return func(*args, **kwargs)

        return wrapper

    return decorator

