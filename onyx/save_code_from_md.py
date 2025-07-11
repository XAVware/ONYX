from onyx import get_logger
from pathlib import Path
import re

logger = get_logger(__name__)

def save_code_from_md(markdown: str, language: str, output_dir: Path) -> None:
    """
    Extract and save code blocks from markdown into project_dir / app_name / relative_path.language.

    Args:
        markdown: The original markdown content
        language: The language to extract from code blocks. Not case sensitive - lowercase enforced.
        output_dir: The parent directory that files and directories should be saved to.
    """
    sections = re.split(r"^##\s+", markdown, flags=re.MULTILINE)
    code_pattern = re.compile(
        rf"```{re.escape(language.lower())}\s*(.*?)```", re.DOTALL
    )

    count = 0
    for section in sections[1:]:
        lines = section.strip().split("\n", 1)
        if len(lines) < 2:
            continue
        rel_path, body = lines[0].lstrip("/"), lines[1]
        match = code_pattern.search(body)
        if not match:
            continue
        file_path = output_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(match.group(1).strip(), encoding="utf-8")
        count += 1

    logger.info(f"Parsed and saved {count} code blocks")