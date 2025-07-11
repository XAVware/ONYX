
from onyx.ai_task import Claude
from prompt_loader import get_prompt_and_system
from xcode_service import create_project, build_xcode_project
from onyx import get_logger, print_fancy
from save_code_from_md import save_code_from_md
from onyx import config
from fix import fix

import argparse
from typing import Optional
from pathlib import Path

from run_architect import run_architect

logger = get_logger(__name__)

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="ONYX")
    parser.add_argument("app_idea", nargs="?", help="App idea to develop (e.g., 'An app to track my fitness')")
    parser.add_argument("--project-name", "-n", help="Name for the project")
    parser.add_argument("--project-dir", "-d", help="Project directory (default: Projects/[ProjectName])")
    parser.add_argument("--root-dir", "-r", help="Root directory for projects")
    return parser.parse_args()

def get_dev_prompts(
    layer: str,
    diagrams_content: str,
    file_content: str,
    additional: Optional[str] = None,
) -> tuple[str, str]:
    """Get development prompts for specific layer using prompt loader."""
    prompt_name = f"develop_{layer.lower()}"

    system_prompt, prompt = get_prompt_and_system(
        "developer",
        prompt_name,
        layer=layer,
        diagrams_content=diagrams_content,
        file_content=file_content,
        additional=additional or "",
    )
    return system_prompt, prompt

    
def develop_layers(prompt, sys_prompt, project_dir: Path):
    engineer = Claude()
    response = engineer.send_prompt(prompt, system_prompt=sys_prompt, maximize=True)
    save_code_from_md(markdown=response, language="swift", output_dir=project_dir / project_dir.name)


def get_data(path: Path) -> str:
    if path.exists():
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

def main():
    # Set root in config/config.json. Defaults to ~/ONYX/
    args = parse_arguments()

    app_idea = args.app_idea
    if not app_idea:
        print_fancy("Please provide an app idea.", "cyan", panel=True)
        app_idea = input("Idea: ")

    project_name = args.project_name
    if not project_name:
        print_fancy("Please provide a project name.", "cyan", panel=True)
        project_name = input("Project Name: ")

    # The app directory is the Projects directory / {app name}
    app_dir = Path(config.directories.projects).expanduser() / project_name
    # The app should have a planning directory - /Projects/AppName/planning
    planning_dir = app_dir / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    # And a source directory - /Projects/AppName/AppName
    source_dir = app_dir / app_dir.name
    source_dir.mkdir(parents=True, exist_ok=True)


    # STEP 1: Create Xcode project first
    logger.info("STEP 1: Setting up initial Xcode project structure")
    # create_project(app_dir)

    # STEP 3: Now proceed with the planning workflow
    logger.info("\nSTEP 2: Starting planning workflow")
    # Step 1: Generate or load Business Plan
    business_plan_path = planning_dir / "Business_Plan.md"
    business_plan = get_data(business_plan_path)
    if not business_plan:
        system_prompt, prompt = get_prompt_and_system(
            "entrepreneur", "business_plan", app_idea=app_idea, app_name=project_name
        )
        logger.info("Generating Business Plan...")
        business_plan = Claude().send_prompt(prompt, system_prompt=system_prompt)
        with open(business_plan_path, "w", encoding="utf-8") as file:
            file.write(business_plan)


    # Step 1: Generate or load Business Plan
    backlog_path = planning_dir / "Agile_Planner.md"
    backlog = get_data(backlog_path)
    if not backlog:
        system_prompt, prompt = get_prompt_and_system(
            "project_manager", "user_stories", business_plan=business_plan
        )
        logger.info("Generating User Stories and Backlog...")
        backlog = Claude().send_prompt(prompt, system_prompt=system_prompt)
        with open(backlog_path, "w", encoding="utf-8") as file:
            file.write(backlog)


    # Step 1: Generate or load Business Plan
    mvp_path = planning_dir / "MVP.md"
    mvp_plan = get_data(mvp_path)
    if not mvp_plan:
        system_prompt, prompt = get_prompt_and_system(
            "project_manager",
            "mvp",
            business_plan=business_plan,
            backlog_csv=backlog,
        )
        logger.info("Generating User Stories and Backlog...")
        mvp_plan = Claude().send_prompt(prompt, system_prompt=system_prompt)
        with open(mvp_path, "w", encoding="utf-8") as file:
            file.write(mvp_plan)

    run_architect(app_dir)
    
        
    with open(
        Path(app_dir / "planning" / "ArchitectureDiagrams.md"), "r", encoding="utf-8"
    ) as f:
        diagrams_content = f.read()

    import glob
    from collections import defaultdict
    
    layers = ["Models", "Services", "ViewModels", "Views"]
    
    for layer in layers:
        matching_files = glob.glob(str(app_dir / "**" / "*.swift"), recursive=True)
        grouped_files = defaultdict(list)

        for file_path in matching_files:
            path_parts = Path(file_path).parts
            for dir_name in layers:
                if dir_name in path_parts:
                    grouped_files[dir_name].append(file_path)
                    break

        logger.info(f"Developing {layer} files...")
        system_prompt, prompt = get_prompt_and_system(
            "developer",
            "engineer",
            layer=layer,
            diagrams_content=diagrams_content,
            file_content=grouped_files[layer],
        )
        
        develop_layers(prompt, system_prompt, app_dir)

    logger.info("Fixing build errors...")
    # output_dir = str(Path(config.directories.projects).expanduser() / project_name)
    
    iteration = 0
    while True:
        print(f"\n--- Build Attempt {iteration + 1} ---\n")
        errors = build_xcode_project(app_dir)
        # Filter to actual errors (not warnings or messages)
        actual_errors = [e for e in errors if e.type == "error"]

        if not actual_errors:
            print("✅ Build succeeded with no errors.")
            break

        fix(app_dir, actual_errors)
        iteration += 1

if __name__ == "__main__":
    main()