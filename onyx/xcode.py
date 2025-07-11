#!/usr/bin/env python3
"""
ONYX XCode Integration

This module provides XCode project creation and building functionality.
It handles:
- Creating new XCode projects from templates
- Building XCode projects and returning errors
- Project setup and configuration
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Add the parent directory to the path so we can import onyx modules
script_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(script_dir))

# Import onyx modules after path setup
from onyx.xcode_service import (  # noqa: E402
    create_project as xcode_create_project,
    build_xcode_project,
    BuildMessage,
    setup_xcode_project
)
from onyx import get_logger, print_fancy, config  # noqa: E402

logger = get_logger(__name__)

def create_project(project_path: Path, build_after_create: bool = False) -> bool:
    """
    Create a new XCode project at the specified path.
    
    Args:
        project_path: Path where the XCode project should be created
        build_after_create: Whether to build the project after creation
        
    Returns:
        bool: True if project creation was successful, False otherwise
    """
    try:
        logger.info(f"Creating XCode project at: {project_path}")
        
        # Ensure the project directory exists
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Use the existing xcode_service functionality
        success = xcode_create_project(project_path, build=build_after_create)
        
        if success:
            print_fancy(f"✅ XCode project created successfully at: {project_path}", "green")
            return True
        else:
            print_fancy(f"❌ Failed to create XCode project at: {project_path}", "red")
            return False
            
    except Exception as e:
        logger.error(f"Error creating XCode project: {e}")
        print_fancy(f"❌ Error creating XCode project: {e}", "red")
        return False

def build(project_path: Path, 
          configuration: str = "Debug",
          clean: bool = True,
          ignore_warnings: bool = False) -> List[BuildMessage]:
    """
    Build an XCode project and return build messages.
    
    Args:
        project_path: Path to the XCode project directory
        configuration: Build configuration (Debug/Release)
        clean: Whether to clean before building
        ignore_warnings: Whether to filter out warnings from results
        
    Returns:
        List[BuildMessage]: List of build messages (errors, warnings, etc.)
    """
    try:
        logger.info(f"Building XCode project at: {project_path}")
        
        # Verify the project exists
        if not project_path.exists():
            error_msg = f"Project directory not found: {project_path}"
            logger.error(error_msg)
            return [BuildMessage(
                type="error",
                file="build_system",
                line=0,
                message=error_msg,
                context=""
            )]
        
        # Find XCode project files
        xcodeproj_files = list(project_path.glob("*.xcodeproj"))
        if not xcodeproj_files:
            error_msg = f"No .xcodeproj file found in {project_path}"
            logger.error(error_msg)
            return [BuildMessage(
                type="error",
                file="build_system",
                line=0,
                message=error_msg,
                context=""
            )]
        
        # Build the project
        messages = build_xcode_project(
            project_path,
            configuration=configuration,
            clean=clean,
            ignore_warnings=ignore_warnings
        )
        
        # Count errors and warnings
        errors = [msg for msg in messages if msg.type == "error"]
        warnings = [msg for msg in messages if msg.type == "warning"]
        
        if errors:
            print_fancy(f"❌ Build failed with {len(errors)} errors and {len(warnings)} warnings", "red")
        elif warnings:
            print_fancy(f"⚠️  Build succeeded with {len(warnings)} warnings", "yellow")
        else:
            print_fancy("✅ Build succeeded with no errors or warnings", "green")
        
        return messages
        
    except Exception as e:
        logger.error(f"Error building XCode project: {e}")
        return [BuildMessage(
            type="error",
            file="build_system",
            line=0,
            message=f"Build system error: {e}",
            context=""
        )]

def setup_project(project_path: Path) -> Optional[Path]:
    """
    Set up an XCode project structure without building.
    
    Args:
        project_path: Path where the XCode project should be set up
        
    Returns:
        Optional[Path]: Path to the project if successful, None otherwise
    """
    try:
        logger.info(f"Setting up XCode project structure at: {project_path}")
        
        # Ensure the project directory exists
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Use the existing setup functionality
        result_path = setup_xcode_project(project_path)
        
        if result_path:
            print_fancy(f"✅ XCode project structure set up at: {result_path}", "green")
            return result_path
        else:
            print_fancy(f"❌ Failed to set up XCode project structure", "red")
            return None
            
    except Exception as e:
        logger.error(f"Error setting up XCode project: {e}")
        print_fancy(f"❌ Error setting up XCode project: {e}", "red")
        return None

def parse_arguments():
    """Parse command-line arguments for XCode operations."""
    parser = argparse.ArgumentParser(description="ONYX XCode Integration")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create project command
    create_parser = subparsers.add_parser("create", help="Create a new XCode project")
    create_parser.add_argument("project_path", help="Path for the new XCode project")
    create_parser.add_argument("--build", action="store_true", help="Build the project after creation")
    
    # Build project command
    build_parser = subparsers.add_parser("build", help="Build an XCode project")
    build_parser.add_argument("project_path", help="Path to the XCode project")
    build_parser.add_argument("--configuration", "-c", default="Debug", 
                            choices=["Debug", "Release"], help="Build configuration")
    build_parser.add_argument("--no-clean", action="store_true", help="Don't clean before building")
    build_parser.add_argument("--ignore-warnings", action="store_true", help="Ignore warnings in output")
    
    # Setup project command
    setup_parser = subparsers.add_parser("setup", help="Set up XCode project structure")
    setup_parser.add_argument("project_path", help="Path for the XCode project setup")
    
    return parser.parse_args()

def main():
    """Main function for command-line usage."""
    args = parse_arguments()
    
    if not args.command:
        print_fancy("Please specify a command: create, build, or setup", "yellow")
        print_fancy("Use --help for more information", "cyan")
        return
    
    project_path = Path(args.project_path).resolve()
    
    if args.command == "create":
        success = create_project(project_path, build_after_create=args.build)
        if success:
            print_fancy("XCode project creation completed successfully!", "green", panel=True)
        else:
            print_fancy("XCode project creation failed!", "red", panel=True)
            sys.exit(1)
    
    elif args.command == "build":
        messages = build(
            project_path,
            configuration=args.configuration,
            clean=not args.no_clean,
            ignore_warnings=args.ignore_warnings
        )
        
        # Print detailed error information
        errors = [msg for msg in messages if msg.type == "error"]
        if errors:
            print_fancy("Build Errors:", "red", panel=True)
            for error in errors:
                print(f"📁 {error.file}:{error.line}")
                print(f"❌ {error.message}")
                if error.context:
                    print(f"   Context: {error.context}")
                print()
            sys.exit(1)
    
    elif args.command == "setup":
        result_path = setup_project(project_path)
        if result_path:
            print_fancy("XCode project setup completed successfully!", "green", panel=True)
        else:
            print_fancy("XCode project setup failed!", "red", panel=True)
            sys.exit(1)

if __name__ == "__main__":
    main()