# from pathlib import Path
# from typing import Dict
# import logging
# from rich.console import Console

# logger = logging.getLogger("swiftai")
# console = Console()
# MAX_CONTEXT_SIZE = 15000  # Characters limit for context

# class DirectoryScanner:
#     """Scans directories for context."""
    
#     def __init__(self):
#         self.text_extensions = {
#             '.swift', '.py', '.js', '.md', '.txt', '.json', 
#             '.yaml', '.yml', '.html', '.css', '.h', '.m'
#         }
#         self.ignore_patterns = [
#             '.git', '.DS_Store', '__pycache__', 
#             'build/', 'node_modules/', 'venv/'
#         ]
    
#     def should_include_file(self, file_path: Path) -> bool:
#         """Check if a file should be included in context."""
#         # Check file extension
#         if file_path.suffix.lower() not in self.text_extensions:
#             return False
        
#         # Check ignore patterns
#         path_str = str(file_path)
#         for pattern in self.ignore_patterns:
#             if pattern in path_str:
#                 return False
        
#         # Check file size (avoid very large files)
#         try:
#             if file_path.stat().st_size > 100_000:  # 100kb
#                 logger.info(f"Skipping large file: {file_path}")
#                 return False
#         except:
#             return False
        
#         return True
    
#     def gather_context(self, directory: Path, max_files: int = 10) -> Dict[str, str]:
#         """Gather context from files in the directory."""
#         context = {}
#         file_count = 0
#         total_size = 0
        
#         console.print(f"[bold blue]Gathering context from [/bold blue][cyan]{directory}[/cyan]")
        
#         # First get all eligible files
#         all_files = [
#             f for f in directory.rglob('*') 
#             if f.is_file() and self.should_include_file(f)
#         ]
        
#         # Sort by modification time (newest first) and size (smallest first)
#         sorted_files = sorted(
#             all_files, 
#             key=lambda f: (-f.stat().st_mtime, f.stat().st_size)
#         )
        
#         # Process files
#         for file_path in sorted_files:
#             if file_count >= max_files or total_size >= MAX_CONTEXT_SIZE:
#                 break
                
#             try:
#                 content = file_path.read_text()
#                 rel_path = file_path.relative_to(directory)
#                 context[str(rel_path)] = content
#                 file_count += 1
#                 total_size += len(content)
#             except Exception as e:
#                 logger.warning(f"Could not read {file_path}: {e}")
        
#         console.print(f"[green]Gathered context from {file_count} files ({total_size} characters)")
#         return context