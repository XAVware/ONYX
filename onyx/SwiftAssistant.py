"""
SwiftAssistant.py - Specialized assistant for Swift development
"""

import logging
from Claude import Claude
from pathlib import Path
import re
import os

logger = logging.getLogger("swiftai")

class SwiftAssistant:
    """Specialized assistant for Swift development tasks."""
    
    def __init__(self):
        """Initialize the Swift assistant."""
        self.claude = Claude()
    
    def develop_file(self, file_path, architecture_doc, mvp_doc, related_files=None):
        """Develop a Swift file based on skeleton."""
        # Read the file skeleton
        with open(file_path, 'r', encoding='utf-8') as f:
            skeleton = f.read()
        
        # Create system prompt
        system_prompt = self._create_system_prompt(file_path)
        
        # Gather context - related files
        context = {}
        if related_files:
            for related_file in related_files:
                if os.path.exists(related_file):
                    with open(related_file, 'r', encoding='utf-8') as f:
                        context[os.path.basename(related_file)] = f.read()
        
        # Create development prompt
        prompt = self._create_development_prompt(file_path, skeleton, architecture_doc, mvp_doc)
        
        # Send prompt to Claude
        response = self.claude.send_prompt(prompt, context=None, system_prompt=system_prompt)
        
        # Extract and validate Swift code
        swift_code = self._extract_swift_code(response)
        
        return swift_code
    
    def _create_system_prompt(self, file_path):
        """Create system prompt based on file type."""
        file_name = os.path.basename(file_path)
        
        base_prompt = """You are SwiftAssistant, an expert Swift developer specializing in iOS app development.
Your task is to implement the provided Swift file with full functionality based on the architecture design.

Follow these guidelines:
1. Implement all properties, methods, and functionality described in the class skeleton.
2. Use modern Swift features (Swift 6+).
3. Follow iOS development best practices.
4. Include thorough documentation.
5. Ensure MVVM architecture alignment.
6. Handle errors properly.
7. Ensure thread safety.
8. Use dependency injection.
9. Write testable code.

Return ONLY the complete Swift implementation without additional explanation."""
        
        # Add file type specific guidance
        if "View" in file_name:
            base_prompt += "\n\nFocus on clean SwiftUI implementation with proper state management."
        elif "Model" in file_name:
            base_prompt += "\n\nEnsure models are immutable when appropriate and use Codable."
        elif "Service" in file_name:
            base_prompt += "\n\nImplement proper async/await patterns and error handling."
            
        return base_prompt
    
    def _create_development_prompt(self, file_path, skeleton, architecture_doc, mvp_doc):
        """Create detailed development prompt."""
        file_name = os.path.basename(file_path)
        
        # Extract relevant sections from architecture and MVP docs
        arch_excerpt = self._extract_relevant_section(architecture_doc, file_name)
        mvp_excerpt = self._extract_relevant_section(mvp_doc, file_name)
        
        prompt = f"""Implement the following Swift file:

File: {file_name}

Current skeleton:
```swift
{skeleton}
```

Relevant architecture information:
{arch_excerpt}

Relevant MVP requirements:
{mvp_excerpt}

Provide complete implementation with all functionality. Use proper error handling, comments, and Swift best practices.

Return ONLY the Swift file implementation without markdown or explanations."""
        
        return prompt
    
    def _extract_relevant_section(self, doc_path, file_name):
        """Extract relevant sections from a document."""
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract file name without extension
            base_name = os.path.splitext(file_name)[0]
            
            # Look for sections mentioning this file or its components
            components = re.findall(r'[A-Z][a-z]+', base_name)
            
            relevant_sections = []
            patterns = [
                rf'##\s+[^#\n]*{re.escape(base_name)}[^#\n]*\n.*?(?=\n##|\Z)',  # Section with filename
                rf'#{1,3}\s+[^#\n]*{re.escape(base_name)}[^#\n]*\n.*?(?=\n#{1,3}|\Z)'  # Heading with filename
            ]
            
            for component in components + [base_name]:
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
                    for match in matches:
                        if match not in relevant_sections:
                            relevant_sections.append(match)
            
            if relevant_sections:
                return "\n\n".join(relevant_sections)
            else:
                return "No specific information found in architecture document."
                
        except Exception as e:
            logger.error(f"Error extracting relevant section: {str(e)}")
            return "Error extracting relevant information."
    
    def _extract_swift_code(self, response):
        """Extract Swift code from Claude's response."""
        # Look for Swift code blocks
        swift_pattern = r'```swift\s*(.*?)```'
        matches = re.findall(swift_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Fallback: look for any code block
        code_pattern = r'```\s*(.*?)```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Last resort: return everything if it looks like Swift
        if "import " in response and ("class " in response or "struct " in response):
            return response.strip()
        
        return response
    
    def improve_file(self, file_path, error_message=None):
        """Improve a Swift file that has errors or issues."""
        with open(file_path, 'r', encoding='utf-8') as f:
            current_code = f.read()
        
        prompt = f"""Improve the following Swift file:

```swift
{current_code}
```
"""

        if error_message:
            prompt += f"\nThe file has the following issue:\n{error_message}\n\nPlease fix the issue and improve the overall quality."
        else:
            prompt += "\nPlease improve code quality, comments, error handling, and overall implementation."
        
        system_prompt = """You are an expert Swift developer. Fix and improve the provided Swift file.
Return ONLY the improved Swift code without explanation or markdown formatting."""
        
        response = self.claude.send_prompt(prompt, system_prompt=system_prompt)
        improved_code = self._extract_swift_code(response)
        
        return improved_code