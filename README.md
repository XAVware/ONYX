# ONYX
Draft project for analyzing Swift code files in a directory. It uses OpenAI's GPT API to generate structured suggestions for code improvements, detailed analysis, and notes. The output is saved as both a JSON file and a Markdown.

## System Requirements
- Python 3.8 or higher
- An OpenAI API key

## Python Dependencies
Install the required Python packages:

```zsh
pip install openai
```

## Getting Started

1. Clone this repository to your local machine:
```zsh
git clone https://github.com/xavware/ONYX.git
cd ONYX
```

2. Setup your virtual environment
```zsh
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows
```

3. Install the dependencies
```zsh
pip install -r requirements.txt
```

### Set Up OpenAI API Key

Set your OpenAI API key as an environment variable:
```zsh
export OPENAI_API_KEY=your_openai_api_key
```
Alternatively, modify the script to include the API key directly:

```python
import openai
openai.api_key = "your_openai_api_key"
```

### Usage
Edit the input_directory in the script to point to your directory of Swift files. The script will recursively analyze all .swift files within the specified directory.:

```python
input_directory = "../path/to/swift/files"
```
Run the script:
```zsh
    python script.py
```

After execution, the results will be saved in:
    swift_analysis_results.json: A structured JSON file.
    swift_analysis_results.md: A human-readable Markdown file.
