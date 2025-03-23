"""
config.py - Centralized configuration using JSON and dataclasses
"""

import json
from dataclasses import dataclass
from pathlib import Path
from dataclasses_json import dataclass_json

# Define path to config file
CONFIG_FILE = Path(__file__).parent.parent / "config" / "config.json"


@dataclass_json
@dataclass
class DirectoryConfig:
    root: str
    projects: str
    logging: str
    resources: str


@dataclass_json
@dataclass
class XcodeConfig:
    development_team_id: str
    bundle_id_prefix: str
    project_template_path: str


@dataclass_json
@dataclass
class AppConfig:
    directories: DirectoryConfig
    xcode: XcodeConfig


def load_config() -> AppConfig:
    """Load configuration from JSON and return an AppConfig object."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return AppConfig.from_dict(data)


# Load config globally
config: AppConfig = load_config()
