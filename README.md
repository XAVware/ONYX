# ONYX

ONYX is an advanced toolchain that uses Anthropic's Claude Sonnet 3.7 and OpenAI to automate and accelerate iOS app development. It creates a complete workflow from initial app idea to working Xcode project with minimal human intervention.

WARNING: Running this will cost over $10 in Anthropic fees.

## Features

- **Three-Step Workflow**: Separate planning, XCode setup, and development phases for better control
- **App Planning**: Generate business plans, user stories, and MVP features from a simple app idea
- **Architecture Design**: Create system diagrams, class structures, and data models
- **XCode Integration**: Dedicated XCode project creation and build management
- **Swift Code Generation**: Transform architecture plans into working Swift code
- **Build & Fix**: Automatically build Xcode projects and fix compilation errors
- **Financial Analysis**: Generate comprehensive financial plans and market analysis
- **Documentation**: Generate beautiful architectural documentation with Mermaid diagrams

## Getting Started

### Prerequisites

- Python 3.8+
- Anthropic API key (Claude 3.7 Sonnet)
- Xcode (for build and deployment)
- Required Python packages (see Installation)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/XAVware/ONYX.git
   cd xavware
   ```

2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   
3. Create a `.env` file in the root directory with your Anthropic and OpenAI API keys:
   ```
   ANTHROPIC_API_KEY=your_api_key
   OPENAI_API_KEY=your_api_key
   ```

### Usage

ONYX now uses a three-step workflow: **Planning**, **XCode Setup**, and **Development**. This separation allows for better control and flexibility in the app creation process.

#### Step 1: Planning Workflow

Generate the app planning documents and architecture:

```bash
python3 onyx/main.py "An app to track my fitness" --project-name MyFitnessApp
```

This will:
1. Generate a business plan
2. Create user stories and backlog
3. Define MVP features
4. Design system architecture with diagrams
5. Create project skeleton files
6. Generate documentation with Mermaid diagrams

#### Step 2: XCode Project Setup

Create and configure the XCode project:

```bash
python3 onyx/xcode.py create ~/Projects/MyFitnessApp
```

This will:
1. Create XCode project structure from template
2. Configure project settings and bundle IDs
3. Set up development team and signing
4. Optionally build the initial project

#### Step 3: Development Workflow

Generate Swift code from the architecture:

```bash
python3 onyx/develop.py MyFitnessApp
```

This will:
1. Generate Swift code for all architectural layers
2. Build the Xcode project automatically
3. Fix compilation errors iteratively
4. Create a working iOS app

#### Advanced Usage

**XCode Project Options:**

```bash
# Create XCode project and build immediately
python3 onyx/xcode.py create ~/Projects/MyFitnessApp --build

# Build an existing XCode project
python3 onyx/xcode.py build ~/Projects/MyFitnessApp

# Build with specific configuration
python3 onyx/xcode.py build ~/Projects/MyFitnessApp --configuration Release

# Build without cleaning first (faster)
python3 onyx/xcode.py build ~/Projects/MyFitnessApp --no-clean
```

**Custom Development Options:**

```bash
# Develop specific layers only
python3 onyx/develop.py MyFitnessApp --layers Models Services

# Skip the build cycle (faster development)
python3 onyx/develop.py MyFitnessApp --skip-build

# Use custom project directory
python3 onyx/develop.py MyFitnessApp --project-dir /path/to/custom/location
```

**Financial Planning Tool:**

Generate financial plans and market analysis from business documents:

```bash
python3 source/finance.py Business_Plan.md MVP.md --output financial_analysis.md
```

#### Prerequisites

Make sure you have the following installed:

```bash
brew install xcodegen
```

## XCode Function Reference

The `onyx/xcode.py` script provides three main functions for XCode project management:

### Command Line Interface

```bash
# View all available commands
python3 onyx/xcode.py --help

# View help for specific commands
python3 onyx/xcode.py create --help
python3 onyx/xcode.py build --help
python3 onyx/xcode.py setup --help
```

### `create` - Create XCode Project

Creates a new XCode project from template with proper configuration:

```bash
# Basic project creation
python3 onyx/xcode.py create /path/to/project

# Create and build immediately
python3 onyx/xcode.py create /path/to/project --build
```

**What it does:**
- Creates XCode project structure from template
- Configures project settings and bundle IDs
- Sets up development team and signing
- Renames files and classes to match project name
- Optionally builds the project after creation

### `build` - Build XCode Project

Builds an existing XCode project and returns detailed error information:

```bash
# Basic build (Debug configuration with clean)
python3 onyx/xcode.py build /path/to/project

# Release build
python3 onyx/xcode.py build /path/to/project --configuration Release

# Build without cleaning (faster)
python3 onyx/xcode.py build /path/to/project --no-clean

# Build and ignore warnings
python3 onyx/xcode.py build /path/to/project --ignore-warnings
```

**What it does:**
- Builds the XCode project using `xcodebuild`
- Parses build output for errors and warnings
- Returns detailed error information with file locations
- Supports different build configurations
- Provides clean, readable error reporting

### `setup` - Setup Project Structure

Sets up XCode project structure without building:

```bash
# Setup project structure only
python3 onyx/xcode.py setup /path/to/project
```

**What it does:**
- Creates XCode project structure from template
- Configures project settings
- Does not attempt to build the project
- Useful for initial project setup

### Integration with Other Scripts

The XCode functions are designed to work seamlessly with other ONYX scripts:

```bash
# Complete workflow example
python3 onyx/main.py "fitness app" --project-name MyFitnessApp
python3 onyx/xcode.py create ~/Projects/MyFitnessApp
python3 onyx/develop.py MyFitnessApp
python3 onyx/xcode.py build ~/Projects/MyFitnessApp --configuration Release
```

### Error Handling

The XCode functions provide comprehensive error handling:

- **Missing project files**: Clear error messages when `.xcodeproj` files aren't found
- **Build errors**: Detailed error information with file locations and line numbers
- **Configuration errors**: Helpful messages for setup and configuration issues
- **Template errors**: Clear feedback when project template is missing or corrupted

### Using XCode Functions in Code

You can also import and use these functions directly in your Python code:

```python
from onyx.xcode import create_project, build, setup_project
from pathlib import Path

# Create a project
project_path = Path("~/Projects/MyApp").expanduser()
success = create_project(project_path, build_after_create=False)

# Build the project
if success:
    messages = build(project_path, configuration="Debug", clean=True)
    errors = [msg for msg in messages if msg.type == "error"]
    if not errors:
        print("Build successful!")
```

## Project Structure

After running ONYX, your project will be organized as follows:

```
Projects/
└── MyFitnessApp/
    ├── plans/                          # Planning documents
    │   ├── Business_Plan.md            # Generated business plan
    │   ├── Agile_Planner.md           # User stories and backlog
    │   ├── MVP.md                     # MVP definition
    │   ├── ArchitectureDiagrams.md    # System diagrams
    │   └── Architecture.md            # Technical architecture
    ├── ios_skeleton/                   # Initial Swift skeleton
    │   ├── Models/                    # Data models
    │   ├── Services/                  # Business logic
    │   ├── ViewModels/               # MVVM view models
    │   └── Views/                    # SwiftUI views
    ├── ios_source/                    # Final Swift code
    │   ├── Models/                   # Generated data models
    │   ├── Services/                 # Generated services
    │   ├── ViewModels/              # Generated view models
    │   └── Views/                   # Generated views
    └── docs/                        # Documentation
        ├── html/                    # Generated HTML docs
        └── diagrams/               # Mermaid diagram files
```

## Workflow Tips

1. **Review Before Development**: Always review the generated plans in the `plans/` directory before creating XCode projects
2. **XCode Project Management**: Use the dedicated XCode script for all project creation and building
3. **Iterative Development**: You can re-run the development script to refine the code
4. **Custom Layers**: Use `--layers` to focus on specific components during development
5. **Skip Build**: Use `--skip-build` for faster iterations when you don't need immediate compilation
6. **Financial Planning**: Use the finance tool to create investor-ready financial analysis
7. **Build Configurations**: Use Debug for development and Release for production builds