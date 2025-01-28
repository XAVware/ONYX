import json
from textwrap import dedent
from openai import OpenAI
from pathlib import Path
import os

def analyze_swift_file(file_path):
    """
    Analyze a single Swift file using GPT.
    """
    with open(file_path, 'r') as file:
        swift_code=file.read()

    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "code_analyzing",
            "schema": {
                "type": "object",
                "properties": {
                    "abstract": {
                        "type": "string"
                    },
                    "analysis": {
                        "type": "string"
                    },
                    "improvements": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "notes": {
                        "type": "string"
                    }
                },
                "required": ["abstract", "analysis", "improvements", "notes"],
                "additionalProperties": False
            },
            "strict": True
        }
    }


    prompt=f"""
    You are a Swift programming expert. Your task is to review the following Swift code and provide structured feedback.

    Here is the schema for your response:
    - abstract: A brief overview of what the file does.
    - analysis: A detailed explanation of how the code works as a whole and its structure.
    - improvements: A list of specific improvements to the code.
    - notes: Any additional comments or observations about the code quality.

    Code:
    ```swift
    {swift_code}
    ```
    """
    response=OpenAI().chat.completions.create(
        model="gpt-4o-2024-08-06",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "You are a helpful programming assistant."},
            {"role": "user", "content": prompt}
        ],
        response_format=response_format
        )

    return response.choices[0].message

def analyze_directory(directory_path):
    """
    Analyze all .swift files in the given directory and return the results.
    """
    results=[]
    swift_files=Path(directory_path).rglob("*.swift")

    for file_path in swift_files:
        print(f"Analyzing {file_path}...")
        try:
            analysis=analyze_swift_file(file_path)
            results.append({
                "file": str(file_path),
                "analysis": analysis.content
            })
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    return results

def save_results_to_markdown(results, output_path):
    """
    Save the analysis results to a Markdown file.
    """
    with open(output_path, 'w') as md_file:
        md_file.write("# Swift Code Analysis Results\n\n")
        for result in results:
            file_name=os.path.basename(result["file"])
            analysis=json.loads(result["analysis"])

            md_file.write(f"## {file_name}\n\n")
            md_file.write("### Abstract:\n")
            md_file.write(f"{analysis.get('abstract', 'N/A')}\n\n")
            
            md_file.write("### Analysis:\n")
            md_file.write(f"{analysis.get('analysis', 'N/A')}\n\n")

            md_file.write("### Improvements:\n")
            for improvement in analysis.get("improvements", []):
                md_file.write(f"- {improvement}\n")
            md_file.write("\n")
            
            md_file.write("### Notes:\n")
            md_file.write(f"{analysis.get('notes', 'N/A')}\n\n")
            md_file.write("---\n\n")
    print(f"Results saved to {output_path}")


def save_results_to_json(results, output_path):
    """
    Save the analysis results to a JSON file with properly formatted and indented 'analysis' fields.
    """
    formatted_results=[]

    for result in results:
        try:
            analysis_data=json.loads(result["analysis"])

            formatted_results.append({
                "file": result["file"],
                "analysis": analysis_data
            })
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for file {result['file']}: {e}")
            formatted_results.append(result)

    with open(output_path, 'w') as json_file:
        json.dump(formatted_results, json_file, indent=4) 

    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    input_directory="../Frameworks/Swift/AuthApp/AuthApp/Features/Alerts"  # Replace with your directory
    output_file="./swift_analysis_results.json"
    output_markdown_file="./swift_analysis_results.md"

    results=analyze_directory(input_directory)
    save_results_to_json(results, output_file)
    save_results_to_markdown(results, output_markdown_file)
