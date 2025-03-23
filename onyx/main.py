
import planning_pipeline as planning_pipeline
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
   

def develop_layers(prompt, sys_prompt, project_dir, project_name):
    engineer = Claude()
    response = engineer.send_prompt(prompt, system_prompt=sys_prompt, maximize=True)
    save_code_from_md(
        markdown=response, language="swift", output_dir=Path(project_dir / project_name)
    )

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

    project_dir = Path(config.directories.projects).expanduser() / project_name

    # STEP 1: Create Xcode project first
    logger.info("STEP 1: Setting up initial Xcode project structure")
    create_project(project_dir, project_name)

    # STEP 3: Now proceed with the planning workflow
    logger.info("\nSTEP 2: Starting planning workflow")
    workflow = planning_pipeline.AppPlanningWorkflow(project_dir)
    workflow.run_workflow(app_idea, project_name)

    run_architect(project_name)
    
    output_dir = Path(project_dir / project_name)
        
    with open(Path(project_dir / "planning" / "ArchitectureDiagrams.md"), 'r', encoding='utf-8') as f:
        diagrams_content = f.read()

    import glob
    from collections import defaultdict
    
    layers = ["Models", "Services", "ViewModels", "Views"]
    
    for layer in layers:
        output_dir = Path(output_dir)
        matching_files = glob.glob(str(output_dir / "**" / "*.swift"), recursive=True)
        grouped_files = defaultdict(list)

        for file_path in matching_files:
            path_parts = Path(file_path).parts
            for dir_name in layers:
                if dir_name in path_parts:
                    grouped_files[dir_name].append(file_path)
                    break

        logger.info(f"Developing {layer} files...")
        additional_rules = ""
        
        (sys_prompt, base_prompt) = get_dev_prompts(layer, diagrams_content, grouped_files[layer], additional_rules)
        
        develop_layers(base_prompt, sys_prompt, project_dir, project_name)

        logger.info("Fixing build errors...")
        output_dir = str(Path(config.directories.projects).expanduser() / project_name)

        iteration = 0
        while True:
            print(f"\n--- Build Attempt {iteration + 1} ---\n")
            errors = build_xcode_project(output_dir)
            # Filter to actual errors (not warnings or messages)
            actual_errors = [e for e in errors if e.type == "error"]

            if not actual_errors:
                print("✅ Build succeeded with no errors.")
                break

            fix(project_name, actual_errors)
            iteration += 1

if __name__ == "__main__":
    main()