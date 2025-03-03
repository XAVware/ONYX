"""
ProjectAnalyzer.py - Analyzes and develops an entire project at once using Claude
"""

import logging
from pathlib import Path
import os
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import json
import re
import time

from Claude import Claude

logger = logging.getLogger("projectanalyzer")
console = Console()

class ProjectAnalyzer:
    """Analyzes and develops an entire project at once using Claude."""
    
    def __init__(self, 
                 project_dir: Path,
                 architecture_path: Path,
                 mvp_path: Path,
                 diagrams_path: Optional[Path] = None):
        """Initialize the project analyzer."""
        self.project_dir = project_dir
        self.architecture_path = architecture_path
        self.mvp_path = mvp_path
        self.diagrams_path = diagrams_path
        self.console = Console()
        
        # Create prompts directory for logging
        self.prompts_dir = project_dir / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # Directory for Swift files
        self.output_dir = Path(f"{self.project_dir}/{self.project_dir.name}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load architecture and MVP docs
        with open(self.architecture_path, 'r', encoding='utf-8') as f:
            self.architecture_doc = f.read()
            
        with open(self.mvp_path, 'r', encoding='utf-8') as f:
            self.mvp_doc = f.read()
            
        if self.diagrams_path and self.diagrams_path.exists():
            with open(self.diagrams_path, 'r', encoding='utf-8') as f:
                self.diagrams_doc = f.read()
        else:
            self.diagrams_doc = ""
    
    def collect_all_files(self) -> Dict[str, str]:
        """Collect all Swift files in the project directory."""
        files = {}
        
        # Collect existing Swift files from output directory
        for file_path in self.output_dir.glob("**/*.swift"):
            # Skip files in build directories
            if "build" in str(file_path):
                continue
                
            # Get relative path for readability
            rel_path = file_path.relative_to(self.project_dir)
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                files[str(rel_path)] = content
            except Exception as e:
                self.console.print(f"[yellow]Error reading file {file_path}: {str(e)}[/yellow]")
        
        self.console.print(f"[green]Collected {len(files)} Swift files for analysis[/green]")
        return files
        
    def create_project_prompt(self, files: Dict[str, str]) -> str:
        """Create a comprehensive prompt for the entire project."""
        # Start with project overview
        prompt = f"""
# Project Development Request

I need your help analyzing and developing a Swift iOS project. I'll provide:
1. The project's MVP requirements
2. Architecture documents and diagrams
3. Existing Swift files (some may be skeleton files that need implementation)

## Your Task
Please analyze all files and implement or improve each Swift file to make the project functional.
For each file, ensure you:
1. Implement all TODOs and missing functionality
2. Follow Swift best practices and MVVM architecture
3. Add proper error handling and documentation
4. Ensure compatibility with other files in the project

## Project MVP Requirements
{self.mvp_doc}

## Architecture Documentation
{self.architecture_doc}
"""

        # Add diagram documentation if available
        if self.diagrams_doc:
            prompt += f"\n## Architecture Diagrams\n{self.diagrams_doc}\n"
        
        # Add file listing with content
        prompt += "\n## Project Files\n\n"
        
        # Organize files by directory for better readability
        organized_files = {}
        for filepath, content in files.items():
            directory = str(Path(filepath).parent)
            if directory not in organized_files:
                organized_files[directory] = {}
            organized_files[directory][Path(filepath).name] = content
        
        # Add each file with its content
        for directory, dir_files in organized_files.items():
            prompt += f"### Directory: {directory}\n\n"
            for filename, content in dir_files.items():
                prompt += f"#### {filename}\n```swift\n{content}\n```\n\n"
        
        # Add specific instructions for response format
        prompt += """
## Response Format
Please provide your implementation for each file in a clearly formatted response:

```swift
// Filename: path/to/File.swift
// Your implementation here
```

Format each file separately and clearly indicate the filename before each implementation.
"""
        return prompt
    
    def develop_entire_project(self) -> Dict[str, str]:
        """Develop the entire project at once using Claude."""
        self.console.print("[bold blue]Starting Project Development with Claude[/bold blue]")
        
        # Collect all Swift files
        files = self.collect_all_files()
        
        # Create comprehensive project prompt
        prompt = self.create_project_prompt(files)
        
        # Create system prompt with explicit formatting instructions
        system_prompt = """You are an expert iOS developer specializing in Swift and MVVM architecture.
Your task is to analyze an entire iOS project and implement or improve all Swift files.

Guidelines:
1. Study the architecture documentation and diagrams carefully
2. Examine relationships between files to ensure consistency
3. Implement all TODOs and missing functionality in each file
4. Follow Swift best practices and MVVM architecture patterns
5. Add proper error handling, documentation, and unit testable code

IMPORTANT - RESPONSE FORMAT:
For each file you implement, follow this exact format:

```
// Filename: path/to/File.swift
```swift
// Your Swift implementation here
```

Make sure there's a clear filename header before each implementation.
Provide the complete implementation for each file, not just the changes.
"""
        
        # Save the prompt
        self.save_prompt(prompt, system_prompt, "full_project")
        
        # Send to Claude
        self.console.print("[bold]Sending project to Claude for analysis and development...[/bold]")
        claude = Claude()
        
        try:
            # Try with a larger context first
            self.console.print("[bold]Attempting with maximize=True (larger context)...[/bold]")
            response = claude.send_prompt(prompt, context=None, system_prompt=system_prompt, maximize=True)
            
            # Process response to extract file implementations
            implemented_files = self.extract_file_implementations(response)
            
            # If no files extracted, we might need to try with smaller chunks
            if not implemented_files:
                self.console.print("[yellow]No files extracted. The project might be too large.[/yellow]")
                self.console.print("[yellow]Consider splitting the project into smaller components or files.[/yellow]")
                
                # As a fallback, analyze just a subset of files
                self.console.print("[bold]Attempting to develop individual files...[/bold]")
                implemented_files = self.develop_files_individually(files)
                
            return implemented_files
            
        except Exception as e:
            self.console.print(f"[bold red]Error during Claude API call: {str(e)}[/bold red]")
            # Try a fallback approach
            self.console.print("[yellow]Attempting fallback approach with individual files...[/yellow]")
            implemented_files = self.develop_files_individually(files)
            return implemented_files
    
    def develop_files_individually(self, files: Dict[str, str]) -> Dict[str, str]:
        """Develop files individually as a fallback."""
        implemented_files = {}
        
        # Sort files by potential dependency (Views last, Models first)
        sorted_files = sorted(files.items(), key=lambda x: (
            "View" in x[0],  # Views last
            "ViewModel" in x[0],  # ViewModels second-to-last
            "Service" not in x[0],  # Services earlier
            "Model" not in x[0]  # Models first
        ))
        
        # Process up to 5 files at a time as a compromise
        for i in range(0, len(sorted_files), 5):
            batch = dict(sorted_files[i:i+5])
            
            self.console.print(f"[bold]Processing batch of {len(batch)} files...[/bold]")
            
            # Create a focused prompt for just these files
            focused_prompt = f"""
# Focused Development Request

I need your help implementing these specific Swift files for my iOS project.

## Your Task
Implement or complete each of the following Swift files based on the architecture guidelines.

## Architecture Overview (Brief)
{self.architecture_doc[:2000]}... (abbreviated)

## Files to Implement
"""
            
            # Add each file with its content
            for filepath, content in batch.items():
                focused_prompt += f"\n### {filepath}\n```swift\n{content}\n```\n\n"
            
            # Add specific instructions for response format
            focused_prompt += """
## Response Format
Please provide your implementation for each file using this format:

// Filename: path/to/File.swift
```swift
// Your implementation here
```

Format each file separately with a clear filename header.
"""
            
            system_prompt = """You are an expert Swift developer. 
Implement the provided Swift files with complete functionality.
For each file, use the format:

// Filename: filename.swift
```swift
// Your implementation
```
"""
            
            # Save the prompt
            batch_num = i // 5 + 1
            self.save_prompt(focused_prompt, system_prompt, f"batch_{batch_num}")
            
            # Send to Claude
            claude = Claude()
            response = claude.send_prompt(focused_prompt, system_prompt=system_prompt)
            
            # Extract implementations
            batch_implementations = self.extract_file_implementations(response)
            implemented_files.update(batch_implementations)
            
            # Small delay between batches
            time.sleep(2)
        
        return implemented_files
    
    def save_raw_response(self, response: str) -> Path:
        """Save Claude's raw response for debugging purposes."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        debug_dir = self.project_dir / "debug"
        debug_dir.mkdir(exist_ok=True)
        
        debug_file = debug_dir / f"claude_response_{timestamp}.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response)
            
        self.console.print(f"[yellow]Saved raw Claude response to {debug_file} for debugging[/yellow]")
        return debug_file
        
    def save_prompt(self, prompt: str, system_prompt: str, prompt_type: str) -> Path:
        """Save a prompt to a file for logging purposes."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        prompt_file = self.prompts_dir / f"{prompt_type}_{timestamp}.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(f"===== SYSTEM PROMPT =====\n\n{system_prompt}\n\n")
            f.write(f"===== USER PROMPT =====\n\n{prompt}\n")
            
        self.console.print(f"[blue]Saved {prompt_type} prompt to {prompt_file}[/blue]")
        return prompt_file
    
    def extract_file_implementations(self, response: str) -> Dict[str, str]:
        """Extract file implementations from Claude's response."""
        implemented_files = {}
        
        # Save raw response for debugging
        debug_file = self.save_raw_response(response)
        
        # First check if we got a good response with code blocks
        if "```swift" not in response:
            self.console.print("[red]No Swift code blocks found in Claude's response[/red]")
            self.console.print(f"[yellow]Check {debug_file} for the full response[/yellow]")
            return implemented_files
            
        # Try multiple patterns to extract files
        
        # Pattern 1: Look for explicit filename headers and swift blocks
        pattern1 = r'(?:```swift\s*\n*// Filename:\s*([^\n]+)|// Filename:\s*([^\n]+)|####\s+([^\n]+\.swift))\s*\n(```swift\s*\n)?(.*?)(?:```|(?=// Filename:)|(?=####\s+[\w/]+\.swift)|$)'
        
        # Pattern 2: Look for markdown headers with .swift extension followed by code blocks
        pattern2 = r'#+\s+([^#\n]+\.swift)\s*\n+```swift\s*\n(.*?)```'
        
        # Pattern 3: More permissive - look for any swift code block preceded by text that might be a filename
        pattern3 = r'(?:\n|^)([^#\n]+\.swift)\s*\n+```swift\s*\n(.*?)```'
        
        # Pattern 4: Just look for Swift file class declarations in code blocks
        pattern4 = r'```swift\s*\n(.*?class\s+(\w+).*?|.*?struct\s+(\w+).*?|.*?enum\s+(\w+).*?)```'
        
        # Try each pattern in order
        for i, pattern in enumerate([pattern1, pattern2, pattern3, pattern4], 1):
            self.console.print(f"[blue]Trying extraction pattern {i}...[/blue]")
            matches = list(re.finditer(pattern, response, re.DOTALL))
            
            if matches:
                self.console.print(f"[green]Found {len(matches)} potential matches with pattern {i}[/green]")
                
                for match in matches:
                    # Handle different pattern structures
                    if i == 1:  # Using pattern1
                        # Get the filename (could be in group 1, 2 or 3)
                        filename = next(filter(None, match.groups()[0:3]), "")
                        filename = filename.strip()
                        
                        # Get the code content
                        code_content = match.group(5)
                        
                    elif i == 2 or i == 3:  # Using pattern2 or pattern3
                        filename = match.group(1).strip()
                        code_content = match.group(2)
                        
                    elif i == 4:  # Using pattern4
                        # Extract class/struct/enum name for filename
                        code_content = match.group(1)
                        
                        # Try to find the name in groups 2-4
                        type_name = next(filter(None, match.groups()[1:4]), "Unknown")
                        filename = f"{type_name}.swift"
                        
                        self.console.print(f"[yellow]Generated filename from type: {filename}[/yellow]")
                    
                    # Clean up the code content
                    if code_content:
                        code_content = code_content.strip()
                        # Remove trailing ``` if it exists
                        if code_content.endswith("```"):
                            code_content = code_content[:-3].strip()
                            
                    if filename and code_content:
                        # Ensure filename has .swift extension
                        if not filename.endswith('.swift'):
                            filename += '.swift'
                            
                        implemented_files[filename] = code_content
                        self.console.print(f"[green]Extracted implementation for {filename}[/green]")
                
                # If we found any implementations with this pattern, no need to try others
                if implemented_files:
                    break
        
        # If we still couldn't extract any files, try one last approach: split by Swift headers
        if not implemented_files:
            self.console.print("[yellow]Attempting last-resort extraction method...[/yellow]")
            # Look for lines that might define a Swift file like "import" statements followed by type declarations
            swift_blocks = re.findall(r'```swift\s*\n(.*?)```', response, re.DOTALL)
            
            for i, block in enumerate(swift_blocks):
                # Check if this looks like a complete Swift file
                if "import " in block and re.search(r'(class|struct|enum)\s+\w+', block):
                    # Try to determine filename from class/type name
                    type_match = re.search(r'(class|struct|enum)\s+(\w+)', block)
                    if type_match:
                        type_name = type_match.group(2)
                        filename = f"{type_name}.swift"
                        implemented_files[filename] = block.strip()
                        self.console.print(f"[green]Created {filename} from block {i+1}[/green]")
                    else:
                        # Fallback: generic filename
                        filename = f"SwiftFile_{i+1}.swift"
                        implemented_files[filename] = block.strip()
                        self.console.print(f"[yellow]Created generic {filename} from block {i+1}[/yellow]")
        
        self.console.print(f"[green]Extracted {len(implemented_files)} file implementations from Claude's response[/green]")
        
        # If we couldn't extract any files, print additional debug info
        if not implemented_files:
            self.console.print("[red]Failed to extract any file implementations[/red]")
            self.console.print("[yellow]Check for Swift code blocks in the response:[/yellow]")
            swift_blocks = re.findall(r'```swift\s*\n(.*?)```', response, re.DOTALL)
            self.console.print(f"[yellow]Found {len(swift_blocks)} Swift code blocks[/yellow]")
            
        return implemented_files
    
    def save_implemented_files(self, implemented_files: Dict[str, str]) -> List[Path]:
        """Save implemented files to the project directory."""
        saved_paths = []
        
        for filename, content in implemented_files.items():
            # Try to find the file in the project directory
            file_matches = list(self.output_dir.glob(f"**/{filename}"))
            
            if file_matches:
                # File exists, update it
                file_path = file_matches[0]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_paths.append(file_path)
                self.console.print(f"[green]Updated file: {file_path.relative_to(self.project_dir)}[/green]")
            else:
                # New file, determine where to save it
                # Check if the filename has a directory structure
                if "/" in filename:
                    file_path = self.output_dir / filename
                else:
                    # Try to guess directory based on file type
                    if "View" in filename:
                        file_path = self.output_dir / "Views" / filename
                    elif "ViewModel" in filename:
                        file_path = self.output_dir / "ViewModels" / filename
                    elif "Model" in filename:
                        file_path = self.output_dir / "Models" / filename
                    elif "Service" in filename or "Manager" in filename:
                        file_path = self.output_dir / "Services" / filename
                    else:
                        file_path = self.output_dir / filename
                
                # Create directory if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_paths.append(file_path)
                self.console.print(f"[green]Created new file: {file_path.relative_to(self.project_dir)}[/green]")
        
        return saved_paths
    
    def run(self) -> Dict:
        """Run the project analyzer to develop the entire project."""
        try:
            # Develop the entire project
            implemented_files = self.develop_entire_project()
            
            # Save the implemented files
            saved_paths = self.save_implemented_files(implemented_files)
            
            return {
                "success": True,
                "files_implemented": len(implemented_files),
                "files_saved": len(saved_paths)
            }
            
        except Exception as e:
            self.console.print(f"[bold red]Error during project analysis: {str(e)}[/bold red]")
            return {
                "success": False,
                "error": str(e)
            }