"""
ClaudeRateLimiter.py - Utilities for rate limiting Claude API calls
"""

import time
import threading
import random
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger("claudeutils")

class RateLimiter:
    """Rate limits requests to the Claude API."""
    
    def __init__(self, requests_per_minute=3, burst_limit=3):
        """Initialize rate limiter with configurable limits."""
        self.rpm = requests_per_minute
        self.burst_limit = burst_limit
        self.request_times = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if needed to stay under the rate limit."""
        with self.lock:
            now = datetime.now()
            
            # Remove requests older than a minute
            self.request_times = [t for t in self.request_times if now - t < timedelta(minutes=1)]
            
            # If we're under the limit, no need to wait
            if len(self.request_times) < self.rpm:
                self.request_times.append(now)
                return 0
            
            # If we're over the burst limit, wait
            if len(self.request_times) >= self.burst_limit:
                # Wait until the oldest request is a minute old
                wait_time = (self.request_times[0] + timedelta(minutes=1) - now).total_seconds()
                wait_time = max(wait_time, 0) + random.uniform(0.1, 1.0)  # Add jitter
                logger.warning(f"Rate limit preemptively applied. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                
                # Update timing after sleep
                now = datetime.now()
                self.request_times = [t for t in self.request_times if now - t < timedelta(minutes=1)]
            
            # Add current request
            self.request_times.append(now)
            
            # Calculate time to next available slot (for logging)
            if len(self.request_times) >= self.rpm:
                next_slot = (self.request_times[0] + timedelta(minutes=1) - now).total_seconds()
                logger.info(f"Using {len(self.request_times)}/{self.rpm} requests. Next slot in {next_slot:.2f}s")
            
            return len(self.request_times)
    
    def with_rate_limiting(self, func):
        """Decorator to apply rate limiting to a function."""
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper

class ApiErrorHandler:
    """Handles API errors with exponential backoff."""
    
    def __init__(self, max_retries=5, base_wait=2, max_wait=60):
        """Initialize error handler with retry configuration."""
        self.max_retries = max_retries
        self.base_wait = base_wait
        self.max_wait = max_wait
        # Keep track of rate limit encounters to adjust backoff strategy
        self.rate_limit_encounters = 0
        self.last_rate_limit_time = None
    
    def with_retries(self, func):
        """Decorator to apply retries with exponential backoff."""
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            
            while retries <= self.max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    retries += 1
                    
                    # Check if it's a rate limit error
                    error_str = str(e).lower()
                    is_rate_limit = any(s in error_str for s in ['rate_limit', '429'])
                    
                    # Check if it's another retryable error
                    other_retryable = any(s in error_str for s in ['timeout', 'connection', 'overloaded', '500', '503'])
                    
                    # If not retryable or max retries exceeded, raise the error
                    if (not is_rate_limit and not other_retryable) or retries > self.max_retries:
                        logger.error(f"Non-retryable error or max retries exceeded: {str(e)}")
                        raise
                    
                    # Handle rate limit errors with special care
                    if is_rate_limit:
                        # Use fixed 30 second wait for rate limit errors
                        wait_time = 30.0 + random.uniform(0, 5.0)  # 30-35 seconds with jitter
                        
                        # Update rate limit encounter metrics
                        now = datetime.now()
                        self.rate_limit_encounters += 1
                        
                        # If we've had multiple rate limits in a short time, increase wait time
                        if (self.last_rate_limit_time and 
                            now - self.last_rate_limit_time < timedelta(minutes=2)):
                            # Additional backoff for frequent rate limits
                            wait_time = min(wait_time * (1.5 * self.rate_limit_encounters), 90)
                            logger.warning(f"Multiple rate limits detected. Extended wait to {wait_time:.1f}s")
                        
                        self.last_rate_limit_time = now
                        logger.warning(f"Rate limit error: {str(e)}. Waiting {wait_time:.1f}s before retry {retries}/{self.max_retries}")
                    else:
                        # Regular exponential backoff for other errors
                        wait_time = min(self.max_wait, self.base_wait * (2 ** (retries - 1)))
                        wait_time = wait_time + random.uniform(0, wait_time * 0.1)  # Add small jitter
                        logger.warning(f"API error: {str(e)}. Retry {retries}/{self.max_retries} after {wait_time:.1f}s")
                    
                    time.sleep(wait_time)
            
            # We should never get here, but just in case
            raise last_error
        
        return wrapper

def parse_rate_limit_headers(headers):
    """Parse rate limit information from response headers."""
    rate_info = {}
    
    # Common rate limit header patterns
    headers_to_check = {
        'x-ratelimit-remaining': 'remaining',
        'x-ratelimit-limit': 'limit',
        'x-ratelimit-reset': 'reset',
        'retry-after': 'retry_after'
    }
    
    # Extract values from headers
    for header, key in headers_to_check.items():
        if header in headers:
            try:
                rate_info[key] = int(headers[header])
            except (ValueError, TypeError):
                rate_info[key] = headers[header]
    
    return rate_info