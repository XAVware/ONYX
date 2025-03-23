import os
import re
from apple_defaults import APPLE_TYPES

STANDARD_TYPES = {
    "String",
    "Int",
    "Double",
    "Float",
    "Bool",
    "Array",
    "Dictionary",
    "Set",
    "Data",
    "UInt64"
}

ADDITIONAL_IGNORE = {
    "Yes",
    "No",
    "A",
    "B",
    "C",
    "D",
    "TD",
    "OK",
    "End",
    "Start",
    "Is",
    "The",
    "DiagramType",    
}

class FileSkeleton:
    def __init__(self, file_path, definitions, references, category):
        self.file_path = file_path
        self.definitions = definitions
        self.references = references
        self.category = category
        self.issues: list[str] = []

    def __repr__(self):
        return f"{self.file_path} ({self.category})\nDefinitions: {self.definitions}\nReferences: {self.references}\n"

def categorize_definition(file_path):
    """
    Determines the category of a definition based on its file path.
    """
    if "ViewModels" in file_path:
        return "ViewModel"
    elif "Views" in file_path:
        return "View"
    elif "Services" in file_path:
        return "Service"
    elif "Models" in file_path:
        return "Model"
    else:
        return "Other"

def extract_skeleton(directory) -> list[FileSkeleton]:
    """
    Recursively searches an iOS app directory for Swift files and extracts type definitions.
    Stores explicit definitions separately from references.
    """
    print("Extracting project skeleton...")
    skeletons = []

    identifier_pattern = re.compile(r'\b[A-Z][a-zA-Z0-9_]*\b')  # Match capitalized words
    type_definition_pattern = re.compile(r'\b(?:struct|class|enum|protocol|extension)\s+([A-Z][a-zA-Z0-9_]*)')
    comment_pattern = re.compile(r'/\*[\s\S]*?\*/|//.*')  # Remove all comment types
    string_pattern = re.compile(r'"(?:\\.|[^"\\])*"')  # Remove anything inside double quotes

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".swift"):  # Only process Swift files
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    content = re.sub(comment_pattern, '', content)
                    content = re.sub(string_pattern, '', content)

                    content = "\n".join(line.split("import", 1)[0] for line in content.splitlines())

                    all_identifiers = set(
                        match for match in identifier_pattern.findall(content)
                        if match not in STANDARD_TYPES 
                        and match not in APPLE_TYPES 
                        and match not in ADDITIONAL_IGNORE
                    )

                    defined_types = set(type_definition_pattern.findall(content))

                    definitions = {f"{ident}" for ident in defined_types}
                    references = all_identifiers - defined_types

                    category = categorize_definition(file_path)

                    skeleton = FileSkeleton(
                        file_path=file_path,
                        definitions=definitions,
                        references=references,
                        category=category
                    )
                    skeletons.append(skeleton)

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return skeletons

# if __name__ == "__main__":
#     """
#     Extracts struct, class, enum, protocol, and extension definitions from Swift files 
#     in the project directory and subdirectories.
#     Categorizes them and stores them as FileSkeleton objects.
#     """
#     from onyx import config
#     from pathlib import Path
#     from typing import DefaultDict
#     from xcode_service import build_xcode_project


#     project_dir = Path(config.directories.projects).expanduser()
#     project_name = "uParker"
#     app_dir = Path(project_dir / project_name)
#     skeletons = extract_skeleton(app_dir)

#     errors = build_xcode_project(project_dir=str(app_dir))
#     files_with_error = []
#     for err in errors:
#         files_with_error.append(err.file)
#     # Create useful maps for lookups
#     all_skeletons = {s.file_path: s for s in skeletons}
#     definition_map = DefaultDict(list)

#     # Map definitions to files
#     for skeleton in skeletons:
#         for definition in skeleton.definitions:
#             definition_map[definition].append(skeleton.file_path)

#     # Find all relevant files (the files with errors and files they reference)
#     relevant_files = set(files_with_error)

#     # Add files referenced by error files (dependencies)
#     for file_path in files_with_error:
#         skeleton = all_skeletons.get(file_path)
#         if skeleton:
#             # For each reference, find files that define it
#             for ref in skeleton.references:
#                 for s in skeletons:
#                     if ref in s.definitions:
#                         relevant_files.add(s.file_path)

#     # Add files that reference error files (dependents)
#     # for file_path in files_with_error:
#     #     for s in skeletons:
#     #         # If any definition in the error file is referenced elsewhere
#     #         for def_name in skeletons.get(
#     #             file_path, FileSkeleton("", set(), set(), "")
#     #         ).definitions:
#     #             if def_name in s.references:
#     #                 relevant_files.add(s.file_path)

#     # Limit to reasonable number (avoid prompt too large)
#     if len(relevant_files) > 8:
#         print(
#             f"  Too many relevant files ({len(relevant_files)}), limiting to most important"
#         )
#         # Prioritize error files and direct dependencies
#         relevant_files = set(files_with_error)
#         for file_path in files_with_error:
#             skeleton = all_skeletons.get(file_path)
#             if skeleton:
#                 # Add up to 3 most relevant dependencies
#                 for ref in list(skeleton.references)[:3]:
#                     for s in all_skeletons:
#                         if ref in s.definitions:
#                             relevant_files.add(s.file_path)
#                             break

#     # Read content of all relevant files
#     file_contents = {}
#     for file_path in relevant_files:
#         try:
#             with open(file_path, "r") as f:
#                 file_contents[file_path] = f.read()
#         except Exception as e:
#             print(f"Error reading {file_path}: {e}")
#             file_contents[file_path] = f"ERROR READING FILE: {e}"

#     # Create project structure context - helpful for understanding architecture
#     project_structure = ""
#     for skeleton in all_skeletons:
#         project_structure += f"{skeleton.file_path} ({skeleton.category})\n"
#         project_structure += f"Definitions: {skeleton.definitions}\n"
#         project_structure += f"References: {skeleton.references}\n\n"
#     prompt = ""
#     for file_path, content in file_contents.items():
#         prompt += f"\n--- {file_path} ---\n```swift\n{content}\n```\n"

#     print(prompt)