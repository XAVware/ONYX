from pathlib import Path
import time
from typing import List, Optional, Dict, Any
import re
import logging
import json
import os

logger = logging.getLogger("swiftai")

class ResultProcessor:
    """Processes Claude responses and extracts code and diagrams."""
    
    def extract_swift_code(self, markdown_content: str) -> List[str]:
        """Extract Swift code blocks from markdown."""
        pattern = r'```swift\s*(.*?)```'
        matches = re.findall(pattern, markdown_content, re.DOTALL)
        
        # Clean up the matches
        return [code.strip() for code in matches]
    
    def extract_json_files(self, response: str) -> Dict[str, str]:
        """Extract file content from JSON response."""
        # Try to find JSON in the response
        json_pattern = r'```json\s*(.*?)```|^\s*(\{.*\})\s*$'
        matches = re.findall(json_pattern, response, re.DOTALL | re.MULTILINE)
        
        files = {}
        for json_match in matches:
            # Use whichever group matched (either inside code block or raw JSON)
            json_str = next(filter(None, json_match), "")
            if not json_str:
                continue
                
            try:
                # Parse JSON content
                data = json.loads(json_str)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    # List of file objects
                    for file_obj in data:
                        if "fileName" in file_obj and "content" in file_obj:
                            files[file_obj["fileName"]] = file_obj["content"]
                elif isinstance(data, dict):
                    # Check if it's a single file object
                    if "fileName" in data and "content" in data:
                        files[data["fileName"]] = data["content"]
                    else:
                        # Dictionary of filename -> content
                        for filename, content in data.items():
                            if isinstance(content, str):
                                files[filename] = content
                            elif isinstance(content, dict) and "content" in content:
                                files[filename] = content["content"]
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
        
        return files
    
    def extract_markdown_files(self, markdown_content: str) -> Dict[str, str]:
        """Extract file content from markdown with filename headers."""
        # Split the content by level 2 headers (##)
        sections = re.split(r'(?m)^##\s+', markdown_content)
        
        files = {}
        
        # Debug output
        logger.info(f"Found {len(sections)} markdown sections")
        
        # Process each section (skip the first if it doesn't have a filename)
        for section in sections[1:] if not sections[0].strip() else sections:
            # Extract the filename and content
            lines = section.split('\n', 1)
            if len(lines) < 2:
                continue
                
            filename = lines[0].strip()
            content = lines[1].strip()
            
            # Ensure filename has .swift extension
            if not filename.lower().endswith('.swift'):
                filename += '.swift'
            
            # Extract Swift code blocks
            swift_blocks = self.extract_swift_code(content)
            if swift_blocks:
                files[filename] = swift_blocks[0]
                logger.info(f"Extracted Swift file: {filename}")
            else:
                logger.warning(f"No Swift code blocks found in section for {filename}")
        
        return files
    
    def extract_mermaid_diagrams(self, markdown_content: str) -> Dict[str, str]:
        """Extract mermaid diagrams from markdown."""
        # Match ```mermaid ... ``` patterns
        pattern = r'```mermaid\s*(.*?)```'
        matches = re.findall(pattern, markdown_content, re.DOTALL)
        
        diagrams = {}
        
        # Debug output
        logger.info(f"Found {len(matches)} mermaid diagrams")
        
        # Get all section headers in the document
        header_positions = []
        
        for i, match in enumerate(re.finditer(r'(?:^|\n)(#+)\s+([^\n]+)(?:\n|$)', markdown_content)):
            level = len(match.group(1))  # Number of # characters
            text = match.group(2).strip()
            position = match.start()
            header_positions.append((position, level, text))
        
        # Find diagram positions
        diagram_positions = []
        for i, match in enumerate(re.finditer(r'```mermaid\s*(.*?)```', markdown_content, re.DOTALL)):
            start_pos = match.start()
            diagram_content = match.group(1).strip()
            diagram_positions.append((start_pos, i, diagram_content))
        
        # Process each diagram
        for i, (start_pos, diagram_index, diagram) in enumerate(diagram_positions):
            # Determine diagram type based on content
            diagram_type = "diagram"
            if 'classDiagram' in diagram:
                diagram_type = "class"
            elif 'erDiagram' in diagram:
                diagram_type = "er"
            elif 'sequenceDiagram' in diagram:
                diagram_type = "sequence"
            elif 'flowchart' in diagram:
                diagram_type = "flow"
            
            # Find the closest header before this diagram
            header_text = f"diagram_{diagram_index+1}"
            closest_header_pos = -1
            for pos, level, text in header_positions:
                if pos < start_pos and pos > closest_header_pos:
                    closest_header_pos = pos
                    header_text = text
            
            # Clean up header text for filename
            header_text = header_text.lower()
            header_text = re.sub(r'[^\w\s-]', '', header_text)  # Remove special chars
            header_text = re.sub(r'\s+', '_', header_text)      # Replace spaces with underscore
            
            # Create filename
            filename = f"{diagram_type}_{header_text}.mmd"
            
            # Add to diagrams dict
            diagrams[filename] = diagram
            logger.info(f"Extracted mermaid diagram: {filename}")
        
        return diagrams
    
    def save_swift_file(self, content: str, filename: Optional[str] = None, 
                      base_dir: Optional[Path] = None) -> Path:
        """Save content as a Swift file."""
        base_dir = base_dir or Path.cwd()
        
        if not filename:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"claude-generated-{timestamp}.swift"
        
        # Ensure the filename has .swift extension
        if not filename.endswith('.swift'):
            filename += '.swift'
        
        output_path = base_dir / filename
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Saved Swift file to {output_path}")
        return output_path
    
    def save_swift_files(self, files: Dict[str, str], base_dir: Optional[Path] = None) -> List[Path]:
        """Save multiple Swift files from extracted JSON."""
        base_dir = base_dir or Path.cwd()
        saved_paths = []
        
        for filename, content in files.items():
            # Create directories if needed
            file_path = base_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            logger.info(f"Saved file to {file_path}")
            saved_paths.append(file_path)
        
        return saved_paths
    
    def save_mermaid_diagrams(self, diagrams: Dict[str, str], base_dir: Optional[Path] = None) -> List[Path]:
        """Save mermaid diagrams to files."""
        base_dir = base_dir or Path.cwd()
        saved_paths = []
        
        for filename, content in diagrams.items():
            # Create directories if needed
            file_path = base_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            logger.info(f"Saved mermaid diagram to {file_path}")
            saved_paths.append(file_path)
        
        return saved_paths
        
    def save_raw_response(self, content: str, base_dir: Optional[Path] = None) -> Path:
        """Save the raw response from Claude to a file."""
        base_dir = base_dir or Path.cwd()
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"claude-raw-response-{timestamp}.md"
        
        output_path = base_dir / filename
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Saved raw Claude response to {output_path}")
        return output_path
    
    def process_architecture_diagrams(self, response_content: str, project_dir: Path) -> List[Path]:
        """Process and save architecture diagrams from Claude's response."""
        # Create diagrams directory if it doesn't exist
        diagrams_dir = project_dir / "planning" / "diagrams"
        diagrams_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract mermaid diagrams
        diagrams = self.extract_mermaid_diagrams(response_content)
        
        # Save diagrams
        saved_paths = self.save_mermaid_diagrams(diagrams, diagrams_dir)
        
        # Generate mkdocs files
        if saved_paths:
            self._generate_mkdocs_files(project_dir, diagrams_dir, saved_paths)
        
        return saved_paths
    
    def _generate_mkdocs_files(self, project_dir: Path, diagrams_dir: Path, diagram_paths: List[Path]) -> None:
        """Generate mkdocs files for diagrams."""
        # Create index.md
        index_content = """# Architecture Diagrams

This section contains the architecture diagrams for the project.

"""
        
        # Create docs directory if it doesn't exist
        docs_dir = project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy diagrams to docs/diagrams
        docs_diagrams_dir = docs_dir / "diagrams"
        docs_diagrams_dir.mkdir(parents=True, exist_ok=True)
        
        # Group diagrams by type
        diagram_types = {}
        for path in diagram_paths:
            filename = path.name
            diagram_type = filename.split('_')[0]
            
            if diagram_type not in diagram_types:
                diagram_types[diagram_type] = []
                
            diagram_types[diagram_type].append(path)
        
        # Add links to each diagram type page in index
        for diagram_type, paths in diagram_types.items():
            type_name = diagram_type.capitalize() + " Diagrams"
            index_content += f"- [{type_name}](diagrams/{diagram_type}.md)\n"
            
            # Create type-specific page
            type_content = f"# {type_name}\n\n"
            
            for path in paths:
                # Format diagram name for display
                name = path.stem.split('_', 1)[1].replace('_', ' ').title()
                
                type_content += f"## {name}\n\n"
                # Use the mermaid wrapper syntax that's better supported
                type_content += "```mermaid\n"
                with open(path, 'r') as f:
                    diagram_content = f.read().strip()
                    # Ensure diagram content starts with a diagram type declaration
                    if not any(diagram_content.startswith(t) for t in ["classDiagram", "erDiagram", "sequenceDiagram", "flowchart", "graph"]):
                        # Add the appropriate diagram type if missing
                        if "class" in path.name:
                            diagram_content = "classDiagram\n" + diagram_content
                        elif "er" in path.name:
                            diagram_content = "erDiagram\n" + diagram_content
                        elif "sequence" in path.name:
                            diagram_content = "sequenceDiagram\n" + diagram_content
                        elif "flow" in path.name:
                            diagram_content = "flowchart TD\n" + diagram_content
                    type_content += diagram_content
                type_content += "\n```\n\n"
                
                # Copy diagram to docs
                target_path = docs_diagrams_dir / path.name
                with open(path, 'r') as src, open(target_path, 'w') as dst:
                    dst.write(src.read())
            
            # Write type-specific page
            type_path = docs_diagrams_dir / f"{diagram_type}.md"
            with open(type_path, 'w') as f:
                f.write(type_content)
        
        # Write index file
        index_path = docs_dir / "index.md"
        with open(index_path, 'w') as f:
            f.write(index_content)
        
        # Create mkdocs.yml
        mkdocs_content = """site_name: Project Documentation
site_description: Documentation with Architecture Diagrams

theme:
  name: material
  features:
    - navigation.instant
    - navigation.tracking
    - content.code.annotate

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: fence_code_format

extra_javascript:
  - https://unpkg.com/mermaid/dist/mermaid.min.js

plugins:
  - search

nav:
  - Home: index.md
  - Diagrams:"""
        
        # Add diagram type pages to navigation
        for diagram_type in diagram_types:
            type_name = diagram_type.capitalize() + " Diagrams"
            mkdocs_content += f"\n    - {type_name}: diagrams/{diagram_type}.md"
        
        # Write mkdocs.yml
        mkdocs_path = project_dir / "mkdocs.yml"
        with open(mkdocs_path, 'w') as f:
            f.write(mkdocs_content)
        
        logger.info(f"Generated mkdocs files at {docs_dir}")
        logger.info(f"Created mkdocs.yml at {mkdocs_path}")