import os
import anthropic
import argparse
import json
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Load API key from environment
load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("Please set the ANTHROPIC_API_KEY environment variable")

# Initialize the Anthropic client
client = anthropic.Anthropic(api_key=API_KEY)


class TextEditorDemo:
    def __init__(self, working_dir: str = "."):
        """Initialize the text editor demo with a working directory."""
        self.working_dir = os.path.abspath(working_dir)
        self.file_backups = {}  # Store backups for undo_edit
        self.messages = []  # Conversation history
        print(f"Working directory: {self.working_dir}")

    def get_absolute_path(self, path: str) -> str:
        """Convert a relative path to an absolute path within working_dir."""
        # Prevent directory traversal attacks
        abs_path = os.path.abspath(os.path.join(self.working_dir, path))
        if not abs_path.startswith(self.working_dir):
            raise ValueError(
                f"Path {path} attempts to access outside the working directory"
            )
        return abs_path

    def handle_view(self, path: str, view_range=None) -> str:
        """
        Handle the 'view' command to read a file or list directory contents.
        """
        abs_path = self.get_absolute_path(path)

        if os.path.isdir(abs_path):
            # List directory contents
            try:
                files = os.listdir(abs_path)
                return "\n".join(files)
            except Exception as e:
                return f"Error listing directory: {str(e)}"

        elif os.path.isfile(abs_path):
            # Read file contents
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Process view range if provided
                if view_range:
                    start_line = max(0, view_range[0] - 1)  # Convert to 0-indexed
                    end_line = view_range[1]
                    if end_line == -1:  # -1 means read to end
                        end_line = len(lines)
                    else:
                        end_line = min(len(lines), end_line)
                    lines = lines[start_line:end_line]

                # Add line numbers
                numbered_lines = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
                return "".join(numbered_lines)
            except Exception as e:
                return f"Error reading file: {str(e)}"

        else:
            return f"Path does not exist: {path}"

    def handle_str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """
        Handle the 'str_replace' command to replace text in a file.
        """
        abs_path = self.get_absolute_path(path)

        if not os.path.isfile(abs_path):
            return f"File does not exist: {path}"

        try:
            # Create a backup of the file
            with open(abs_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            self.file_backups[abs_path] = original_content

            # Count occurrences to ensure unique match
            occurrences = original_content.count(old_str)
            if occurrences == 0:
                print(f"Warning: No matches found for the text to replace in {path}")
                print(f"Text to replace: {repr(old_str)}")
                return "No matches found for the text to replace."
            if occurrences > 1:
                print(f"Warning: Found {occurrences} occurrences of the text in {path}")
                return f"Found {occurrences} occurrences of the text. Must match exactly one location."

            # Replace the text
            new_content = original_content.replace(old_str, new_str)

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return "Successfully replaced text at exactly one location."

        except Exception as e:
            return f"Error replacing text: {str(e)}"

    def handle_create(self, path: str, file_text: str) -> str:
        """
        Handle the 'create' command to create a new file.
        """
        abs_path = self.get_absolute_path(path)

        if os.path.exists(abs_path):
            return f"File already exists: {path}"

        try:
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(file_text)

            return f"Successfully created file: {path}"

        except Exception as e:
            return f"Error creating file: {str(e)}"

    def handle_insert(self, path: str, insert_line: int, new_str: str) -> str:
        """
        Handle the 'insert' command to insert text at a specific line.
        """
        abs_path = self.get_absolute_path(path)

        if not os.path.isfile(abs_path):
            return f"File does not exist: {path}"

        try:
            # Create a backup of the file
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            self.file_backups[abs_path] = "".join(lines)

            # Ensure the insert_line is valid
            if insert_line < 0 or insert_line > len(lines):
                return (
                    f"Invalid line number: {insert_line}. File has {len(lines)} lines."
                )

            # Insert the new text
            lines.insert(
                insert_line, new_str + "\n" if not new_str.endswith("\n") else new_str
            )

            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            return f"Successfully inserted text after line {insert_line}."

        except Exception as e:
            return f"Error inserting text: {str(e)}"

    def handle_undo_edit(self, path: str) -> str:
        """
        Handle the 'undo_edit' command to restore a file from backup.
        """
        abs_path = self.get_absolute_path(path)

        if abs_path not in self.file_backups:
            return f"No backup found for file: {path}"

        try:
            # Restore from backup
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(self.file_backups[abs_path])

            del self.file_backups[abs_path]

            return f"Successfully restored file: {path}"

        except Exception as e:
            return f"Error restoring file: {str(e)}"

    def extract_parameter(self, params, name, default=None):
        """Safely extract a parameter from either an object or a dictionary."""
        if hasattr(params, name):
            return getattr(params, name)
        elif isinstance(params, dict) and name in params:
            return params[name]
        return default

    def handle_editor_tool(self, tool_use):
        """
        Process a text editor tool command from Claude.
        """
        try:
            # Extract input parameters safely
            if hasattr(tool_use, "input"):
                input_params = tool_use.input
            elif isinstance(tool_use, dict) and "input" in tool_use:
                input_params = tool_use["input"]
            else:
                print(f"Unexpected tool_use structure: {tool_use}")
                return "Error: Could not extract input parameters from tool use"

            # Extract command and path
            command = self.extract_parameter(input_params, "command", "")
            path = self.extract_parameter(input_params, "path", "")

            print(f"Tool command: {command}, path: {path}")
            print(f"Executing command: {command} on path: {path}")

            # Handle different commands
            if command == "view":
                view_range = self.extract_parameter(input_params, "view_range")
                return self.handle_view(path, view_range)

            elif command == "str_replace":
                old_str = self.extract_parameter(input_params, "old_str", "")
                new_str = self.extract_parameter(input_params, "new_str", "")
                print(f"str_replace: old_str={repr(old_str)}, new_str={repr(new_str)}")
                return self.handle_str_replace(path, old_str, new_str)

            elif command == "create":
                file_text = self.extract_parameter(input_params, "file_text", "")
                return self.handle_create(path, file_text)

            elif command == "insert":
                insert_line = self.extract_parameter(input_params, "insert_line", 0)
                new_str = self.extract_parameter(input_params, "new_str", "")
                return self.handle_insert(path, insert_line, new_str)

            elif command == "undo_edit":
                return self.handle_undo_edit(path)

            else:
                return f"Unknown command: {command}"

        except Exception as e:
            print(f"Error in handle_editor_tool: {str(e)}")
            traceback.print_exc()
            return f"Error processing tool command: {str(e)}"

    def chat_with_claude(self, user_message: str):
        """
        Send a message to Claude and process its response.
        """
        # Add user message to conversation history
        self.messages.append({"role": "user", "content": user_message})

        try:
            # Send initial message to Claude
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=4096,
                tools=[{"type": "text_editor_20250124", "name": "str_replace_editor"}],
                messages=self.messages,
            )

            # Process Claude's response
            print("\n--- Claude's Response ---")
            self.process_response(response)

        except Exception as e:
            print(f"Error communicating with Claude: {str(e)}")
            traceback.print_exc()

    def process_response(self, response):
        """Process a response from Claude, handling any tool uses."""
        has_tool_use = False

        # Save Claude's response to the conversation
        self.messages.append({"role": "assistant", "content": response.content})

        # Process each content block
        for content in response.content:
            if content.type == "text":
                print(content.text)

            elif content.type == "tool_use":
                has_tool_use = True

                try:
                    # Get tool name
                    tool_name = self.extract_parameter(
                        content, "name", "str_replace_editor"
                    )
                    print(f"\n[Using tool: {tool_name}]")

                    # Execute the tool
                    result = self.handle_editor_tool(content)
                    print("\n--- Tool Result ---")
                    print(result)

                    # Get tool ID
                    tool_id = self.extract_parameter(content, "id", "tool_id")

                    # Create tool result message
                    tool_result_msg = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result,
                            }
                        ],
                    }

                    # Add the tool result to the conversation
                    self.messages.append(tool_result_msg)

                    # Continue the conversation with the tool result
                    followup_response = client.messages.create(
                        model="claude-3-7-sonnet-20250219",
                        max_tokens=4096,
                        tools=[
                            {
                                "type": "text_editor_20250124",
                                "name": "str_replace_editor",
                            }
                        ],
                        messages=self.messages,
                    )

                    # Process the follow-up response (recursively)
                    print("\n--- Claude's Follow-up Response ---")
                    self.process_response(followup_response)
                    return  # Return after processing follow-up to avoid processing the same response twice

                except Exception as e:
                    print(f"Error processing tool use: {str(e)}")
                    traceback.print_exc()

                    # Add error result to conversation
                    tool_id = getattr(content, "id", "error_id")
                    error_result = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Error: {str(e)}",
                            }
                        ],
                    }
                    self.messages.append(error_result)


def main():
    """Main function to run the text editor demo."""
    parser = argparse.ArgumentParser(description="Claude Text Editor Tool Demo")
    parser.add_argument(
        "--dir", "-d", default=".", help="Working directory for file operations"
    )
    args = parser.parse_args()

    editor = TextEditorDemo(working_dir=args.dir)

    print("Welcome to the Claude Text Editor Tool Demo!")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("Working directory:", editor.working_dir)

    while True:
        user_input = input("\n> ")

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        editor.chat_with_claude(user_input)


if __name__ == "__main__":
    main()
