# #!/usr/bin/env python3
# """
# SwiftAI - Streamlined Claude-to-Swift Workflow

# This script provides a simplified workflow that:
# 1. Gathers context from the current directory
# 2. Sends a request to Claude with directory context
# 3. Extracts Swift code from Claude's response
# 4. Saves the Swift code to the directory
# 5. Builds the code and reports errors
# 6. If there are errors, loops back to Claude for debugging
# """

# import asyncio
# import click
# import logging
# import time
# from pathlib import Path
# from rich.console import Console
# from rich.panel import Panel
# from rich.syntax import Syntax
# from rich.markdown import Markdown
# from rich.prompt import Prompt, Confirm
# from rich.table import Table

# from onyx.archive.Config import Config
# from DirectoryScanner import DirectoryScanner
# from SwiftProcessor import SwiftProcessor
# from onyx.Claude import Claude
# from ResultProcessor import ResultProcessor

# import os
# import yaml
# from pathlib import Path

# # Set up logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger("swiftai")
# console = Console()

# # Initialize config
# app_config = Config()

# @click.group()
# def cli():
#     """SwiftAI - Streamlined Claude-to-Swift Workflow."""
#     pass

# @cli.command()
# @click.option('--api-key', help='Set your Anthropic API key')
# @click.option('--model', help='Set default Claude model')
# def config(api_key, model):
#     """Configure SwiftAI settings."""
#     if api_key:
#         app_config.data['api_key'] = api_key
    
#     if model:
#         app_config.data['default_model'] = model
    
#     app_config.save_config()
#     console.print("[green]Configuration updated successfully![/green]")
    
#     # Display current configuration
#     console.print("\n[bold]Current Configuration:[/bold]")
#     for key, value in app_config.data.items():
#         if key == 'api_key':
#             display_value = value[:4] + '...' if value else 'Not set'
#         else:
#             display_value = value
#         console.print(f"{key}: {display_value}")

# @cli.command()
# @click.option('--prompt', '-p', help='Prompt for Claude')
# @click.option('--directory', '-d', type=click.Path(exists=True),
#               help='Directory to gather context from (defaults to current)')
# @click.option('--max-files', type=int, default=10,
#               help='Maximum number of files to include in context')
# @click.option('--filename', '-f', help='Output filename (defaults to auto-generated)')
# @click.option('--run/--no-run', default=True, help='Run the Swift file after building')
# @click.option('--system-prompt', '-s', help='Custom system prompt for Claude')
# @click.option('--max-iterations', '-m', type=int, default=3,
#               help='Maximum debugging iterations')
# def generate(prompt, directory, max_files, filename, run, system_prompt, max_iterations):
#     """Generate Swift code using Claude."""
#     # Run the async function with asyncio.run
#     asyncio.run(_generate(prompt, directory, max_files, filename, run, system_prompt, max_iterations))

# async def _generate(prompt, directory, max_files, filename, run, system_prompt, max_iterations):
#     """Async implementation of generate command."""
    
#     # Initialize components
#     dir_scanner = DirectoryScanner()
#     # swift_proc = SwiftProcessor()
#     result_proc = ResultProcessor()
    
#     try:
#         claude = Claude()
        
#         # Determine working directory
#         work_dir = Path(directory) if directory else Path.cwd()
        
#         # Gather context
#         context = dir_scanner.gather_context(work_dir, max_files)
        
#         # Get prompt if not provided
#         if not prompt:
#             prompt = Prompt.ask("Enter your Swift code request for Claude")
        
#         # For keeping track of iterations
#         iteration = 0
#         build_success = False
#         swift_file_paths = []
        
#         # Debug loop
#         while not build_success and iteration < max_iterations:
#             console.rule(f"[bold]Iteration {iteration + 1}/{max_iterations}")
            
#             # Send to Claude
#             response = claude.send_prompt(
#                 prompt, context, system_prompt
#             )
            
#             if not response["success"]:
#                 console.print(f"[bold red]Error:[/bold red] {response['error']}")
#                 break
            
#             # Save the raw response to a file
#             raw_response_path = result_proc.save_raw_response(response["response"], work_dir)
#             console.print(f"[blue]Saved raw Claude response to [/blue][cyan]{raw_response_path}[/cyan]")
            
#             # Display response
#             console.print(Panel(
#                 Markdown(response["response"]), 
#                 title="Claude Response", 
#                 border_style="green"
#             ))
            
#             json_files = result_proc.extract_json_files(response["response"])
            
#             if json_files:
#                 # Save all files from JSON
#                 swift_file_paths = result_proc.save_swift_files(json_files, work_dir)
                
#                 # Create a table to display files
#                 file_table = Table(title="Generated Files")
#                 file_table.add_column("Filename", style="cyan")
#                 file_table.add_column("Path", style="green")
                
#                 for path in swift_file_paths:
#                     file_table.add_row(path.name, str(path.relative_to(work_dir)))
                
#                 console.print(file_table)
                
#                 # Use the first Swift file for build/run if no specific filename
#                 primary_swift_file = None
#                 for path in swift_file_paths:
#                     if path.suffix.lower() == '.swift':
#                         primary_swift_file = path
#                         break
                
#                 if primary_swift_file:
#                     console.print(Syntax(primary_swift_file.read_text(), "swift", theme="monokai", line_numbers=True))
                    
#                     # Build the Swift file
#                     build_success, build_output = swift_proc.build_swift_file(primary_swift_file)
#                 else:
#                     console.print("[yellow]No Swift files found in JSON response[/yellow]")
#                     break
#             else:
#                 # Try extracting from markdown format with headers
#                 markdown_files = result_proc.extract_markdown_files(response["response"])
                
#                 if markdown_files:
#                     # Save all files from markdown
#                     swift_file_paths = result_proc.save_swift_files(markdown_files, work_dir)
                    
#                     # Create a table to display files
#                     file_table = Table(title="Generated Files")
#                     file_table.add_column("Filename", style="cyan")
#                     file_table.add_column("Path", style="green")
                    
#                     for path in swift_file_paths:
#                         file_table.add_row(path.name, str(path.relative_to(work_dir)))
                    
#                     console.print(file_table)
                    
#                     # Use the first Swift file for build/run if no specific filename
#                     primary_swift_file = None
#                     for path in swift_file_paths:
#                         if path.suffix.lower() == '.swift':
#                             primary_swift_file = path
#                             break
                    
#                     if primary_swift_file:
#                         console.print(Syntax(primary_swift_file.read_text(), "swift", theme="monokai", line_numbers=True))
                        
#                         # Build the Swift file
#                         build_success, build_output = swift_proc.build_swift_file(primary_swift_file)
#                     else:
#                         console.print("[yellow]No Swift files found in markdown response[/yellow]")
#                         break
#                 else:
#                     # Fall back to traditional code block extraction
#                     swift_code = result_proc.extract_swift_code(response["response"])
            
#             iteration += 1
        
#         if build_success:
#             console.print(f"[bold green]Success after {iteration} iteration(s)![/bold green]")
#         else:
#             console.print(f"[bold red]Failed to build Swift file after {iteration} iteration(s)[/bold red]")
    
#     except Exception as e:
#         logger.error(f"Error in workflow: {str(e)}")
#         console.print_exception()

# if __name__ == '__main__':
#     cli()