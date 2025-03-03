from anthropic import Anthropic
from dotenv import load_dotenv
import uuid
import time
import json
import logging
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import AppPlanningWorkflow
from Claude import Claude
from ResultProcessor import ResultProcessor
from SwiftAssistant import SwiftAssistant
from pathlib import Path
from rich.table import Table
from mermaid import setup_mermaid_docs, serve_docs
from pathlib import Path
import re
import logging
import networkx as nx
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import time
import os
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import threading

import concurrent.futures
import time
import random
class FileDevOrchestrator:
    def __init__(self, project_dir, architecture_path, mvp_path, diagrams_path):
        self.project_dir = project_dir
        self.architecture_path = architecture_path
        self.mvp_path = mvp_path
        self.diagrams_path = diagrams_path
        self.development_queue = []
        self.completed_files = []
        self.dependency_graph = nx.DiGraph()
        self.result_processor = ResultProcessor()
        self.console = Console()
        
        # Initialize the development queue from architecture file
        self._initialize_development_queue()
        
    def _initialize_development_queue(self):
        """Parse the architecture file to find Swift files to develop."""
        with open(self.architecture_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use ResultProcessor to extract files from architecture
        files = self.result_processor.extract_markdown_files(content)
        
        # Create base output directory
        output_dir = Path(f"{self.project_dir}/{self.project_dir.name}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save all files as skeleton files first
        saved_paths = self.result_processor.save_swift_files(files, output_dir)
        
        # Add all files to development queue
        self.development_queue = saved_paths
        
        self.console.print(f"[green]Added {len(saved_paths)} files to development queue[/green]")
        
        # Build dependency graph
        self.build_dependency_graph()
        
    def build_dependency_graph(self):
        """Parse Swift files to find import statements and dependencies."""
        for file_path in self.development_queue:
            # Add the file to the graph
            self.dependency_graph.add_node(file_path)
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for import statements
            import_pattern = r'import\s+([A-Za-z0-9_\.]+)'
            imports = re.findall(import_pattern, content)
            
            # Look for class references
            class_pattern = r'class\s+([A-Za-z0-9_]+)'
            classes_defined = re.findall(class_pattern, content)
            
            # Look for protocol references
            protocol_pattern = r'protocol\s+([A-Za-z0-9_]+)'
            protocols_defined = re.findall(protocol_pattern, content)
            
            # Look for struct references
            struct_pattern = r'struct\s+([A-Za-z0-9_]+)'
            structs_defined = re.findall(struct_pattern, content)
            
            # Look for enum references
            enum_pattern = r'enum\s+([A-Za-z0-9_]+)'
            enums_defined = re.findall(enum_pattern, content)
            
            # Combine all defined types
            defined_types = set(classes_defined + protocols_defined + structs_defined + enums_defined)
            
            # For each file, check if it contains types referenced in this file
            for other_path in self.development_queue:
                if other_path == file_path:
                    continue
                    
                with open(other_path, 'r', encoding='utf-8') as f:
                    other_content = f.read()
                
                # Check if any imported module matches
                if any(module in other_path.name for module in imports):
                    self.dependency_graph.add_edge(file_path, other_path)
                    continue
                
                # Check if any referenced type is defined in the other file
                other_defined_types = set(re.findall(class_pattern, other_content) + 
                                         re.findall(protocol_pattern, other_content) + 
                                         re.findall(struct_pattern, other_content) + 
                                         re.findall(enum_pattern, other_content))
                
                # If any type referenced in this file is defined in the other file, add dependency
                for type_name in defined_types:
                    if type_name in other_content and type_name not in ["class", "struct", "enum", "protocol"]:
                        self.dependency_graph.add_edge(file_path, other_path)
                        break
        
        # Log the dependency graph
        self.console.print(f"[green]Built dependency graph with {self.dependency_graph.number_of_nodes()} nodes and {self.dependency_graph.number_of_edges()} edges[/green]")
    
    def prioritize_development_queue(self):
        """Use topological sort to order files by dependencies."""
        try:
            # Get a topological sort of the dependency graph
            sorted_files = list(nx.topological_sort(self.dependency_graph))
            
            # Update development queue
            self.development_queue = sorted_files
            
            self.console.print(f"[green]Prioritized development queue with {len(sorted_files)} files[/green]")
            return sorted_files
        except nx.NetworkXUnfeasible:
            # There's a cycle in the dependencies
            self.console.print("[yellow]Warning: Cyclic dependencies detected, using degree-based ordering[/yellow]")
            
            # Use in-degree as a heuristic (fewer dependencies first)
            sorted_files = sorted(self.dependency_graph.nodes(), 
                                 key=lambda x: self.dependency_graph.in_degree(x))
            
            # Update development queue
            self.development_queue = sorted_files
            return sorted_files
    
    def get_next_ready_file(self, remaining_files):
        """Get the next file whose dependencies are already completed."""
        for file_path in remaining_files:
            # Get dependencies of this file
            dependencies = list(self.dependency_graph.predecessors(file_path))
            
            # Check if all dependencies are completed
            if all(dep in self.completed_files for dep in dependencies):
                return file_path
        
        # If no file is ready, return the first file (may happen with cycles)
        if remaining_files:
            self.console.print("[yellow]Warning: No file with all dependencies satisfied, selecting first available[/yellow]")
            return remaining_files[0]
            
        return None
    
    def extract_relevant_architecture(self, file_path):
        """Extract relevant sections from architecture document for this file."""
        with open(self.architecture_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get the filename without path
        filename = Path(file_path).name
        
        # Find sections in architecture doc that mention this file
        # First try exact match section
        section_pattern = rf'##\s+[^#\n]*{re.escape(filename)}.*?(?=\n##|\Z)'
        sections = re.findall(section_pattern, content, re.DOTALL)
        
        if not sections:
            # Try finding by class/struct/protocol name
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Extract defined types
            types_pattern = r'(?:class|struct|protocol|enum)\s+([A-Za-z0-9_]+)'
            defined_types = re.findall(types_pattern, file_content)
            
            for type_name in defined_types:
                type_section_pattern = rf'##\s+[^#\n]*{re.escape(type_name)}.*?(?=\n##|\Z)'
                type_sections = re.findall(type_section_pattern, content, re.DOTALL)
                sections.extend(type_sections)
        
        # Return combined sections or the whole architecture if nothing specific found
        if sections:
            return "\n\n".join(sections)
        else:
            # Just return the whole architecture document as fallback
            return content
    
    def extract_relevant_mvp(self, file_path):
        """Extract relevant sections from MVP document for this file."""
        with open(self.mvp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get the filename without path and extension
        base_name = Path(file_path).stem
        
        # Find parts of the MVP that might relate to this file
        # Look for feature names that could match filename
        words = re.findall(r'[A-Z][a-z]+', base_name)
        
        relevant_sections = []
        for word in words:
            # Look for headings or bullet points containing this feature name
            section_pattern = rf'(?:^|\n)(?:#{1,6}|[-*+])\s+[^\n]*{word}.*?(?=\n#|\n[-*+]|\Z)'
            sections = re.findall(section_pattern, content, re.DOTALL | re.MULTILINE)
            relevant_sections.extend(sections)
        
        # Return combined sections or the whole MVP if nothing specific found
        if relevant_sections:
            return "\n\n".join(relevant_sections)
        else:
            return content
    
    def create_system_prompt_for_file(self, file_path):
        """Create a specialized system prompt for developing this file with namespace awareness."""
        # Determine file type from path
        filename = Path(file_path).name
        file_type = "unknown"
        
        if "View" in filename or "Screen" in filename:
            file_type = "view"
        elif "Model" in filename or "ViewModel" in filename:
            file_type = "viewmodel"
        elif "Service" in filename or "Manager" in filename or "Client" in filename:
            file_type = "service"
        elif "Repository" in filename or "Store" in filename:
            file_type = "repository"
        elif "Protocol" in filename or "Interface" in filename:
            file_type = "protocol"
        
        # Base system prompt for Swift development
        base_prompt = """You are an expert iOS developer specializing in Swift development following MVVM architecture patterns.
    Your task is to implement the provided Swift file with full functionality based on the architecture design.

    Follow these guidelines:
    1. Implement all properties, methods, and functionality described in the class skeleton.
    2. Use modern Swift features and idioms (Swift 6+).
    3. Follow iOS development best practices for memory management, error handling, and UI updates.
    4. Include thorough inline documentation using markup comments.
    5. Ensure your implementation aligns with the MVVM architecture.
    6. Implement proper error handling with do/catch blocks where appropriate.
    7. Ensure thread safety where needed, especially for shared resources.
    8. Follow dependency injection patterns for services and repositories.
    9. Implement unit testable code with clear separation of concerns.

    IMPORTANT NAMING CONVENTIONS AND NAMESPACE GUIDELINES:
    1. Always use unique, descriptive type names that reflect both purpose and category.
    2. Follow these consistent naming patterns:
    - Models: Suffix with 'Model' (e.g., UserModel, ProfileModel)
    - ViewModels: Suffix with 'ViewModel' (e.g., UserViewModel, ProfileViewModel)
    - Services: Suffix with 'Service' (e.g., AuthenticationService)
    - Repositories: Suffix with 'Repository' (e.g., UserRepository)
    - Views: Suffix with 'View' (e.g., ProfileView, SettingsView)
    3. When referencing external types, use fully qualified names to avoid ambiguity.
    4. Consider using namespaces for related types:
    ```swift
    enum Models {
        struct UserModel { ... }
        struct ProfileModel { ... }
    }
    ```
    5. When you need to access a type that might have a naming conflict, use module prefix:
    ```swift
    let model = ModuleName.UserModel()
    ```
    6. Use type aliases to simplify usage of namespaced types:
    ```swift
    typealias UserModel = Models.UserModel
    ```

    Your implementation must strictly follow the provided class structure without adding any new public APIs 
    unless absolutely necessary to fulfill the requirements.
    """
        
        # Add file-type specific guidelines
        if file_type == "view":
            base_prompt += """
    For SwiftUI Views:
    - Use @State, @Binding, @ObservedObject, @EnvironmentObject appropriately
    - Ensure view updates are efficient and not over-reactive
    - Break complex views into smaller component views
    - Keep business logic out of views - delegate to ViewModels
    - Use proper view modifiers in the right order for best performance
    - Focus on declarative UI patterns
    - Use unique names for views (ProfileView rather than simply Profile)
    """
        elif file_type == "viewmodel":
            base_prompt += """
    For ViewModels:
    - Implement @Published properties for view state
    - Keep models separate from ViewModels
    - Follow reactive patterns with Combine or async/await
    - Provide clear interfaces for views to interact with
    - Handle all business logic and data transformation
    - Use dependency injection for services
    - Keep ViewModels testable and free of UI logic
    - Always suffix with 'ViewModel' (e.g., ProfileViewModel)
    """
        elif file_type == "service":
            base_prompt += """
    For Services:
    - Implement proper error handling and propagation
    - Make network calls asynchronous using async/await
    - Provide clear interfaces for consumers
    - Handle authentication and authorization properly
    - Cache results where appropriate
    - Use dependency injection for other services
    - Add proper logging for operational visibility
    - Always suffix with 'Service' (e.g., NetworkService)
    """
        elif file_type == "repository":
            base_prompt += """
    For Repositories:
    - Implement proper data persistence strategies
    - Handle CoreData, UserDefaults, or other storage properly
    - Provide clean abstractions for data access
    - Include proper error handling for storage failures
    - Use appropriate concurrency approaches for data access
    - Implement caching strategies where appropriate
    - Always suffix with 'Repository' (e.g., UserRepository)
    """
        
        return base_prompt
    
    def create_development_prompt(self, file_path):
        """Create a prompt for developing a specific file."""
        # Read the file skeleton
        with open(file_path, 'r', encoding='utf-8') as f:
            skeleton = f.read()
        
        # Create the prompt
        prompt = f"""Please implement the following Swift file with complete functionality:

File: {Path(file_path).name}

Current skeleton:
```swift
{skeleton}
```

The file is part of an iOS app following MVVM architecture. Based on the skeleton, 
please provide a complete implementation with all methods, properties, and functionality 
implemented. Make sure to add proper error handling, comments, and follow Swift best practices.

Please consider the following specific requirements from the MVP plan and architecture:

1. This file should implement all functionality described in the skeleton comments
2. Ensure proper integration with other components in the system
3. Follow SOLID principles and make the code testable
4. Use async/await for asynchronous operations where appropriate
5. Include thorough documentation for public APIs

Your implementation should replace the skeleton but keep the same class structure, property names, 
and method signatures. Add implementation to any TODOs and fill in any code marked with ellipses (...).

Return ONLY the complete Swift file implementation without additional explanations or markdown.
"""
        
        return prompt
    
    def run_development_pipeline(self):
        """Run the sequential development pipeline with namespace awareness."""
        self.console.print("[bold blue]Starting Sequential File Development[/bold blue]")
        
        # First detect any duplicate types
        duplicates = self.detect_duplicate_types()
        
        # Prioritize the development queue
        self.prioritize_development_queue()
        
        # Process all files in queue
        for i, file_path in enumerate(self.development_queue):
            self.console.print(f"[bold]Developing file {i+1}/{len(self.development_queue)}: {file_path.name}[/bold]")
            
            try:
                # Create context for this file
                context = self.build_context_for_file(file_path)
                
                # Create system prompt
                system_prompt = self.create_system_prompt_for_file(file_path)
                
                # Create development prompt
                prompt = self.create_development_prompt(file_path)
                
                # Create Claude instance
                engineer = Claude()
                
                # Send prompt
                response = engineer.send_prompt(prompt, context=None, system_prompt=system_prompt, maximize=True)
                
                # Extract Swift code from response
                swift_code = self.extract_swift_code(response)
                
                # Post-process the code to ensure naming conventions and avoid ambiguities
                swift_code = self.post_process_swift_code(file_path, swift_code)
                
                # Save the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(swift_code)
                
                # Add to completed files
                self.completed_files.append(file_path)
                
                self.console.print(f"[green]File developed successfully: {file_path.name}[/green]")
                
                # Wait between requests to avoid rate limit
                time.sleep(5)
                
            except Exception as e:
                self.console.print(f"[red]Error developing file {file_path.name}: {str(e)}[/red]")
        
        # If we had duplicate types, add namespaces to resolve them
        if duplicates:
            self.add_namespaces_to_architecture()
        
        return {
            "success": True,
            "completed": len(self.completed_files),
            "total": len(self.development_queue)
        }

    def run_development_pipeline_parallel(self, max_workers=3, requests_per_minute=10):
        """Run the parallel development pipeline with rate limiting and namespace awareness."""
        import concurrent.futures
        import time
        
        self.console.print(f"[bold blue]Starting Parallel File Development with {max_workers} workers[/bold blue]")
        
        # First detect any duplicate types
        duplicates = self.detect_duplicate_types()
        
        # Prioritize the development queue
        self.prioritize_development_queue()
        
        # Track completed files
        self.completed_files = []
        processed_count = 0
        
        # Process files with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            remaining_files = self.development_queue.copy()
            
            while remaining_files or futures:
                # Launch new tasks if slots are available and we respect rate limits
                while len(futures) < max_workers and remaining_files and len(futures) < requests_per_minute:
                    # Get next file with satisfied dependencies
                    next_file = self.get_next_ready_file(remaining_files)
                    if not next_file:
                        break
                        
                    self.console.print(f"[bold]Starting development for: {next_file.name} ({processed_count+1}/{len(self.development_queue)})[/bold]")
                    
                    future = executor.submit(self._develop_single_file, next_file)
                    futures[future] = next_file
                    remaining_files.remove(next_file)
                    processed_count += 1
                    
                    # Add small delay between launches to spread out requests
                    time.sleep(2)
                
                # Wait for any task to complete
                if futures:
                    done, _ = concurrent.futures.wait(
                        futures, timeout=5, 
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    
                    for future in done:
                        file_path = futures[future]
                        try:
                            result = future.result()
                            if result:
                                self.completed_files.append(file_path)
                                self.console.print(f"[green]Successfully developed: {file_path.name}[/green]")
                            else:
                                self.console.print(f"[red]Failed to develop: {file_path.name}[/red]")
                        except Exception as e:
                            self.console.print(f"[red]Error developing {file_path.name}: {str(e)}[/red]")
                        
                        del futures[future]
                else:
                    # No active futures but still have remaining files
                    # This happens if all files have unsatisfied dependencies
                    if remaining_files:
                        self.console.print("[yellow]Warning: Remaining files have unsatisfied dependencies. Taking first available.[/yellow]")
                        next_file = remaining_files.pop(0)
                        future = executor.submit(self._develop_single_file, next_file)
                        futures[future] = next_file
                        processed_count += 1
                        time.sleep(2)
        
        # If we had duplicate types, add namespaces to resolve them
        if duplicates:
            self.add_namespaces_to_architecture()
        
        success_rate = len(self.completed_files) / len(self.development_queue) if self.development_queue else 0
        self.console.print(f"[bold green]Development completed: {len(self.completed_files)}/{len(self.development_queue)} files ({success_rate*100:.1f}%)[/bold green]")
        
        return {
            "success": True,
            "completed": len(self.completed_files),
            "total": len(self.development_queue)
        }
    
    def extract_swift_code(self, response):
        """Extract Swift code from Claude's response."""
        # Try to find a Swift code block
        swift_pattern = r'```swift\s*(.*?)```'
        swift_matches = re.findall(swift_pattern, response, re.DOTALL)
        
        if swift_matches:
            return swift_matches[0].strip()
        
        # If no Swift code block, try to find just the code without markers
        # This is a fallback if Claude forgot to format as code block
        # Check for common Swift patterns
        if "import " in response and ("class " in response or "struct " in response or "enum " in response):
            # Strip any markdown or explanations before or after code
            lines = response.split('\n')
            start_idx = 0
            end_idx = len(lines)
            
            for i, line in enumerate(lines):
                if line.strip().startswith("import "):
                    start_idx = i
                    break
            
            for i in range(len(lines)-1, -1, -1):
                if lines[i].strip() == "}" and i > start_idx:
                    end_idx = i + 1
                    break
            
            return '\n'.join(lines[start_idx:end_idx])
        
        # If we can't extract code, return the whole response
        return response
    
    def run_development_pipeline_parallel(self, max_workers=3, requests_per_minute=10):
        """Run the parallel development pipeline with rate limiting."""
        import concurrent.futures
        import time
        
        self.console.print(f"[bold blue]Starting Parallel File Development with {max_workers} workers[/bold blue]")
        
        # Prioritize the development queue
        self.prioritize_development_queue()
        
        # Track completed files
        self.completed_files = []
        processed_count = 0
        
        # Process files with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            remaining_files = self.development_queue.copy()
            
            while remaining_files or futures:
                # Launch new tasks if slots are available and we respect rate limits
                while len(futures) < max_workers and remaining_files and len(futures) < requests_per_minute:
                    # Get next file with satisfied dependencies
                    next_file = self.get_next_ready_file(remaining_files)
                    if not next_file:
                        break
                        
                    self.console.print(f"[bold]Starting development for: {next_file.name} ({processed_count+1}/{len(self.development_queue)})[/bold]")
                    
                    future = executor.submit(self._develop_single_file, next_file)
                    futures[future] = next_file
                    remaining_files.remove(next_file)
                    processed_count += 1
                    
                    # Add small delay between launches to spread out requests
                    time.sleep(2)
                
                # Wait for any task to complete
                if futures:
                    done, _ = concurrent.futures.wait(
                        futures, timeout=5, 
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    
                    for future in done:
                        file_path = futures[future]
                        try:
                            result = future.result()
                            if result:
                                self.completed_files.append(file_path)
                                self.console.print(f"[green]Successfully developed: {file_path.name}[/green]")
                            else:
                                self.console.print(f"[red]Failed to develop: {file_path.name}[/red]")
                        except Exception as e:
                            self.console.print(f"[red]Error developing {file_path.name}: {str(e)}[/red]")
                        
                        del futures[future]
                else:
                    # No active futures but still have remaining files
                    # This happens if all files have unsatisfied dependencies
                    if remaining_files:
                        self.console.print("[yellow]Warning: Remaining files have unsatisfied dependencies. Taking first available.[/yellow]")
                        next_file = remaining_files.pop(0)
                        future = executor.submit(self._develop_single_file, next_file)
                        futures[future] = next_file
                        processed_count += 1
                        time.sleep(2)
        
        success_rate = len(self.completed_files) / len(self.development_queue) if self.development_queue else 0
        self.console.print(f"[bold green]Development completed: {len(self.completed_files)}/{len(self.development_queue)} files ({success_rate*100:.1f}%)[/bold green]")
        
        return {
            "success": True,
            "completed": len(self.completed_files),
            "total": len(self.development_queue)
        }

    def _develop_single_file(self, file_path):
        """Develop a single file with proper context."""
        try:
            # Create context for this file
            context = self.build_context_for_file(file_path)
            
            # Create system prompt
            system_prompt = self.create_system_prompt_for_file(file_path)
            
            # Create development prompt
            prompt = self.create_development_prompt(file_path)
            
            # Create Claude instance
            engineer = Claude()
            
            # Send prompt
            response = engineer.send_prompt(prompt, context=None, system_prompt=system_prompt)
            
            # Extract Swift code from response
            swift_code = self.extract_swift_code(response)
            
            # Save the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(swift_code)
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error developing file {file_path.name}: {str(e)}[/red]")
            return False

    def build_context_for_file(self, file_path):
        """Build context dictionary with relevant information for this file."""
        context = {}
        
        # Add the file skeleton itself
        with open(file_path, 'r', encoding='utf-8') as f:
            context[file_path.name] = f.read()
        
        # Add direct dependencies
        for dependency in self.dependency_graph.predecessors(file_path):
            if dependency in self.completed_files:
                with open(dependency, 'r', encoding='utf-8') as f:
                    context[dependency.name] = f.read()
        
        # Add architecture excerpts
        context['architecture'] = self.extract_relevant_architecture(file_path)
        
        # Add MVP excerpts
        context['mvp'] = self.extract_relevant_mvp(file_path)
        
        return context
    
    def detect_duplicate_types(self):
        """Scan the architecture document to detect duplicate type names across files."""
        duplicate_types = {}
        all_types = {}
        
        # Parse Swift files to find defined types
        for file_path in self.development_queue:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract all type definitions (class, struct, enum, protocol)
            type_pattern = r'(?:class|struct|enum|protocol)\s+([A-Za-z0-9_]+)'
            types_defined = re.findall(type_pattern, content)
            
            for type_name in types_defined:
                if type_name in all_types:
                    # Found a duplicate
                    if type_name not in duplicate_types:
                        duplicate_types[type_name] = [all_types[type_name]]
                    duplicate_types[type_name].append(file_path)
                else:
                    all_types[type_name] = file_path
        
        # Log detected duplicates
        if duplicate_types:
            self.console.print("[yellow]Warning: Detected duplicate type names across files:[/yellow]")
            for type_name, files in duplicate_types.items():
                self.console.print(f"  [bold]{type_name}[/bold] appears in:")
                for file_path in files:
                    self.console.print(f"    - {file_path}")
        
        return duplicate_types

    def add_namespaces_to_architecture(self):
        """Add namespaces to the architecture to prevent duplicate type names."""
        # First detect duplicates
        duplicates = self.detect_duplicate_types()
        
        if not duplicates:
            self.console.print("[green]No duplicate types detected.[/green]")
            return
        
        self.console.print("[bold blue]Adding namespaces to resolve duplicate types...[/bold blue]")
        
        # Process each file that contains duplicate types
        for type_name, file_paths in duplicates.items():
            for i, file_path in enumerate(file_paths):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Determine a proper namespace based on file path
                file_category = "Unknown"
                if "Model" in file_path.name:
                    file_category = "Models"
                elif "ViewModel" in file_path.name:
                    file_category = "ViewModels"
                elif "View" in file_path.name:
                    file_category = "Views"
                elif "Service" in file_path.name:
                    file_category = "Services"
                elif "Controller" in file_path.name:
                    file_category = "Controllers"
                
                # Add namespace wrapper
                namespace_content = f"""// Namespace added to prevent type conflicts
    enum {file_category} {{
    {self._indent_code(content)}
    }}

    // Type alias for backward compatibility
    typealias {type_name} = {file_category}.{type_name}
    """
                
                # Write back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(namespace_content)
                
                self.console.print(f"[green]Added namespace {file_category} to {file_path.name}[/green]")
        
        self.console.print("[green]Completed adding namespaces.[/green]")

    def _indent_code(self, code, spaces=4):
        """Indent code by specified number of spaces."""
        lines = code.split('\n')
        indented_lines = [' ' * spaces + line for line in lines]
        return '\n'.join(indented_lines)
    
    def post_process_swift_code(self, file_path, swift_code):
        """Post-process generated Swift code to ensure consistent naming and avoid ambiguities."""
        filename = Path(file_path).name
        
        # Detect file category and suggest appropriate naming convention
        file_category = None
        type_suffix = None
        
        if "Model" in filename and "ViewModel" not in filename:
            file_category = "Models"
            type_suffix = "Model"
        elif "ViewModel" in filename:
            file_category = "ViewModels"
            type_suffix = "ViewModel"
        elif "View" in filename and "Controller" not in filename:
            file_category = "Views"
            type_suffix = "View"
        elif "Service" in filename:
            file_category = "Services"
            type_suffix = "Service"
        elif "Repository" in filename:
            file_category = "Repositories"
            type_suffix = "Repository"
        elif "Controller" in filename:
            file_category = "Controllers"
            type_suffix = "Controller"
        
        # If no specific category detected, return the original code
        if not file_category or not type_suffix:
            return swift_code
        
        # Extract the main type name from the file
        type_pattern = r'(?:class|struct|enum|protocol)\s+([A-Za-z0-9_]+)'
        types_defined = re.findall(type_pattern, swift_code)
        
        if not types_defined:
            return swift_code  # No types found
        
        main_type = types_defined[0]
        
        # Check if the main type already has the appropriate suffix
        if not main_type.endswith(type_suffix):
            # Replace the type name with the suffixed version
            new_type_name = main_type + type_suffix
            swift_code = re.sub(
                rf'(class|struct|enum|protocol)\s+{re.escape(main_type)}', 
                f'\\1 {new_type_name}', 
                swift_code
            )
            
            # Replace references to the type within the file
            swift_code = re.sub(
                rf'\b{re.escape(main_type)}\b(?!\w)', 
                new_type_name, 
                swift_code
            )
            
            self.console.print(f"[green]Renamed type {main_type} to {new_type_name} in {file_path.name}[/green]")
        
        # Check if we need to add namespace
        # For now, let's keep it simple and not wrap everything in namespaces by default
        # This would be activated only when duplicates are detected by the duplicate detector
        
        return swift_code

    def extract_swift_code(self, response):
        """Extract Swift code from Claude's response and post-process it."""
        # Try to find a Swift code block
        swift_pattern = r'```swift\s*(.*?)```'
        swift_matches = re.findall(swift_pattern, response, re.DOTALL)
        
        if swift_matches:
            return swift_matches[0].strip()
        
        # If no Swift code block, try to find just the code without markers
        # This is a fallback if Claude forgot to format as code block
        # Check for common Swift patterns
        if "import " in response and ("class " in response or "struct " in response or "enum " in response):
            # Strip any markdown or explanations before or after code
            lines = response.split('\n')
            start_idx = 0
            end_idx = len(lines)
            
            for i, line in enumerate(lines):
                if line.strip().startswith("import "):
                    start_idx = i
                    break
            
            for i in range(len(lines)-1, -1, -1):
                if lines[i].strip() == "}" and i > start_idx:
                    end_idx = i + 1
                    break
            
            return '\n'.join(lines[start_idx:end_idx])
        
        # If we can't extract code, return the whole response
        return response

    def _develop_single_file(self, file_path):
        """Develop a single file with proper context and post-processing."""
        try:
            # Create context for this file
            context = self.build_context_for_file(file_path)
            
            # Create system prompt
            system_prompt = self.create_system_prompt_for_file(file_path)
            
            # Create development prompt
            prompt = self.create_development_prompt(file_path)
            
            # Create Claude instance
            engineer = Claude()
            
            # Send prompt
            response = engineer.send_prompt(prompt, context=None, system_prompt=system_prompt)
            
            # Extract Swift code from response
            swift_code = self.extract_swift_code(response)
            
            # Post-process the code to ensure naming conventions and avoid ambiguities
            swift_code = self.post_process_swift_code(file_path, swift_code)
            
            # Save the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(swift_code)
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error developing file {file_path.name}: {str(e)}[/red]")
            return False