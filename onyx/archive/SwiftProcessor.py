# from pathlib import Path
# import subprocess
# from typing import Tuple
# import logging
# from rich.console import Console

# logger = logging.getLogger("swiftai")
# console = Console()

# class SwiftProcessor:
#     """Processes Swift files: building, and reporting errors."""
    
#     def __init__(self):
#         self.xcode_version = self._get_xcode_version()
    
#     def _get_xcode_version(self) -> str:
#         """Get the current Xcode version."""
#         try:
#             result = subprocess.run(
#                 ["xcodebuild", "-version"],
#                 capture_output=True,
#                 text=True,
#                 check=True
#             )
#             return result.stdout.strip().split('\n')[0]
#         except Exception as e:
#             logger.warning(f"Could not determine Xcode version: {e}")
#             return "Unknown"
    
#     def build_swift_file(self, file_path: Path) -> Tuple[bool, str]:
#         """Build a single Swift file."""
#         try:
#             with console.status(f"Building {file_path.name}..."):
#                 result = subprocess.run(
#                     ["swiftc", "-o", str(file_path.with_suffix("")), str(file_path)],
#                     capture_output=True,
#                     text=True
#                 )
            
#             if result.returncode != 0:
#                 logger.error(f"Build failed: {result.stderr}")
#                 return False, result.stderr
            
#             logger.info(f"Built {file_path.name} successfully")
#             return True, result.stdout
#         except Exception as e:
#             logger.error(f"Exception during build: {str(e)}")
#             return False, str(e)
    
#     def run_swift_file(self, file_path: Path) -> Tuple[bool, str]:
#         """Run a Swift executable."""
#         executable_path = file_path.with_suffix("")
#         if not executable_path.exists():
#             success, output = self.build_swift_file(file_path)
#             if not success:
#                 return success, output
        
#         try:
#             with console.status(f"Running {executable_path.name}..."):
#                 result = subprocess.run(
#                     [str(executable_path)],
#                     capture_output=True,
#                     text=True,
#                     timeout=30  # Timeout after 30 seconds
#                 )
            
#             if result.returncode != 0:
#                 logger.error(f"Execution failed: {result.stderr}")
#                 return False, result.stderr
            
#             logger.info(f"Execution successful")
#             return True, result.stdout
#         except subprocess.TimeoutExpired:
#             logger.error(f"Execution timed out")
#             return False, "Execution timed out after 30 seconds"
#         except Exception as e:
#             logger.error(f"Exception during execution: {str(e)}")
#             return False, str(e)
