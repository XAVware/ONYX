
from onyx import get_logger, config
from pathlib import Path
from save_code_from_md import save_code_from_md
from xcode_service import BuildMessage
from typing import List
from onyx.ai_task import Claude
from prompt_loader import get_system_prompt, format_prompt

logger = get_logger(__name__)

def get_all_swift_code(project_dir: Path) -> str:
    swift_files = project_dir.rglob("*.swift")
    all_code = []
    for file in swift_files:
        try:
            content = file.read_text()
            all_code.append(f"// {file.relative_to(project_dir)}\n{content}")
        except Exception as e:
            print(f"Could not read {file}: {e}")
    return "\n\n".join(all_code)

def fix(project_name: str, errors: List[BuildMessage]):
    root_dir = Path(config.directories.projects)
    project_name = project_name
    project_dir = Path(root_dir.expanduser() / project_name)
    errors = filter(lambda x: x.type == "error", errors)
    for err in errors:
        logger.error(err.file + "\n" + err.message + "\n")

    all_code = get_all_swift_code(project_dir)

    # Send to AI
    logger.info("Fixing Errors...")
    system_prompt = get_system_prompt("debugger", "send_all_errors")
    prompt = format_prompt(
        persona="debugger", prompt_name="send_all_errors", errors=errors, all_code=all_code
    )

    architect = Claude()
    response = architect.send_prompt(
        prompt, system_prompt=system_prompt, maximize=True
    )

    save_code_from_md(
        markdown=response,
        language="swift",
        output_dir=Path(project_dir / project_name),
    )

if __name__ == "__main__":
    from xcode_service import build_xcode_project
    from pathlib import Path

    project_name = "SoFit"
    project_path = str(Path(config.directories.projects).expanduser() / project_name)

    iteration = 0
    while True:
        print(f"\n--- Build Attempt {iteration + 1} ---\n")
        errors = build_xcode_project(project_path)
        actual_errors = [e for e in errors if e.type == "error"]

        if not actual_errors:
            print("✅ Build succeeded with no errors.")
            break

        fix(project_name, actual_errors)
        iteration += 1
