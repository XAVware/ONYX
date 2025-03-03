from anthropic import Anthropic
from dotenv import load_dotenv
from ProjectAnalyzer import ProjectAnalyzer
import logging
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import AppPlanningWorkflow
import argparse
from ResultProcessor import ResultProcessor
from pathlib import Path
from Claude import Claude
from rich.table import Table
from mermaid import setup_mermaid_docs, serve_docs
from FileDevOrchestrator import FileDevOrchestrator
from ClaudeRateLimiter import RateLimiter, ApiErrorHandler
import re
from build import build_xcode_project, fix_build_errors

def create_architecture_diagrams(mvp_plan, project_name):
    """Generate class diagrams, ERD, and architecture explanation based on MVP plan."""
    console = Console()
    console.print("[bold blue]Creating Architecture Diagrams...[/bold blue]")
    
    # Check if architecture diagrams already exist
    diagrams_path = Path(mvp_plan).parent / "ArchitectureDiagrams.md"
    if diagrams_path.exists():
        console.print(f"[yellow]Architecture Diagrams already exist at [/yellow][cyan]{diagrams_path}[/cyan]")
        console.print("[yellow]Loading existing Architecture Diagrams...[/yellow]")
        with open(diagrams_path, "r", encoding="utf-8") as file:
            diagrams_response = file.read()
        
        # Process existing diagrams for documentation
        result_processor = ResultProcessor()
        saved_diagrams = result_processor.process_architecture_diagrams(diagrams_response, Path(mvp_plan).parent.parent)
        
        console.print(Panel(
            Markdown(diagrams_response),
            title="Architecture Diagrams",
            border_style="green"
        ))
        
        return diagrams_path
    
    system_prompt = """
    You are an expert iOS App Architect specializing in Swift 6 and MVVM architecture.
    Based on the provided MVP plan, create architecture diagrams and explanations:

    1. Create a class diagram using Mermaid syntax showing:
       - Major classes and their relationships
       - Key properties and methods
       - MVVM pattern implementation

    2. Create an Entity Relationship Diagram (ERD) using Mermaid syntax showing:
       - Data entities and their attributes
       - Relationships between entities
       - Cardinality of relationships

    3. Provide a detailed verbal explanation of:
       - How components interact with each other
       - Data flow through the application
       - Key architectural decisions and their rationale
       - How the MVVM pattern is implemented

    DO NOT provide any Swift code implementation. Focus only on diagrams and explanations.
    
    Format your response in Markdown with clear sections:
    
    # Architecture Diagrams for [Project Name]
    
    ## Class Diagram
    ```mermaid
    classDiagram
        [Your class diagram here]
    ```
    
    ## Entity Relationship Diagram
    ```mermaid
    erDiagram
        [Your ERD here]
    ```
    
    ## Architecture Explanation
    [Your detailed explanation here]
    """
    
    with open(mvp_plan, "r", encoding="utf-8") as file:
        mvp_content = file.read()
    
    prompt = f"""
    Create architecture diagrams and explanations for an iOS app named "{project_name}" based on this MVP plan:
    
    {mvp_content}
    """
    
    architect = Claude()
    diagrams_response = architect.send_prompt(prompt, system_prompt=system_prompt)

    # Save diagrams document
    with open(diagrams_path, "w", encoding="utf-8") as file:
        file.write(diagrams_response)
    
    # Process mermaid diagrams
    result_processor = ResultProcessor()
    saved_diagrams = result_processor.process_architecture_diagrams(diagrams_response, Path(mvp_plan).parent.parent)
    
    console.print(f"[green]Generated {len(saved_diagrams)} mermaid diagrams for documentation[/green]")
    
    console.print(Panel(
        Markdown(diagrams_response),
        title="Architecture Diagrams",
        border_style="green"
    ))
    
    return diagrams_path

def architect_design(mvp_plan, diagrams_path, project_name):
    """Generate system architecture and class diagram based on MVP plan and architecture diagrams."""
    console = Console()
    console.print("[bold blue]Creating System Architecture...[/bold blue]")
    
    # Check if architecture already exists
    architecture_path = Path(mvp_plan).parent / "Architecture.md"
    if architecture_path.exists():
        console.print(f"[yellow]Architecture already exists at [/yellow][cyan]{architecture_path}[/cyan]")
        console.print("[yellow]Loading existing Architecture...[/yellow]")
        with open(architecture_path, "r", encoding="utf-8") as file:
            architecture_response = file.read()
        
        console.print(Panel(
            Markdown(architecture_response),
            title="Architecture",
            border_style="green"
        ))
        
        return architecture_path
    
    system_prompt = """
    You are an expert iOS App Architect specializing in Swift 6 and MVVM architecture.
    Based on the provided MVP plan and architecture diagrams, design a skeleton architecture for an iOS app. Please provide:

    1. File/directory structure
    2. Service boundaries and communication patterns
    3. Core class definitions with relationships
    4. Function signatures without implementation
    5. Data flow diagrams if applicable

    The architecture should fully adhere to the class diagrams and ERD provided, implementing all classes, relationships, 
    and data models as specified in the diagrams. Follow the architectural explanation to ensure proper component 
    interaction and MVVM pattern implementation.

    Do not include implementation details or line-by-line code. Focus only on the high-level architecture and relationships between components. 
    Do not go beyond the scope of the MVP plan.
    
    Format your response in Markdown with a clear structure that makes it easy to extract file names and content. For each Swift file:
    1. Include the subdirectory (Views, Services, ViewModels, etc.) and filename as a level 2 heading (##)
    2. Immediately follow with the Swift code in a code block

    <ResponseFormat>
    ## Subdirectory/FileName.swift
    ```swift
    // Swift code here
    ```

    ## Subdirectory/AnotherFile.swift
    ```swift
    // More Swift code here
    ```
    </ResponseFormat>
    
    Files will be generated from your response and a team of engineers will develop the final functionality based on your skeleton.
    """
    
    with open(mvp_plan, "r", encoding="utf-8") as file:
        mvp_content = file.read()
    
    with open(diagrams_path, "r", encoding="utf-8") as file:
        diagrams_content = file.read()
    
    example = """
    <EXAMPLE>
    /// Short description of the function
    func fooBar(parameters) -> return value { 
        // Step 1: do something
        // Step 2: do something else
        ...
    }
    </EXAMPLE>
    """
    prompt = f"""
    Design the architecture for an iOS app named {project_name} based on this MVP plan and architecture diagrams:
    
    # MVP PLAN
    {mvp_content}
    
    # ARCHITECTURE DIAGRAMS AND EXPLANATION
    {diagrams_content}
    
    Follow the class diagrams, ERD, and architectural explanation to create Swift file skeletons. Your team of engineers will iterate through the skeleton and develop each swift file, so make sure it includes any relevant context. Any functions that you do not fully write should be outlined like this:
    {example}
    """
    
    architect = Claude()
    architecture_response = architect.send_prompt(prompt, system_prompt=system_prompt, maximize=True)
    
    # Save architecture document
    with open(architecture_path, "w", encoding="utf-8") as file:
        file.write(architecture_response)
    
    console.print(Panel(
        Markdown(architecture_response),
        title="Architecture",
        border_style="green"
    ))
    
    return architecture_path

# Update the develop_project_files function in main.py
def develop_project_files(project_dir, architecture_path, mvp_path, diagrams_path):
    """Develop all Swift files in the project using the ProjectAnalyzer approach"""
    console = Console()
    console.print("[bold blue]Starting Project-based File Development...[/bold blue]")
    
    # Create and run the ProjectAnalyzer instead of FileDevOrchestrator
    analyzer = ProjectAnalyzer(
        project_dir=project_dir,
        architecture_path=architecture_path,
        mvp_path=mvp_path,
        diagrams_path=diagrams_path
    )
    
    result = analyzer.run()
    
    # Show development statistics
    table = Table(title="Project Development Results")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="green")
    
    if result["success"]:
        table.add_row("Files Implemented", str(result["files_implemented"]))
        table.add_row("Files Saved", str(result["files_saved"]))
        console.print(table)
    else:
        console.print(f"[bold red]Project development failed: {result['error']}[/bold red]")
    
    return result

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="ONYX")
    parser.add_argument("app_idea", nargs="?", help="App idea to develop (e.g., 'An app to track my fitness')")
    parser.add_argument("--project-name", "-n", help="Name for the project")
    parser.add_argument("--project-dir", "-d", help="Project directory (default: Projects/[ProjectName])")
    parser.add_argument("--root-dir", "-r", help="Root directory for projects")
    return parser.parse_args()

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger("appplanner")
    console = Console()

    # Parse command-line arguments
    args = parse_arguments()
    
    # Get app idea
    app_idea = args.app_idea
    if not app_idea:
        console.print("[bold yellow]Please provide an app idea.[/bold yellow]")
        app_idea = input("Enter your app idea: ")
    
    # Get project name
    if args.project_name:
        project_name = args.project_name
    else:
        # Extract a reasonable project name from the app idea
        words = app_idea.split()
        if len(words) <= 3:
            # Use the whole idea if it's short
            project_name = ''.join(word.capitalize() for word in words)
        else:
            # Use first 3 words if the idea is long
            project_name = ''.join(word.capitalize() for word in words[:3])
        
        # Remove non-alphanumeric characters
        project_name = ''.join(c for c in project_name if c.isalnum())
        
        # Confirm with user
        console.print(f"[yellow]Suggested project name: [/yellow][bold cyan]{project_name}[/bold cyan]")
        user_input = input("Use this name? (Press Enter to accept, or type a different name): ")
        if user_input.strip():
            project_name = user_input.strip()
    
    # Set up project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        if args.root_dir:
            root_dir = Path(args.root_dir)
        else:
            # Default to user's Documents folder
            import os
            home_dir = os.path.expanduser("~")
            root_dir = Path(f"{home_dir}/ONYX/Projects")
        
        project_dir = root_dir / project_name
    
    # Create project directory if it doesn't exist
    project_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Project directory: [/green][cyan]{project_dir}[/cyan]")
     
    # Run workflow
    workflow = AppPlanningWorkflow.AppPlanningWorkflow(project_dir)
    result = workflow.run_workflow(app_idea)

    mvp_path = result["mvp_plan"]

    if result["success"]:
        console.print("[bold green]Workflow completed successfully![/bold green]")
        console.print("Now generating architecture and implementation...")
        
        # Step 1: Architect creates system diagrams
        diagrams_path = create_architecture_diagrams(mvp_path, project_name)
        console.print(f"[green]Architecture diagrams saved to [/green][cyan]{diagrams_path}[/cyan]")
        setup_mermaid_docs(project_dir)
        serve_docs(project_dir)

        # Step 2: Architect develops skeleton (using diagrams and MVP as reference)
        architecture_path = architect_design(mvp_path, diagrams_path, project_name)
        console.print(f"[green]Architecture saved to [/green][cyan]{architecture_path}[/cyan]")

        # Step 3: Parse and save swift files to project
        architecture_response_path = Path(architecture_path)

        with open(architecture_response_path, "r") as file:
            response_content = file.read()

        result_processor = ResultProcessor()

        markdown_files = result_processor.extract_markdown_files(response_content)

        if markdown_files:
            output_dir = Path(f"{project_dir}/{project_name}")
            saved_paths = result_processor.save_swift_files(markdown_files, output_dir)
            # Create a table to display files
            file_table = Table(title="Generated Files")
            file_table.add_column("Filename", style="cyan")
            file_table.add_column("Path", style="green")
            
            for path in saved_paths:
                file_table.add_row(path.name, str(path.relative_to(project_dir)))

            console.print(file_table)
            
            # Launch development with the new ProjectAnalyzer approach
            console.print("[bold blue]Starting project-based development phase...[/bold blue]")
            development_result = develop_project_files(
                project_dir=project_dir,
                architecture_path=architecture_path,
                mvp_path=mvp_path,
                diagrams_path=diagrams_path
            )
            
            # Build the project after development
            if development_result["success"] and development_result["files_saved"] > 0:
                console.print("[bold blue]Development completed. Building project...[/bold blue]")
                
                # Build the project
                build_result = build_xcode_project(project_dir)
                
                # If build failed, try to fix errors
                if build_result and build_result.result != "SUCCESS":
                    console.print("[bold blue]Attempting to fix build errors...[/bold blue]")
                    
                    # Try up to 3 iterations of fixes and rebuilds
                    for iteration in range(3):
                        console.print(f"[bold]Fix iteration {iteration + 1}/3[/bold]")
                        
                        # Fix errors
                        fixed = fix_build_errors(project_dir, build_result)
                        
                        if not fixed:
                            console.print("[yellow]No more fixable errors[/yellow]")
                            break
                        
                        # Rebuild
                        console.print("[bold blue]Rebuilding project after fixes...[/bold blue]")
                        build_result = build_xcode_project(project_dir)
                        
                        # If build succeeds, we're done
                        if build_result and build_result.result == "SUCCESS":
                            console.print("[bold green]Build successful after fixes![/bold green]")
                            break
                    
                    # Final build status
                    if build_result and build_result.result == "SUCCESS":
                        console.print("[bold green]Final build successful![/bold green]")
                    else:
                        console.print("[bold red]Could not resolve all build errors[/bold red]")
            else:
                console.print("[yellow]No files were developed. Skipping build.[/yellow]")

        else:
            print("No Swift code found in the response.")
    else:
        console.print(f"[bold red]Workflow failed: {result['error']}[/bold red]")

if __name__ == "__main__":
    main()