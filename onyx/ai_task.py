from typing import Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv
from rate_limiter import RateLimiter
from api_error_handler import ApiErrorHandler
from onyx import get_logger
logger = get_logger(__name__)

class Claude:
    """Handles communication with the Anthropic API."""
    def __init__(self):
        load_dotenv(override=True)
        self.client = Anthropic()
        self.model = "claude-3-7-sonnet-20250219"
        self.max_tokens = 25000

        self.rate_limiter = RateLimiter(
            requests_per_minute=3, token_limit_per_minute=16000
        )
        self.error_handler = ApiErrorHandler(max_retries=5, base_wait=5, max_wait=120)

        self.send_prompt = self.rate_limiter.with_rate_limiting(
            self.error_handler.with_retries(self._send_prompt)
        )

    def _send_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, str]] = None,
        system_prompt: Optional[str] = "",
        maximize: bool = False,
    ) -> str:
        """Send a prompt to Claude with retry logic for rate limits and other errors."""
        headers = {}
        tokens = 25000
        if maximize:
            headers = {"anthropic-beta": "output-128k-2025-02-19"}
            tokens = 128000

        estimated_tokens = (
            estimate_tokens(prompt) + estimate_tokens(system_prompt) + tokens
        )
        self.rate_limiter.register_token_usage(estimated_tokens)

        response = ""

        try:
            with Anthropic().messages.stream(
                model="claude-3-7-sonnet-20250219",
                max_tokens=tokens,
                temperature=1,
                thinking={"type": "enabled", "budget_tokens": 24000},
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                extra_headers=headers,
            ) as stream:
                for chunk in stream:
                    if hasattr(chunk, "type"):
                        if chunk.type == "text":
                            response += chunk.text

            return response

        except Exception as e:
            logger.error(f"Error in Claude API request: {str(e)}")
            raise

def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a string of text.
    This is a rough estimate - about 4 characters per token for English text."""
    if not text:
        return 0
    return len(text) // 4

