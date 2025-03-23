
import logging
import os
from pathlib import Path
from rich.logging import RichHandler
from rich.style import Style
from rich.theme import Theme
from rich.console import Console
import datetime
from .config import config, AppConfig  # noqa: F401
import re
logger = logging.getLogger("onyx")

log_level_name = os.environ.get("ONYX_LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

logger.setLevel(log_level)

custom_theme = Theme(
    {
        "logging.level.debug": Style(color="cyan", bold=True),
        "logging.level.info": Style(color="blue", bold=True),
        "logging.level.warning": Style(color="yellow", bold=True),
        "logging.level.error": Style(color="red", bold=True),
        "logging.level.critical": Style(color="white", bgcolor="red", bold=True),
        "logging.level.name": Style(color="green")
    }
)

rich_console = Console(theme=custom_theme)

console_handler = RichHandler(
    console=rich_console,
    rich_tracebacks=True,
    markup=False,
    show_time=False,
    show_level=True,
    show_path=False
)
console_handler.setLevel(log_level)

class ColorlessFormatter(logging.Formatter):
    """A formatter that doesn't include color codes in file logs"""
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        
    def format(self, record):
        formatted_message = super().format(record)
        clean_message = re.sub(r'\[(/?[a-zA-Z0-9_\-\s]+)\]', '', formatted_message)
        return clean_message

file_formatter = ColorlessFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

try:
    log_dir = Path(config.directories.logging).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_filename = f"{today}.log"
    file_handler = logging.FileHandler(log_dir / log_filename)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as _:
    # Don't fail if log can't be created
    pass

logger.addHandler(console_handler)

logger.propagate = False

def get_logger(name):
    """Get a logger for a specific module."""
    if name.startswith("onyx."):
        module_logger = logging.getLogger(name)
    else:
        module_logger = logging.getLogger(f"onyx.{name}")
    
    return module_logger

def print_fancy(message, style=None, highlight=False, panel=False, title=None):
    """Print a fancy message using Rich styling."""
    logger.info(message)
    if panel:
        from rich.panel import Panel
        panel_obj = Panel(message, title=title, style=style or "")
        rich_console.print(panel_obj)
    else:
        rich_console.print(message, style=style, highlight=highlight)
