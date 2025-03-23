
import yaml
from pathlib import Path
from typing import Dict, Any
from onyx import get_logger

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def load_prompt(persona: str, prompt_name: str) -> Dict[str, Any]:
    """Load a prompt configuration from a YAML file."""
    prompt_path = PROMPTS_DIR / persona / f"{prompt_name}.yaml"

    if not prompt_path.exists():
        logger.error(f"Prompt file not found: {prompt_path}")
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    try:
        with open(prompt_path, "r", encoding="utf-8") as file:
            prompt_config = yaml.safe_load(file)
        return prompt_config
    except Exception as e:
        logger.error(f"Error loading prompt {prompt_path}: {str(e)}")
        raise


def get_system_prompt(persona: str, prompt_name: str) -> str:
    """Get the system prompt from a prompt configuration."""
    prompt_config = load_prompt(persona, prompt_name)
    return prompt_config.get("system_prompt", "")


def format_prompt(persona: str, prompt_name: str, **kwargs) -> str:
    """Format a prompt template with the provided arguments."""
    prompt_config = load_prompt(persona, prompt_name)
    template = prompt_config.get("prompt_template", "")

    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing required parameter in prompt {prompt_name}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error formatting prompt {prompt_name}: {str(e)}")
        raise


def get_prompt_and_system(persona: str, prompt_name: str, **kwargs) -> tuple[str, str]:
    """Get both the system prompt and formatted user prompt as a tuple."""
    prompt_config = load_prompt(persona, prompt_name)
    system_prompt = prompt_config.get("system_prompt", "")
    template = prompt_config.get("prompt_template", "")

    try:
        formatted_prompt = template.format(**kwargs)
        return system_prompt, formatted_prompt
    except KeyError as e:
        logger.error(f"Missing required parameter in prompt {prompt_name}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error formatting prompt {prompt_name}: {str(e)}")
        raise
