import time
import threading
import random
from datetime import datetime, timedelta
from onyx import get_logger
from typing import Callable

logger = get_logger(__name__)
class RateLimiter:
    """Rate limits requests to the Claude API based on both request count and token usage."""

    def __init__(
        self, requests_per_minute=3, token_limit_per_minute=16000, max_backlog=20
    ):
        """Initialize rate limiter with configurable limits."""
        self.rpm = requests_per_minute
        self.token_limit = token_limit_per_minute
        self.max_backlog = max_backlog
        self.request_times = []
        self.token_usage = []
        self.lock = threading.Lock()
        self.waiting = False

    def register_token_usage(self, token_count: int):
        """Register token usage for tracking."""
        with self.lock:
            now = datetime.now()
            self.token_usage.append((now, token_count))

    def wait_if_needed(self):
        """Wait if needed to stay under the rate limit."""
        with self.lock:
            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)

            self.request_times = [t for t in self.request_times if t > one_minute_ago]
            self.token_usage = [
                (t, count) for t, count in self.token_usage if t > one_minute_ago
            ]

            current_requests = len(self.request_times)
            current_tokens = sum(count for _, count in self.token_usage)

            logger.info(
                f"Current usage: {current_requests}/{self.rpm} requests, {current_tokens}/{self.token_limit} tokens in last minute"
            )

            wait_time = 0
            reason = ""

            if current_requests >= self.rpm:
                time_until_slot = (
                    self.request_times[0] + timedelta(minutes=1) - now
                ).total_seconds()
                if time_until_slot > wait_time:
                    wait_time = time_until_slot
                    reason = f"request limit ({current_requests}/{self.rpm})"

            if current_tokens >= self.token_limit * 0.9:
                sorted_usage = sorted(self.token_usage, key=lambda x: x[0])
                tokens_to_expire = current_tokens - (self.token_limit * 0.7)
                tokens_expired = 0

                for timestamp, count in sorted_usage:
                    tokens_expired += count
                    if tokens_expired >= tokens_to_expire:
                        token_wait_time = (
                            timestamp + timedelta(minutes=1) - now
                        ).total_seconds()
                        if token_wait_time > wait_time:
                            wait_time = token_wait_time
                            reason = (
                                f"token limit ({current_tokens}/{self.token_limit})"
                            )
                        break

            # Avoid thundering herd problem
            if wait_time > 0:
                wait_time += random.uniform(0.5, 2.0)
                logger.warning(
                    f"Rate limiting due to {reason}. Waiting {wait_time:.2f} seconds"
                )

                self.waiting = True

                self.lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self.lock.acquire()
                    self.waiting = False

                now = datetime.now()
                one_minute_ago = now - timedelta(minutes=1)
                self.request_times = [
                    t for t in self.request_times if t > one_minute_ago
                ]
                self.token_usage = [
                    (t, count) for t, count in self.token_usage if t > one_minute_ago
                ]

            self.request_times.append(now)
            return current_requests

    def with_rate_limiting(self, func: Callable) -> Callable:
        """Decorator to apply rate limiting to a function."""

        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)

        return wrapper

