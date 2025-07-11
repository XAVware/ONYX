#!/usr/bin/env python3
"""
ONYX CLI - A command-line tool for using ONYX from any directory.
This script allows you to select prompts, models, and files to include,
then sends the request to the selected model and saves the response.
"""

import argparse
import os
import sys
import yaml
import glob
from pathlib import Path
import datetime
from typing import List, Optional, Dict, Any, Union
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint
from rich.syntax import Syntax
from rich.table import Table

# Add the parent directory to the path so we can import onyx modules
script_dir = Path(__file__).resolve().parent
sys.path.append(str(script_dir))

# Import onyx modules
from onyx.ai_task import Claude
from onyx.prompt_loader import load_prompt, PROMPTS_DIR
from onyx.save_code_from_md import save_code_from_md

# Initialize rich console
console = Console()

def print_fancy(message, style=None, highlight=False, panel=False, title=None):
    """Print a fancy message using Rich styling."""
    if panel:
        panel_obj = Panel(message, title=title, style=style or "")
        console.print(panel_obj)
    else:
        console.print(message, style=style, highlight=highlight)

def list_available_prompts():
    """List all available prompts from the prompts directory."""
    prompts = {}
    # Get all subdirectories in the prompts directory
    for persona_dir in PROMPTS_DIR.iterdir():
        if persona_dir.is_dir():
            persona = persona_dir.name
            persona_prompts = []
            
            # Get all YAML files in the persona directory
            for prompt_file in persona_dir.glob("*.yaml"):
                prompt_name = prompt_file.stem
                try:
                    # Load the prompt to get its description
                    prompt_data = load_prompt(persona, prompt_name)
                    description = prompt_data.get("description", "No description available")
                    persona_prompts.append((prompt_name, description))
                except Exception as e:
                    print_fancy(f"Error loading prompt {prompt_name}: {str(e)}", style="red")
            
            if persona_prompts:
                prompts[persona] = persona_prompts
    
    return prompts

def select_prompt():
    """Interactively select a prompt."""
    prompts = list_available_prompts()
    
    # Display available personas
    table = Table(title="Available Prompt Categories")
    table.add_column("Number", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Prompts", style="yellow")
    
    for i, (persona, prompt_list) in enumerate(prompts.items(), 1):
        table.add_row(str(i), persona, f"{len(prompt_list)} prompts")
    
    console.print(table)
    
    # Select a persona
    choice = Prompt.ask("Select a category number", choices=[str(i) for i in range(1, len(prompts) + 1)])
    selected_persona = list(prompts.keys())[int(choice) - 1]
    
    # Display prompts for the selected persona
    prompt_table = Table(title=f"Prompts in {selected_persona}")
    prompt_table.add_column("Number", style="cyan")
    prompt_table.add_column("Prompt", style="green")
    prompt_table.add_column("Description", style="yellow")
    
    prompt_list = prompts[selected_persona]
    for i, (prompt_name, description) in enumerate(prompt_list, 1):
        prompt_table.add_row(str(i), prompt_name, description)
    
    console.print(prompt_table)
    
    # Select a prompt
    prompt_choice = Prompt.ask("Select a prompt number", choices=[str(i) for i in range(1, len(prompt_list) + 1)])
    selected_prompt = prompt_list[int(prompt_choice) - 1][0]
    
    # Allow user to type a custom prompt
    use_custom = Confirm.ask("Would you like to type a custom prompt instead?")
    if use_custom:
        custom_prompt_text = console.input("Enter your custom prompt:\n")
        return selected_persona, selected_prompt, custom_prompt_text
    
    return selected_persona, selected_prompt, None

def select_model():
    """Select the model to use (Claude or OpenAI)."""
    table = Table(title="Available Models")
    table.add_column("Number", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Description", style="yellow")
    
    models = [
        ("claude", "Claude-3.7-Sonnet", "Anthropic's Claude 3.7 Sonnet model"),
        ("openai", "GPT-4o", "OpenAI's GPT-4o model")
    ]
    
    for i, (model_id, model_name, description) in enumerate(models, 1):
        table.add_row(str(i), model_name, description)
    
    console.print(table)
    
    choice = Prompt.ask("Select a model", choices=["1", "2"])
    return models[int(choice) - 1][0]

def select_files():
    """Interactively select files to include in the prompt."""
    selected_files = []
    working_dir = Path.cwd()
    
    while True:
        # Show currently selected files
        if selected_files:
            print_fancy("Currently selected files:", style="bold")
            for file in selected_files:
                print_fancy(f"  - {file}", style="green")
        
        # Options for file selection
        print_fancy("\nFile selection options:", style="bold")
        print_fancy("1. Add file by path", style="cyan")
        print_fancy("2. Add files by pattern (glob)", style="cyan") 
        print_fancy("3. Finish selection", style="cyan")
        
        choice = Prompt.ask("Choose an option", choices=["1", "2", "3"])
        
        if choice == "1":
            # Add a single file
            file_path = Prompt.ask("Enter file path (relative to current directory)")
            full_path = working_dir / file_path
            if full_path.exists() and full_path.is_file():
                selected_files.append(str(full_path))
                print_fancy(f"Added: {full_path}", style="green")
            else:
                print_fancy(f"File not found: {file_path}", style="red")
        
        elif choice == "2":
            # Add files by pattern
            pattern = Prompt.ask("Enter glob pattern (e.g., *.py or src/**/*.js)")
            matching_files = glob.glob(pattern, recursive=True)
            
            if matching_files:
                # Show matching files with numbers
                table = Table(title=f"Matching Files for '{pattern}'")
                table.add_column("Number", style="cyan")
                table.add_column("File", style="green")
                
                for i, file in enumerate(matching_files, 1):
                    table.add_row(str(i), file)
                
                console.print(table)
                
                # Ask if user wants to add all or select specific ones
                add_all = Confirm.ask("Add all matching files?")
                if add_all:
                    for file in matching_files:
                        full_path = Path(working_dir / file).resolve()
                        selected_files.append(str(full_path))
                    print_fancy(f"Added {len(matching_files)} files", style="green")
                else:
                    # Let user select specific files
                    selections = Prompt.ask(
                        "Enter file numbers to add (comma-separated, e.g., 1,3,5)",
                        default="1"
                    )
                    for num in selections.split(","):
                        try:
                            idx = int(num.strip()) - 1
                            if 0 <= idx < len(matching_files):
                                full_path = Path(working_dir / matching_files[idx]).resolve()
                                selected_files.append(str(full_path))
                                print_fancy(f"Added: {matching_files[idx]}", style="green")
                        except ValueError:
                            pass
            else:
                print_fancy(f"No files matched pattern: {pattern}", style="yellow")
        
        elif choice == "3":
            # Finished selecting files
            break
    
    return selected_files

def read_file_contents(file_paths: List[str]) -> Dict[str, str]:
    """Read contents of selected files."""
    file_contents = {}
    for file_path in file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_contents[file_path] = f.read()
        except Exception as e:
            print_fancy(f"Error reading {file_path}: {str(e)}", style="red")
    return file_contents

def send_to_claude(prompt: str, system_prompt: str = "") -> str:
    """Send a prompt to Claude API and return the response."""
    claude = Claude()
    return claude.send_prompt(prompt, system_prompt=system_prompt)

def send_to_openai(prompt: str, system_prompt: str = "") -> str:
    """Send a prompt to OpenAI API and return the response."""
    print_fancy("OpenAI integration is not yet implemented", style="yellow")
    return "OpenAI integration is not yet implemented"

def save_response(response: str, directory: str = "assistant_responses"):
    """Save the model response as a markdown file."""
    # Create the assistant_responses directory if it doesn't exist
    response_dir = Path.cwd() / directory
    response_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a filename with the current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"response_{timestamp}.md"
    filepath = response_dir / filename
    
    # Save the response
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response)
    
    print_fancy(f"Response saved to {filepath}", style="green")
    return filepath

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="ONYX CLI - Run from any directory")
    parser.add_argument("--no-interactive", action="store_true", help="Run in non-interactive mode")
    args = parser.parse_args()
    
    # Print welcome message
    print_fancy("Welcome to ONYX CLI", style="bold magenta", panel=True, title="ONYX")
    
    # Select prompt
    persona, prompt_name, custom_prompt = select_prompt()
    
    # Get the prompt and system prompt
    if custom_prompt:
        system_prompt = ""
        prompt_text = custom_prompt
    else:
        try:
            prompt_data = load_prompt(persona, prompt_name)
            system_prompt = prompt_data.get("system_prompt", "")
            prompt_template = prompt_data.get("prompt_template", "")
            prompt_text = prompt_template
        except Exception as e:
            print_fancy(f"Error loading prompt: {str(e)}", style="red")
            return
    
    # Select model
    model = select_model()
    
    # Select files
    selected_files = select_files()
    
    # Read file contents
    file_contents = read_file_contents(selected_files)
    
    # Prepare the prompt with file contents
    if not custom_prompt:
        try:
            # Create a dictionary of file_content variables
            file_content_str = "\n\n".join([f"## {path}\n```\n{content}\n```" for path, content in file_contents.items()])
            prompt_text = prompt_template.format(file_content=file_content_str)
        except KeyError:
            # If the prompt template doesn't use file_content, append it
            file_content_str = "\n\n".join([f"## {path}\n```\n{content}\n```" for path, content in file_contents.items()])
            prompt_text += f"\n\nHere are the files you requested:\n\n{file_content_str}"
    
    # Show a preview of the prompt
    print_fancy("Prompt Preview:", style="bold")
    syntax = Syntax(prompt_text[:500] + "..." if len(prompt_text) > 500 else prompt_text, "markdown", theme="monokai")
    console.print(syntax)
    
    # Confirm before sending
    if not Confirm.ask("Send this prompt to the model?"):
        print_fancy("Operation cancelled", style="yellow")
        return
    
    # Send to selected model
    print_fancy(f"Sending prompt to {model.upper()}...", style="cyan")
    if model == "claude":
        response = send_to_claude(prompt_text, system_prompt)
    else:
        response = send_to_openai(prompt_text, system_prompt)
    
    # Print a preview of the response
    print_fancy("Response Preview:", style="bold")
    syntax = Syntax(response[:500] + "..." if len(response) > 500 else response, "markdown", theme="monokai")
    console.print(syntax)
    
    # Save the response
    filepath = save_response(response)
    
    # Ask if user wants to extract and save code blocks
    if Confirm.ask("Extract and save code blocks from the response?"):
        output_dir = Path.cwd() / "extracted_code"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        language = Prompt.ask("Enter language to extract (e.g., python, javascript, swift)", default="python")
        save_code_from_md(response, language, output_dir)
        print_fancy(f"Code blocks saved to {output_dir}", style="green")

if __name__ == "__main__":
    main()