from onyx.ai_task import Claude
# from xcode_service import create_project, build_xcode_project
from onyx import get_logger, print_fancy
from save_code_from_md import save_code_from_md
from onyx import config

import argparse
from typing import Optional
from pathlib import Path

from prompt_loader import get_prompt_and_system
from prompt_loader import get_system_prompt, format_prompt
from mermaid import setup_mermaid_docs, serve_docs

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


def get_text_from_filepath(path: Path) -> str:
    if path.exists():
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

def main():
    args = parse_arguments()

    app_idea = args.app_idea
    if not app_idea:
        print_fancy("Please provide an app idea.", "cyan", panel=True)
        app_idea = input("Idea: ")

    project_name = args.project_name
    if not project_name:
        print_fancy("Please provide a project name.", "cyan", panel=True)
        project_name = input("Project Name: ")

    # Directory specific to the current project
    project_directory = Path(config.directories.projects).expanduser() / project_name
    
    # Make the 'plans' directory if it doesn't already exist
    plans_directory = project_directory / "plans"
    plans_directory.mkdir(parents=True, exist_ok=True)

    # STEP 1: Create Xcode project first
    logger.info("STEP 1: Setting up initial Xcode project structure")
    # create_project(app_dir)

    # STEP 3: Now proceed with the planning workflow
    logger.info("\nSTEP 2: Starting planning workflow")
    # Step 1: Generate or load Business Plan
    business_plan_path = plans_directory / "Business_Plan.md"
    business_plan = get_text_from_filepath(business_plan_path)


    if not business_plan:
        system, prompt = get_prompt_and_system(
            "entrepreneur", 
            "business_plan", 
            app_idea=app_idea, 
            app_name=project_name
        )

        logger.info("Generating Business Plan...")
        business_plan = Claude().send_prompt(
            prompt, 
            system_prompt=system
        )

        with open(business_plan_path, "w", encoding="utf-8") as file:
            file.write(business_plan)


    backlog_path = plans_directory / "Agile_Planner.md"
    backlog = get_text_from_filepath(backlog_path)
    if not backlog:
        system, prompt = get_prompt_and_system(
            "project_manager", 
            "user_stories", 
            business_plan=business_plan
        )
        logger.info("Generating User Stories and Backlog...")
        backlog = Claude().send_prompt(prompt, system_prompt=system)
        with open(backlog_path, "w", encoding="utf-8") as file:
            file.write(backlog)


    # Step 1: Generate or load MVP Plan
    mvp_path = plans_directory / "MVP.md"
    mvp_plan = get_text_from_filepath(mvp_path)
    if not mvp_plan:
        system, prompt = get_prompt_and_system(
            "project_manager",
            "mvp",
            business_plan=business_plan,
            backlog_csv=backlog,
        )
        logger.info("Generating minimum viable product plan...")
        mvp_plan = Claude().send_prompt(prompt, system_prompt=system)
        with open(mvp_path, "w", encoding="utf-8") as file:
            file.write(mvp_plan)

    # ARCHITECT
    # mvp_path = Path(plans_directory / "MVP.md").expanduser()

    # START Diagrams
    diagrams_path = Path(plans_directory / "ArchitectureDiagrams.md")

    # If diagrams response already exists, read it, otherwise send to Claude
    if diagrams_path.exists():
        logger.debug(f"Diagrams already exists at {diagrams_path}")
        print_fancy("Loading existing diagrams...", style="yellow")

        with open(diagrams_path, "r", encoding="utf-8") as file:
            diagrams_response = file.read()
    else:
        with open(mvp_path, "r", encoding="utf-8") as file:
            mvp_content = file.read()

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

        with open(diagrams_path, "w", encoding="utf-8") as file:
            file.write(diagrams_response)
        logger.info(f"Architecture diagrams saved to {diagrams_path}")

    save_code_from_md(
        markdown=diagrams_response, 
        language="mermaid", 
        output_dir=Path(plans_directory)
    )

    logger.info("Generated mermaid diagrams for documentation.")

    setup_mermaid_docs(project_directory)
    serve_docs(project_directory)
    # END Diagrams

    # START Skeleton
    skeleton_md_path = Path(plans_directory / "Architecture.md")

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
        skeleton_response = architect.send_prompt(
            prompt, system_prompt=system_prompt, maximize=True
        )

        # Save raw response
        with open(skeleton_md_path, "w", encoding="utf-8") as file:
            file.write(skeleton_response)

    save_code_from_md(markdown=skeleton_response, 
                      language="swift", 
                      output_dir=project_directory / "ios_skeleton"
                      )

    
        
    # with open(
    #     Path(plans_directory / "ArchitectureDiagrams.md"), "r", encoding="utf-8"
    # ) as f:
    #     diagrams_content = f.read()

    # import glob
    # from collections import defaultdict
    
    # layers = ["Models", "Services", "ViewModels", "Views"]
    
    # for layer in layers:
    #     matching_files = glob.glob(str(project_directory / "**" / "*.swift"), recursive=True)
    #     grouped_files = defaultdict(list)

    #     for file_path in matching_files:
    #         path_parts = Path(file_path).parts
    #         for dir_name in layers:
    #             if dir_name in path_parts:
    #                 grouped_files[dir_name].append(file_path)
    #                 break

    #     logger.info(f"Developing {layer} files...")
    #     system, prompt = get_prompt_and_system(
    #         "developer",
    #         "engineer",
    #         layer=layer,
    #         diagrams_content=diagrams_content,
    #         file_content=grouped_files[layer],
    #     )
        
    #     develop_layers(prompt, system, project_directory)

    # logger.info("Fixing build errors...")
    # # output_dir = str(Path(config.directories.projects).expanduser() / project_name)
    
    # iteration = 0
    # while True:
    #     print(f"\n--- Build Attempt {iteration + 1} ---\n")
    #     errors = build_xcode_project(project_directory)
    #     # Filter to actual errors (not warnings or messages)
    #     actual_errors = [e for e in errors if e.type == "error"]

    #     if not actual_errors:
    #         print("✅ Build succeeded with no errors.")
    #         break

    #     fix(project_directory, actual_errors)
    #     iteration += 1

if __name__ == "__main__":
    main()