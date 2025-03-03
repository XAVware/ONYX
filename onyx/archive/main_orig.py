# """
# Example usage of the enhanced ClaudeClient for Swift development
# """

# import os
# import logging
# from pathlib import Path
# from onyx.Claude import Claude
# from onyx.archive.Config import Config
# from DirectoryScanner import DirectoryScanner
# from SwiftProcessor import SwiftProcessor
# from ResultProcessor import ResultProcessor
# from rich.syntax import Syntax
# from rich.table import Table
# from rich.console import Console


# # Set up logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger("swiftai")
# console = Console()

# swift_markdown_response_format = """
# Format your response in Markdown with a clear structure that makes it easy to extract file names and content. For each Swift file:
# 1. Include the filename as a level 2 heading (##)
# 2. Immediately follow with the Swift code in a code block

# <ResponseFormat>
# ## FileName.swift
# ```swift
# // Swift code here
# ```

# ## AnotherFile.swift
# ```swift
# // More Swift code here
# ```
# </ResponseFormat>
# """

# def main():
        
#     # Create project directory if it doesn't exist
#     project_dir = Path("/Users/ryan/Documents/Documents/XAVware/Projects/Flix")
#     project_dir.mkdir(parents=True, exist_ok=True)

#     system_prompt = f"""
#     You are an expert iOS Engineer who specializes in SwiftUI & Swift development. 

#     {swift_markdown_response_format}

#     Follow Swift 6 and MVVM best practices in your implementations. Always include the files' imports.
#     """

#     prompt = "Create a iOS app in Swift like a Tinder but for streaming movie sites like Netflix or Hulu. Users should have the ability to connect with family members so, on movie nights, they can go on the app, see all the services they subscribe to along with their movies, and swipe left/right on movies based on their likes & dislikes. In the end, all family member votes are compared and the most up-voted movies are displayed."

#     # Initialize components
#     dir_scanner = DirectoryScanner()
#     swift_proc = SwiftProcessor()
#     result_proc = ResultProcessor()
    
#     # try:
#     claude = Claude()
    
#     # Determine working directory
#     work_dir = Path(directory) if directory else Path.cwd()
    
#     # Gather context
#     context = dir_scanner.gather_context(work_dir)
    
#     # Send to Claude
#     response = claude.send_prompt(
#         prompt, context, system_prompt
#     )
    
#     if not response["success"]:
#         console.print(f"[bold red]Error:[/bold red] {response['error']}")
    
#     # Save the raw response to a file
#     raw_response_path = result_proc.save_raw_response(response["response"], work_dir)
#     console.print(f"[blue]Saved raw Claude response to [/blue][cyan]{raw_response_path}[/cyan]")

#     result_proc.save_raw_response(response, base_dir=directory)

#     markdown_files = result_proc.extract_markdown_files(response["response"])
                
#     if markdown_files:
#         # Save all files from markdown
#         swift_file_paths = result_proc.save_swift_files(markdown_files, work_dir)
        
#         # Create a table to display files
#         file_table = Table(title="Generated Files")
#         file_table.add_column("Filename", style="cyan")
#         file_table.add_column("Path", style="green")
        
#         for path in swift_file_paths:
#             file_table.add_row(path.name, str(path.relative_to(work_dir)))
        
#         console.print(file_table)
        
#         # Use the first Swift file for build/run if no specific filename
#         # primary_swift_file = None
#         # for path in swift_file_paths:
#         #     if path.suffix.lower() == '.swift':
#         #         primary_swift_file = path
#         #         break
        
#         # if primary_swift_file:
#         #     console.print(Syntax(primary_swift_file.read_text(), "swift", theme="monokai", line_numbers=True))
            
#         #     # Build the Swift file
#         #     build_success, build_output = swift_proc.build_swift_file(primary_swift_file)
#         # else:
#         #     console.print("[yellow]No Swift files found in markdown response[/yellow]")
#     else:
#         # Fall back to traditional code block extraction
#         swift_code = result_proc.extract_swift_code(response["response"])

#     # Save the response and extract Swift code files
#     # dev_claude.save_response_to_file(response, prefix="initial_response")
#     # swift_files = dev_claude.save_swift_code(response["content"])
    
#     # # # Save the complete chat history
#     # history_path = dev_claude.save_chat_history(format="md")
#     # print(f"Chat history saved to: {history_path}")

# if __name__ == "__main__":
#     main()