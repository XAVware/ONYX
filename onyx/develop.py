#!/usr/bin/env python3

import argparse
import glob
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Add the parent directory to the path so we can import onyx modules
script_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(script_dir))

# Import onyx modules after path setup
from onyx.ai_task import Claude  # noqa: E402
from onyx.prompt_loader import get_prompt_and_system  # noqa: E402
from onyx.save_code_from_md import save_code_from_md  # noqa: E402
from onyx.xcode import build  # noqa: E402
from onyx.fix import fix  # noqa: E402
from onyx import get_logger, print_fancy, config  # noqa: E402

logger = get_logger(__name__)

def parse_arguments():
    """Parse command-line arguments for development script."""
    parser = argparse.ArgumentParser(description="ONYX Development - Generate Swift code from architecture")
    parser.add_argument("project_name", help="Name of the project to develop")
    parser.add_argument("--project-dir", "-d", help="Project directory (default: Projects/[ProjectName])")
    parser.add_argument("--layers", "-l", nargs="+", 
                       default=["Models", "Services", "ViewModels", "Views"],
                       help="Layers to develop (default: Models Services ViewModels Views)")
    parser.add_argument("--skip-build", action="store_true", 
                       help="Skip the build and fix cycle")
    return parser.parse_args()

def get_text_from_filepath(path: Path) -> str:
    """Read text content from a file path."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    return ""

def develop_layers(prompt, sys_prompt, project_dir: Path):
    """Send development prompt to Claude and save the generated code."""
    engineer = Claude()
    response = engineer.send_prompt(prompt, system_prompt=sys_prompt, maximize=True)
    save_code_from_md(markdown=response, language="swift", output_dir=project_dir / "ios_source")

def main():
    """Main function to run the development process."""
    args = parse_arguments()
    
    project_name = args.project_name
    
    # Set up project directory
    if args.project_dir:
        project_directory = Path(args.project_dir)
    else:
        project_directory = Path(config.directories.projects).expanduser() / project_name
    
    if not project_directory.exists():
        print_fancy(f"Project directory not found: {project_directory}", "red", panel=True)
        return
    
    plans_directory = project_directory / "plans"
    
    # Check if required files exist
    diagrams_path = plans_directory / "ArchitectureDiagrams.md"
    if not diagrams_path.exists():
        print_fancy(f"Architecture diagrams not found: {diagrams_path}", "red", panel=True)
        print_fancy("Please run the main planning workflow first.", "yellow")
        return
    
    # Read architecture diagrams
    with open(diagrams_path, "r", encoding="utf-8") as f:
        diagrams_content = f.read()
    
    logger.info("Starting development process...")
    
    # Development layers
    layers = args.layers
    
    for layer in layers:
        logger.info(f"Developing {layer} files...")
        
        # Find existing files for this layer
        matching_files = glob.glob(str(project_directory / "**" / "*.swift"), recursive=True)
        grouped_files = defaultdict(list)

        for file_path in matching_files:
            path_parts = Path(file_path).parts
            for dir_name in layers:
                if dir_name in path_parts:
                    grouped_files[dir_name].append(file_path)
                    break

        # Get development prompts
        system_prompt, prompt = get_prompt_and_system(
            "developer",
            "engineer",
            layer=layer,
            diagrams_content=diagrams_content,
            file_content=grouped_files[layer],
        )
        
        # Develop the layer
        develop_layers(prompt, system_prompt, project_directory)
        
        print_fancy(f"Completed {layer} development", "green")
    
    # Build and fix cycle (if not skipped)
    if not args.skip_build:
        logger.info("Starting build and fix cycle...")
        
        iteration = 0
        max_iterations = 10  # Prevent infinite loops
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Build Attempt {iteration} ---\n")
            
            try:
                messages = build(project_directory)
                # Filter to actual errors (not warnings or messages)
                actual_errors = [e for e in messages if e.type == "error"]

                if not actual_errors:
                    print_fancy("✅ Build succeeded with no errors.", "green", panel=True)
                    break

                print_fancy(f"Found {len(actual_errors)} errors. Attempting to fix...", "yellow")
                fix(project_directory, actual_errors)
                
            except Exception as e:
                logger.error(f"Build attempt {iteration} failed: {e}")
                if iteration >= max_iterations:
                    print_fancy("❌ Maximum build attempts reached. Manual intervention required.", "red", panel=True)
                    break
        
        if iteration >= max_iterations:
            print_fancy("Development completed but build issues remain.", "yellow", panel=True)
        else:
            print_fancy("Development completed successfully!", "green", panel=True)
    else:
        print_fancy("Development completed (build skipped)", "green", panel=True)

if __name__ == "__main__":
    main()