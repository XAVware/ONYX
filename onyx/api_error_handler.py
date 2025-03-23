from typing import Callable
from anthropic import APIStatusError, APITimeoutError, APIConnectionError
import time
import random
from datetime import datetime, timedelta
import json
import re
from onyx import get_logger

logger = get_logger(__name__)

class ApiErrorHandler:
    """Handles API errors with exponential backoff."""

    def __init__(self, max_retries=5, base_wait=2, max_wait=60):
        """Initialize error handler with retry configuration."""
        self.max_retries = max_retries
        self.base_wait = base_wait
        self.max_wait = max_wait
        self.rate_limit_encounters = 0
        self.last_rate_limit_time = None

    def parse_error_message(self, error) -> dict:
        """Extract useful information from the error message."""
        result = {
            "is_rate_limit": False,
            "retry_after": None,
            "token_limit": False,
            "connection_error": False,
            "timeout_error": False,
            "server_error": False,
            "overloaded": False,
            "error_message": str(error),
        }

        error_str = str(error).lower()

        try:
            if isinstance(error, APIStatusError):
                error_dict = error.body
                if isinstance(error_dict, dict) and "error" in error_dict:
                    error_type = error_dict.get("error", {}).get("type", "")
                    if error_type == "overloaded_error" or "overloaded" in error_type:
                        result["overloaded"] = True
            elif isinstance(error, str) and (
                '{"type":"error"' in error or "{'type': 'error'" in error
            ):
                error_json = re.search(r"(\{.*\})", error_str)
                if error_json:
                    error_dict = json.loads(error_json.group(1).replace("'", '"'))
                    if isinstance(error_dict, dict) and "error" in error_dict:
                        error_type = error_dict.get("error", {}).get("type", "")
                        if (
                            error_type == "overloaded_error"
                            or "overloaded" in error_type
                        ):
                            result["overloaded"] = True
        except (json.JSONDecodeError, AttributeError, ValueError) as _:
            pass

        if "overloaded" in error_str:
            result["overloaded"] = True

        # Check for rate limit errors
        if any(
            term in error_str for term in ["rate_limit", "429", "too many requests"]
        ):
            result["is_rate_limit"] = True

            retry_match = re.search(r"retry[\s-]after[:\s]+(\d+)", error_str)
            if retry_match:
                result["retry_after"] = int(retry_match.group(1))

            if "token" in error_str and any(
                term in error_str for term in ["limit", "exceed"]
            ):
                result["token_limit"] = True

        if (
            isinstance(error, (APIConnectionError, ConnectionError))
            or "connection" in error_str
        ):
            result["connection_error"] = True

        if isinstance(error, (APITimeoutError, TimeoutError)) or "timeout" in error_str:
            result["timeout_error"] = True

        if isinstance(error, APIStatusError):
            status_code = getattr(error, "status_code", None)
            if status_code and str(status_code).startswith(("5", "503")):
                result["server_error"] = True

        return result

    def with_retries(self, func: Callable) -> Callable:
        """Decorator to apply retries with exponential backoff."""

        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            backoff_factor = 1.0

            while retries <= self.max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    retries += 1

                    error_info = self.parse_error_message(e)

                    should_retry = (
                        error_info["is_rate_limit"]
                        or error_info["connection_error"]
                        or error_info["timeout_error"]
                        or error_info["server_error"]
                        or error_info["overloaded"]
                    )

                    if not should_retry or retries > self.max_retries:
                        logger.error(
                            f"Non-retryable error or max retries exceeded: {str(e)}"
                        )
                        raise

                    now = datetime.now()

                    if error_info["is_rate_limit"]:
                        if error_info["retry_after"]:
                            wait_time = error_info["retry_after"] + random.uniform(1, 5)
                        else:
                            wait_time = 30.0 + random.uniform(1, 5)

                        if error_info["token_limit"]:
                            wait_time = max(wait_time, 60.0)

                        self.rate_limit_encounters += 1
                        # Progressive backoff for frequent rate limits
                        if (
                            self.last_rate_limit_time
                            and now - self.last_rate_limit_time < timedelta(minutes=2)
                        ):
                            backoff_factor = min(backoff_factor * 1.5, 3.0)
                            wait_time = min(wait_time * backoff_factor, 120)
                            logger.warning(
                                f"Multiple rate limits detected. Extended wait to {wait_time:.1f}s"
                            )
                        else:
                            backoff_factor = 1.0

                        self.last_rate_limit_time = now
                        logger.warning(
                            f"Rate limit error: {error_info['error_message']}. Waiting {wait_time:.1f}s before retry {retries}/{self.max_retries}"
                        )

                    elif error_info["overloaded"]:
                        wait_time = min(
                            self.max_wait, self.base_wait * (2 ** (retries - 1))
                        )
                        wait_time = max(wait_time, 10)
                        wait_time = wait_time + random.uniform(1, 5)  # Jitter
                        logger.warning(
                            f"Anthropic API overloaded. Waiting {wait_time:.1f}s before retry {retries}/{self.max_retries}"
                        )

                    elif error_info["connection_error"] or error_info["timeout_error"]:
                        wait_time = min(
                            self.max_wait, self.base_wait * (1.5 ** (retries - 1))
                        )
                        wait_time = wait_time + random.uniform(0, 2)  # Small jitter
                        logger.warning(
                            f"Connection/timeout error: {error_info['error_message']}. Retry {retries}/{self.max_retries} after {wait_time:.1f}s"
                        )

                    else:
                        wait_time = min(
                            self.max_wait, self.base_wait * (2 ** (retries - 1))
                        )
                        wait_time = wait_time + random.uniform(
                            0, wait_time * 0.1
                        )  # Small jitter
                        logger.warning(
                            f"API error: {error_info['error_message']}. Retry {retries}/{self.max_retries} after {wait_time:.1f}s"
                        )

                    for remaining in range(int(wait_time), 0, -5):
                        if remaining % 15 == 0 or remaining <= 5:
                            logger.info(f"Retrying in {remaining}s...")
                        time.sleep(min(5, remaining))

            raise last_error

        return wrapper
