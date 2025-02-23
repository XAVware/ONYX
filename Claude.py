import os
import anthropic
import json
from dotenv import load_dotenv

class ClaudeProject:
    client: anthropic.Anthropic
    def __init__(self, project_name):
        load_dotenv()
        API_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.project_name = project_name
        self.client = anthropic.Anthropic(api_key=API_KEY)
        self.instructions = ""
        self.files = []
        self.chat_history = []
    
    def set_instructions(self, instructions):
        """Set global project instructions."""
        self.instructions = instructions

    def upload_file(self, file_path):
        """Simulate file upload by storing its contents."""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        
        with open(file_path, "r") as file:
            content = file.read()
        
        self.files.append({"filename": os.path.basename(file_path), "content": content})
        print(f"Uploaded: {file_path}")

    def get_file_content(self):
        return "\n".join([f"### {f['filename']} ###\n{f['content']}" for f in self.files])

    def send_message(self, user_message):
        """Send a message to Claude with project context."""
        context_messages = [
            {"role": "user", "content": user_message}
        ]

        systemPrompt = self.instructions

        # If files have been uploaded, append the file content to the system prompt
        if self.files:
            file_content = self.get_file_content()
            systemPrompt = systemPrompt + "\nHere are the project files:\n" + file_content
        

        # Add chat history (up to last 5 messages for context)
        context_messages.extend(self.chat_history[-5:])

        # Call Anthropic API
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=context_messages,
            max_tokens=4096,
            temperature=0.0,
            system=systemPrompt
        )

        assistant_message = response.content[0].text
        print(f"Claude: {assistant_message}")

        return assistant_message
    
    def add_to_chat_history(self, user_message, assistant_response):
        self.chat_history.append({"role": "user", "content": user_message})
        self.chat_history.append({"role": "assistant", "content": assistant_response})
        print("Chat history updated.")
        # Print each message in the history
        for history in self.chat_history:
            print(f"{history['role']}: {history['content']}")

    def get_history(self):
        return "\n".join(f"{msg['role']}: {msg['content']}" for msg in self.chat_history)

if __name__ == "__main__":
    project = ClaudeProject("My AI Project")

    # Set persistent project instructions
    project.set_instructions("You are an AI assistant helping with a Python project.")

    # Upload multiple project files
    project.upload_file("Claude.py")

    prompt = "The 'add history' functionality isn't working. How can I fix it?"

    # Chat with Claude within the project scope
    response = project.send_message(prompt)

    # Append to chat history
    project.add_to_chat_history(user_message=prompt, assistant_response=response)
    project.get_history()

