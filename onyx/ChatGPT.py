"""
ChatGPT.py - Handles communication with the OpenAI API for ChatGPT
"""

import logging
import os
import time
import random
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional, Dict
from rich.console import Console

logger = logging.getLogger("chatgpt")
console = Console()

class ChatGPT:
    """Handles communication with the OpenAI API."""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4-turbo"
        self.max_tokens = 2000
        
    def send_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a prompt to ChatGPT and return the response."""
        console.print("[bold green]Sending request to ChatGPT...[/bold green]")
        
        try:
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            return content
            
        except Exception as e:
            logger.error(f"Error in ChatGPT API request: {str(e)}")
            # On error, return a message indicating the failure
            return f"Error querying ChatGPT: {str(e)}"
    
    def analyze_build_errors(self, file_path: str, errors: list, file_content: str) -> str:
        """Analyze build errors using ChatGPT."""
        # Format the errors into a string
        error_descriptions = "\n".join([f"Error at line {e.line}: {e.message}" for e in errors])
        
        # Create the prompt
        prompt = f"""I have Swift build errors in the following file:

```swift
{file_content}
```

Build errors:
{error_descriptions}

Please analyze these errors and provide:
1. A detailed explanation of what's causing each error
2. Specific recommendations on how to fix each error
3. Any potential namespace/type conflicts you notice
4. Best practices that should be applied in the fix

Focus on analysis rather than rewriting the entire file.
"""
        
        system_prompt = """You are an expert Swift developer specializing in iOS development. 
Your task is to analyze Swift build errors and provide detailed explanations and recommendations.
Focus on root causes and specific fixes rather than completely rewriting the code."""
        
        # Send to ChatGPT and return the analysis
        return self.send_prompt(prompt, system_prompt)