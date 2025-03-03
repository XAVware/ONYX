from typing import Dict, Optional, Any
import logging
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from anthropic import Anthropic
from dotenv import load_dotenv
import os
from ClaudeRateLimiter import RateLimiter, ApiErrorHandler

logger = logging.getLogger("ONYX")
console = Console()

class ClaudeContext:
    """Manages context for Claude"""
    def __init__(self, file_contents: Dict[str, str], max_context_chars: int = 10000):
        """Format file contents as context for Claude."""
        self.max_context_chars = max_context_chars
        self.context_parts = []
        self.total_size = 0
        
        # Sort files by size (smallest first)
        sorted_files = sorted(file_contents.items(), key=lambda x: len(x[1]))
        
        for file_path, content in sorted_files:
            # Check if adding this file would exceed our size limit
            file_size = len(content)
            if self.total_size + file_size > self.max_context_chars:
                logger.info(f"Skipping file {file_path} due to context size limitations")
                continue
                
            self.context_parts.append(f"File: {file_path}\n\n```\n{content}\n```\n\n")
            self.total_size += file_size
        
        logger.info(f"Using {self.total_size} characters of context in {len(self.context_parts)} files")
    
    def get_formatted_context(self):
        """Get the formatted context string."""
        return "".join(self.context_parts)

class Claude:
    """Handles communication with the Anthropic API."""
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic()
        self.model = "claude-3-7-sonnet-20250219"
        self.max_tokens = 25000
        
        # Initialize rate limiter and error handler
        self.rate_limiter = RateLimiter(requests_per_minute=3, burst_limit=3)
        self.error_handler = ApiErrorHandler(max_retries=5, base_wait=5, max_wait=120)
        
        # Apply decorators to the send_prompt method
        self.send_prompt = self.rate_limiter.with_rate_limiting(
            self.error_handler.with_retries(self._send_prompt)
        )

    def _send_prompt(self, prompt: str, context: Optional[Dict[str, str]] = None, 
                   system_prompt: Optional[str] = "",
                   maximize: bool = False) -> str:
        """Send a prompt to Claude with retry logic for rate limits and other errors."""
        formatted_context = ""
        if context:
            context_manager = ClaudeContext(context)
            formatted_context = context_manager.get_formatted_context()
                
        console.print("[bold green]Sending request to Claude...[/bold green]")
        
        headers = {}
        tokens = 25000
        if maximize:
            headers = {"anthropic-beta": "output-128k-2025-02-19"}
            tokens = 128000
        
        response = ""
        
        try:
            with Anthropic().messages.stream(
                model="claude-3-7-sonnet-20250219",
                max_tokens=tokens,
                temperature=1,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 16000
                },
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                extra_headers=headers
            ) as stream:
                for chunk in stream:
                    if hasattr(chunk, 'type'):
                        if chunk.type == 'text':
                            response += chunk.text
            
            return response

        except Exception as e:
            logger.error(f"Error in Claude API request: {str(e)}")
            raise
