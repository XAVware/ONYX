"""Utility for building Xcode projects and processing build output."""

import subprocess
from pathlib import Path
from typing import List
from dataclasses import dataclass
import re
import json

@dataclass
class BuildMessage:
    """The message returned from the build."""
    type: str
    file: str
    line: int
    message: str

    def to_dict(self) -> dict:
        """Convert the BuildMessage to a JSON-serializable dictionary"""
        return {
            "type": self.type,
            "file": self.file,
            "line": self.line,
            "message": self.message
        }

@dataclass
class BuildOutput:
    """The output returned from the build."""
    result: str
    messages: List[BuildMessage]
    raw_output: str

class XcodeBuilder:
    """Coordinates the build execution and response log."""
    def __init__(self, project_path: str):
        """
        Initialize XcodeBuilder with project path
        """
        self.project_path = Path(project_path)
        # Find project
        xcodeproj_files = list(self.project_path.glob("*.xcodeproj"))
        if not xcodeproj_files:
            raise ValueError(f"No .xcodeproj file found in {project_path}")
        self.xcodeproj = xcodeproj_files[0]
        self.project_name = self.xcodeproj.stem

    def _parse_build_messages(self, output: str)->List[BuildMessage]:
        """Parse build output for warnings and errors"""
        messages = []
        # Split output into lines and process each line
        lines = output.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if ': error:' in line or ': warning:' in line:
                # Try to parse the standard Xcode format
                match = re.match(r'(.*?):(\d+)(?::\d+)?: (warning|error): (.*)', line)

                if match:
                    file_path, line_num, msg_type, msg = match.groups()
                    try:
                        line_num = int(line_num)
                    except ValueError:
                        line_num = 0

                    # Get additional context from following lines
                    context = []
                    j = i + 1
                    while j < len(lines) and not (
                        ': error:' in lines[j] or ': warning:' in lines[j]):
                        if lines[j].strip():
                            context.append(lines[j].strip())
                        j += 1
                        if len(context) >= 3:  # Limit context to 3 lines
                            break

                    full_message = f"{msg}\nContext:\n" + "\n".join(context) if context else msg
                    messages.append(BuildMessage(
                        type=msg_type,
                        file=file_path,
                        line=line_num,
                        message=full_message
                    ))

                else:
                    # If we can't parse the standard format, just capture the whole message
                    messages.append(BuildMessage(
                        type="error" if ": error:" in line else "warning",
                        file="unknown",
                        line=0,
                        message=line
                    ))
            i += 1
        return messages

    def build(self, configuration: str = "Debug",
              destination: str = "platform=iOS Simulator,name=iPhone 16 Pro",
              clean: bool = True) -> BuildOutput:
        """
        Build the Xcode project
        """
        # Construct xcodebuild command
        cmd = [
            "xcodebuild",
            "-project", str(self.xcodeproj),
            "-scheme", self.project_name,
            "-configuration", configuration,
            "-destination", destination
        ]
        if clean:
            cmd.extend(["clean", "build"])
        else:
            cmd.append("build")

        print(f"Starting build with command: {' '.join(cmd)}")

        # Run xcodebuild
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.project_path),
            check=False
        )
        # Combine output and error streams
        combined_output = f"{result.stdout}\n{result.stderr}".strip()

        # Parse build messages
        messages = self._parse_build_messages(combined_output)

        # Determine build result
        if result.returncode == 0:
            build_result = "SUCCESS"
        else:
            build_result = "FAILURE"
            # If no error messages were parsed but build failed, add a generic error
            if not any(msg.type == "error" for msg in messages):
                messages.append(BuildMessage(
                    type="error",
                    file="",
                    line=0,
                    message="Build failed with no error message. Check raw output for details."
                ))

        return BuildOutput(
            result=build_result,
            messages=messages,
            raw_output=combined_output
        )