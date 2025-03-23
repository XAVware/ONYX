# ONYX

ONYX is an advanced toolchain that uses Anthropic's Claude Sonnet 3.7 and OpenAI to automate and accelerate iOS app development. It creates a complete workflow from initial app idea to working Xcode project with minimal human intervention.

WARNING: Running this will cost over $10 in Anthropic fees.

## Features

- **App Planning Workflow**: Generate business plans, user stories, and MVP features from a simple app idea
- **Architecture Design**: Create system diagrams, class structures, and data models
- **Swift Code Generation**: Transform architecture plans into working Swift code
- **Build & Fix**: Automatically build Xcode projects and fix compilation errors
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

#### Basic App Creation

To create a new app from a simple idea:

```bash
python3 main.py "An app to track my fitness"
```

This will:
1. Generate a business plan
2. Create user stories and backlog
3. Define MVP features
4. Design system architecture with diagrams
5. Generate Swift code for all components
6. Build the Xcode project and fix errors (as long as a valid XCode project exists at the project directory)


Also

brew install xcodegen