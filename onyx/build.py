"""
Build and debug utility for Xcode projects - can be run independently of the development process.
"""

from rich.console import Console
from pathlib import Path
from XcodeBuilder import XcodeBuilder
from Claude import Claude
import re
import os
import argparse
import sys

console = Console()

def build_xcode_project(project_dir):
    """Build the Xcode project and return any errors."""
    console.print("[bold blue]Building Xcode Project...[/bold blue]")
    
    try:
        builder = XcodeBuilder(project_dir)
        console.print(f"Building {builder.project_name}...")
        result = builder.build()
        
        # Display build results
        if result.result == "SUCCESS":
            console.print(f"[bold green]Build successful![/bold green]")
        else:
            console.print(f"[bold red]Build failed with {len([m for m in result.messages if m.type == 'error'])} errors and {len([m for m in result.messages if m.type == 'warning'])} warnings[/bold red]")
            
            # Print errors and warnings
            for msg in result.messages:
                color = "red" if msg.type == "error" else "yellow"
                console.print(f"[{color}]{msg.type.upper()}: {msg.file}:{msg.line} - {msg.message}[/{color}]")
        
        return result
        
    except Exception as e:
        console.print(f"[bold red]Error building project: {str(e)}[/bold red]")
        return None


def fix_build_errors(project_dir, build_result):
    """Fix files with build errors using ChatGPT for analysis and Claude for implementation."""
    if build_result.result == "SUCCESS":
        return True
    
    console.print("[bold blue]Fixing build errors...[/bold blue]")
    
    # Import the ChatGPT class
    try:
        from ChatGPT import ChatGPT
    except ImportError:
        console.print("[yellow]ChatGPT module not found. Make sure to add ChatGPT.py to your project.[/yellow]")
        return False
    
    # Group errors by file
    files_with_errors = {}
    
    for msg in build_result.messages:
        if msg.type == "error":
            if msg.file != "unknown":
                if msg.file not in files_with_errors:
                    files_with_errors[msg.file] = []
                files_with_errors[msg.file].append(msg)
    
    if not files_with_errors:
        console.print("[yellow]No fixable file errors found[/yellow]")
        return False
    
    fixed_files = 0

    
    # STEP 1: Get analysis from ChatGPT
    console.print(f"[bold]STEP 1: Analyzing errors with ChatGPT[/bold]")
    
    # Initialize ChatGPT client
    chatgpt = ChatGPT()
    
    # Format the errors for ChatGPT
    error_descriptions = build_result.messages
    chatgpt_prompt = f"""I have the following Swift errors:

Build errors:
{error_descriptions}

Please analyze these errors and create a list of oversights or improper implementations that may have been made while using parts of the SwiftUI/Swift language.

For example, if you are sent an error related to this line of code:
ProgressView(0.5)

You should respond by reminding the developer that ProgressView should not take any arguments in modern SwiftUI.
"""
            
    chatgpt_system_prompt = """You are an expert Swift developer specializing in iOS development."""
            
    # Send to ChatGPT and get the analysis
    chatgpt_analysis = chatgpt.send_prompt(chatgpt_prompt, chatgpt_system_prompt)
    
    console.print(f"[green]✓ Received error analysis from ChatGPT[/green]")
    


    for file_path, errors in files_with_errors.items():
        try:
            # Try to find the actual file path
            file_obj = Path(file_path)
            # STEP 2: Send to Claude with ChatGPT's analysis as context
            console.print(f"[bold]STEP 2: Sending to Claude with ChatGPT analysis for {file_obj.name}...[/bold]")
            if not file_obj.exists():
                # Try to find the file in the project directory
                potential_matches = list(Path(project_dir).glob(f"**/{file_obj.name}"))
                if potential_matches:
                    file_obj = potential_matches[0]
                else:
                    console.print(f"[yellow]Could not find file: {file_path}[/yellow]")
                    continue
            
            # Read the file content
            with open(file_obj, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            
            # Initialize Claude client
            fixer = Claude()
            
            # Create prompt with errors and ChatGPT's analysis
            claude_prompt = f"""The following Swift file has build errors that need to be fixed:
            
```swift
{file_content}
```
            
Build errors:
{error_descriptions}

ChatGPT's analysis of the errors:
{chatgpt_analysis}

Please provide a fixed version of the file that resolves these errors. Pay special attention to:
1. Using fully qualified type names when needed to resolve ambiguities (e.g., YourModule.TypeName)
2. Adding type aliases when necessary (e.g., typealias LocalUser = Models.User)
3. Using proper namespacing with enums if there are naming conflicts
4. Ensuring consistent naming conventions (Models end with "Model", ViewModels with "ViewModel", etc.)

Return ONLY the corrected Swift code without explanations or commentary.
"""
            
            claude_system_prompt = """You are an expert Swift developer. Fix the build errors in the provided Swift file and return ONLY the corrected code.
            
Pay special attention to handling ambiguous type references by using these techniques:
1. Use fully qualified names (ModuleName.TypeName)
2. Add namespaces (enum Models { struct User {...} })
3. Add type aliases (typealias LocalUser = Models.User)
4. Rename types to be more specific (User → UserModel)

Return only the fixed Swift code with no explanation."""

            # Send to Claude to get the fixed code
            response = fixer.send_prompt(claude_prompt, system_prompt=claude_system_prompt)
            
            # Extract Swift code from response
            swift_code_pattern = r'```swift\s*(.*?)```'
            matches = re.findall(swift_code_pattern, response, re.DOTALL)
            
            if matches:
                fixed_code = matches[0].strip()
            else:
                # Assume the entire response is Swift code if no code block is found
                fixed_code = response.strip()
            
            # Write the fixed code back to the file
            with open(file_obj, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            console.print(f"[green]✓ Fixed file: {file_obj.name}[/green]")
            fixed_files += 1
            
        except Exception as e:
            console.print(f"[red]Error fixing file {file_path}: {str(e)}[/red]")
    
    console.print(f"[green]Fixed {fixed_files}/{len(files_with_errors)} files with errors[/green]")
    return fixed_files > 0

def build_and_fix(project_dir, max_iterations=3):
    """Build the project and attempt to fix any errors."""
    console.print("[bold blue]Building and fixing project...[/bold blue]")
    
    # Build the project
    build_result = build_xcode_project(project_dir)
    
    if not build_result:
        console.print("[bold red]Build failed with critical error[/bold red]")
        return False
    
    # If build succeeded, we're done
    if build_result.result == "SUCCESS":
        console.print("[bold green]Build successful![/bold green]")
        return True
    
    # Try to fix errors
    console.print("[bold blue]Attempting to fix build errors...[/bold blue]")
    
    # Try up to max_iterations of fixes and rebuilds
    for iteration in range(max_iterations):
        console.print(f"[bold]Fix iteration {iteration + 1}/{max_iterations}[/bold]")
        
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
            return True
    
    # Final build status
    if build_result and build_result.result == "SUCCESS":
        console.print("[bold green]Final build successful![/bold green]")
        return True
    else:
        console.print("[bold red]Could not resolve all build errors[/bold red]")
        return False


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Build and debug a Swift project")
    parser.add_argument("project_dir", nargs="?", help="Path to the project directory")
    parser.add_argument("--max-iterations", type=int, default=3, 
                        help="Maximum number of fix iterations (default: 3)")
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()
    
    # If no project directory provided, use current directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path.cwd()
        console.print(f"[yellow]No project directory specified, using current directory: {project_dir}[/yellow]")
    
    # Check if project directory exists
    if not project_dir.exists():
        console.print(f"[bold red]Project directory not found: {project_dir}[/bold red]")
        return
    
    # Check if .xcodeproj exists in the directory
    xcodeproj_files = list(project_dir.glob("*.xcodeproj"))
    if not xcodeproj_files:
        console.print(f"[bold red]No .xcodeproj file found in {project_dir}[/bold red]")
        return
    
    console.print(f"[bold blue]Starting build and debug for project: {project_dir}[/bold blue]")
    
    # Build and fix errors
    success = build_and_fix(project_dir, args.max_iterations)
    
    if success:
        console.print("[bold green]Build and fix process completed successfully![/bold green]")
    else:
        console.print("[bold red]Build and fix process completed with errors.[/bold red]")


if __name__ == "__main__":
    main()
