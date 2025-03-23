
from onyx.ai_task import Claude
from mermaid import setup_mermaid_docs, serve_docs

from prompt_loader import get_system_prompt, format_prompt
from onyx import get_logger, print_fancy
from pathlib import Path
from onyx import config
from save_code_from_md import save_code_from_md

logger = get_logger(__name__)

def create_architecture_diagrams(mvp_content, project_name):
    """Generate class diagrams, ERD, and architecture explanation based on MVP plan."""
    logger.info("Creating Architecture Diagrams...")
    system_prompt = get_system_prompt("architect", "diagrams")

    prompt = format_prompt(
        persona="architect", 
        prompt_name="diagrams", 
        project_name=project_name, 
        mvp_content=mvp_content
    )

    architect = Claude()
    diagrams_response = architect.send_prompt(prompt, system_prompt=system_prompt)

    return diagrams_response


def generate_skeleton(mvp_content, diagrams_content, project_name):
    """Generate skeleton project based on MVP plan and architecture diagrams."""
    logger.info("Creating System Skeleton...")
    system_prompt = get_system_prompt("architect", "skeleton")
    prompt = format_prompt(
        persona="architect",
        prompt_name="skeleton",
        project_name=project_name,
        mvp_content=mvp_content,
        diagrams_content=diagrams_content,
    )

    architect = Claude()
    architecture_response = architect.send_prompt(
        prompt, system_prompt=system_prompt, maximize=True
    )    

    return architecture_response


def run_architect(project_name: str):
    root_dir = Path(config.directories.projects)
    project_dir = Path(root_dir.expanduser() / project_name)
    planning_dir = Path(project_dir / "planning")

    # When the architect workflow begins, the MVP document should exist
    mvp_path = Path(planning_dir / "MVP.md").expanduser()

    # START Diagrams
    diagrams_path = Path(planning_dir / "ArchitectureDiagrams.md")

    # If diagrams response already exists, read it, otherwise send to Claude
    if diagrams_path.exists():
        logger.debug(f"Diagrams already exists at {diagrams_path}")
        print_fancy("Loading existing diagrams...", style="yellow")

        with open(diagrams_path, "r", encoding="utf-8") as file:
            diagrams_response = file.read()
    else:
        with open(mvp_path, "r", encoding="utf-8") as file:
            mvp_content = file.read()
        diagrams_response = create_architecture_diagrams(mvp_content, project_name)
        # Save raw response
        with open(diagrams_path, "w", encoding="utf-8") as file:
            file.write(diagrams_response)
        logger.info(f"Architecture diagrams saved to {diagrams_path}")

    save_code_from_md(
        markdown=diagrams_response, 
        language="mermaid", 
        output_dir=Path(planning_dir)
    )

    logger.info("Generated mermaid diagrams for documentation.")

    setup_mermaid_docs(project_dir)
    serve_docs(project_dir)
    # END Diagrams

    # START Skeleton
    skeleton_md_path = Path(planning_dir / "Architecture.md")

    # If skeleton response already exists, read it, otherwise send to Claude
    if skeleton_md_path.exists():
        logger.debug(f"Skeleton already exists at {skeleton_md_path}")
        print_fancy("Loading existing skeleton...", style="yellow")

        with open(skeleton_md_path, "r", encoding="utf-8") as file:
            skeleton_response = file.read()
    else:
        with open(mvp_path, "r", encoding="utf-8") as file:
            mvp_content = file.read()

        with open(diagrams_path, "r", encoding="utf-8") as file:
            diagrams_content = file.read()

        skeleton_response = generate_skeleton(
            mvp_content, diagrams_content, project_name
        )
        # Save raw response
        with open(skeleton_md_path, "w", encoding="utf-8") as file:
            file.write(skeleton_response)

    save_code_from_md(
        markdown=skeleton_response, 
        language="swift", 
        output_dir=Path(project_dir / project_name)
    )
    # END Skeleton



if __name__ == "__main__":
    run_architect()