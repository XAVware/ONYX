import shutil
from pathlib import Path
import subprocess
import re
from dataclasses import dataclass
from typing import List
from onyx import get_logger, config

logger = get_logger(__name__)

DEVELOPMENT_TEAM_ID = config.xcode.development_team_id
BUNDLE_ID_PREFIX = config.xcode.bundle_id_prefix
TEMPLATE_PATH = Path(config.xcode.project_template_path)

@dataclass
class BuildMessage:
    type: str
    file: str
    line: int
    message: str
    context: str = ""


def parse_build_messages(output: str) -> List[BuildMessage]:
    messages = []
    lines = output.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if ": error:" in line or ": warning:" in line:
            match = re.match(r"(.*?):(\d+)(?::\d+)?: (warning|error): (.*)", line)
            if match:
                file_path, line_num, msg_type, msg = match.groups()
                try:
                    line_num = int(line_num)
                except ValueError:
                    line_num = 0
                context = []
                j = i + 1
                while j < len(lines) and not (
                    ": error:" in lines[j] or ": warning:" in lines[j]
                ):
                    if lines[j].strip():
                        context.append(lines[j].strip())
                    j += 1
                    if len(context) >= 3:
                        break
                messages.append(
                    BuildMessage(
                        type=msg_type,
                        file=file_path,
                        line=line_num,
                        message=msg,
                        context="\n".join(context) if context else "",
                    )
                )
            else:
                messages.append(
                    BuildMessage(
                        type="error" if ": error:" in line else "warning",
                        file="unknown",
                        line=0,
                        message=line,
                        context="",
                    )
                )
        i += 1
    return messages


def build_xcode_project(
    project_dir: Path,
    configuration: str = "Debug",
    destination: str = "platform=iOS Simulator,name=iPhone 16 Pro",
    clean: bool = True,
    ignore_warnings: bool = False

) -> List[BuildMessage]:
    """Build the Xcode project"""
    xcodeproj_files = list(project_dir.glob("*.xcodeproj"))
    if not xcodeproj_files:
        raise ValueError(f"No .xcodeproj file found in {project_dir}")

    project_name = project_dir.name

    cmd = [
        "xcodebuild",
        "-project",
        str(xcodeproj_files[0]),
        "-scheme",
        project_name,
        "-configuration",
        configuration,
        "-destination",
        destination,
    ]

    if clean:
        cmd.extend(["clean", "build"])
    else:
        cmd.append("build")

    logger.info(f"Starting build with command: {' '.join(cmd)}")

    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        cwd=str(project_dir), 
        check=False
    )

    combined_output = f"{result.stdout}\n{result.stderr}".strip()

    messages = parse_build_messages(combined_output)
    if ignore_warnings:
        messages = [msg for msg in messages if msg.type != "warning"]

    return messages


def copy_template_xcode_project(project_dir: Path):
    """Copy the Xcode project template and rename necessary files."""
    project_name = project_dir.name
    if not TEMPLATE_PATH.exists():
        logger.error(f"Template Xcode project not found at {TEMPLATE_PATH}")
        exit(1)

    logger.info("Copying template Xcode project...")

    shutil.copytree(TEMPLATE_PATH, project_dir, dirs_exist_ok=True)

    # Rename everything
    old_xcodeproj = project_dir / "XCodeProjectTemplate.xcodeproj"
    new_xcodeproj = project_dir / f"{project_name}.xcodeproj"
    if old_xcodeproj.exists():
        old_xcodeproj.rename(new_xcodeproj)

    old_source_dir = project_dir / "XCodeProjectTemplate"
    new_source_dir = project_dir / project_name
    if old_source_dir.exists():
        old_source_dir.rename(new_source_dir)

    old_tests_dir = project_dir / "XCodeProjectTemplateTests"
    new_tests_dir = project_dir / f"{project_name}Tests"
    if old_tests_dir.exists():
        old_tests_dir.rename(new_tests_dir)

    old_ui_tests_dir = project_dir / "XCodeProjectTemplateUITests"
    new_ui_tests_dir = project_dir / f"{project_name}UITests"
    if old_ui_tests_dir.exists():
        old_ui_tests_dir.rename(new_ui_tests_dir)

    rename_tests_and_models(project_dir, project_name)
    update_project_settings(project_dir, project_name)
    update_project_name_in_files(project_dir, project_name)

    logger.info(f"Xcode project successfully copied and renamed at: {new_xcodeproj}")


def update_project_settings(project_dir, project_name):
    """Modify the project files to reflect the new app name."""
    pbxproj_path = project_dir / f"{project_name}.xcodeproj" / "project.pbxproj"

    if not pbxproj_path.exists():
        logger.error(f"Could not find {pbxproj_path} to update settings.")
        return

    with open(pbxproj_path, "r") as file:
        content = file.read()

    content = content.replace("XCodeProjectTemplate", project_name)
    content = content.replace(
        "com.xavware.XCodeProjectTemplate", f"{BUNDLE_ID_PREFIX}.{project_name}"
    )

    with open(pbxproj_path, "w") as file:
        file.write(content)

    logger.info("Updated project settings in project.pbxproj")

def rename_tests_and_models(project_dir, project_name):
    """Rename test files and SwiftData model to match the new app name."""
    tests_dir = project_dir / f"{project_name}Tests"
    ui_tests_dir = project_dir / f"{project_name}UITests"
    model_dir = (
        project_dir / project_name
    )

    old_test_file = tests_dir / "XCodeProjectTemplateTests.swift"
    new_test_file = tests_dir / f"{project_name}Tests.swift"
    if old_test_file.exists():
        old_test_file.rename(new_test_file)
        update_file_content(
            new_test_file, "XCodeProjectTemplateTests", f"{project_name}Tests"
        )

    old_ui_test_file = ui_tests_dir / "XCodeProjectTemplateUITests.swift"
    new_ui_test_file = ui_tests_dir / f"{project_name}UITests.swift"
    if old_ui_test_file.exists():
        old_ui_test_file.rename(new_ui_test_file)
        update_file_content(
            new_ui_test_file, "XCodeProjectTemplateUITests", f"{project_name}UITests"
        )

    old_model_file = model_dir / "XCodeProjectTemplateModel.swift"
    new_model_file = model_dir / f"{project_name}Model.swift"
    if old_model_file.exists():
        old_model_file.rename(new_model_file)
        update_file_content(
            new_model_file, "XCodeProjectTemplateModel", f"{project_name}Model"
        )

    logger.info("Renamed test files and SwiftData model.")


def update_file_content(file_path, old_text, new_text):
    """Replace occurrences of old text with new text in a given file."""
    if not file_path.exists():
        return

    with open(file_path, "r") as file:
        content = file.read()

    content = content.replace(old_text, new_text)

    with open(file_path, "w") as file:
        file.write(content)


def update_project_name_in_files(project_dir, project_name):
    """Replace project name in file comments inside Swift files."""
    for swift_file in project_dir.rglob("*.swift"):
        update_file_content(swift_file, "XCodeProjectTemplate", project_name)

    logger.info("Updated project name in Swift file comments.")


def rename_entry_point(project_dir, project_name):
    """Rename the SwiftUI entry point file and class name."""
    sources_dir = project_dir / project_name
    old_entry_point = sources_dir / "XCodeProjectTemplateApp.swift"
    new_entry_point = sources_dir / f"{project_name}App.swift"

    if old_entry_point.exists():
        old_entry_point.rename(new_entry_point)
        update_file_content(
            new_entry_point, "XCodeProjectTemplateApp", f"{project_name}App"
        )

        logger.info(f"Renamed entry point file to {new_entry_point}")


def setup_xcode_project(project_dir: Path):
    """Set up the Xcode project with the given name at the specified directory."""
    logger.info("Setting up Xcode project...")
    project_name = project_dir.name
    try:
        xcodeproj_path = project_dir / f"{project_name}.xcodeproj"
        if xcodeproj_path.exists():
            logger.info(
                f"Xcode project already exists at {xcodeproj_path}. Reusing existing project."
            )
            return project_dir

        try:
            copy_template_xcode_project(project_dir)
        except Exception as e:
            logger.error(f"Error copying template: {str(e)}")
            return None

        rename_entry_point(project_dir, project_name)
        # ensure_project_scheme(project_dir, project_name)

        return project_dir
    except Exception as e:
        logger.error(f"Error setting up Xcode project: {str(e)}")
        return None


def create_project(app_dir: Path, build: bool = True):
    """Create a new Xcode project with the given name at the specified directory."""
    # project_dir = Path(app_dir)
    result_dir = setup_xcode_project(app_dir)

    if result_dir and build:
        logger.info("Building the project...")
        result = build_xcode_project(app_dir)
        if not any(msg.type == "error" for msg in result):
            logger.info(f"Project setup and build completed successfully at: {app_dir}")
            return True
        else:
            logger.error("Project setup completed with errors.")
            return False
    return result_dir is not None


if __name__ == "__main__":
    project_name = input("Enter the name of your project: ").strip()
    project_dir = Path.home() / "ONYX" / "Projects" / project_name
    create_project(project_dir, project_name, build=True)
