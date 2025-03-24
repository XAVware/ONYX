import subprocess
import webbrowser
import time
import os
import shutil
from pathlib import Path
from rich.console import Console
import signal
from onyx import get_logger

logger = get_logger(__name__)


def check_mkdocs_installed():
    """Check if mkdocs is installed and available."""
    try:
        # Check if mkdocs is in PATH
        if shutil.which("mkdocs") is None:
            return False

        # Verify it can be executed
        result = subprocess.run(["mkdocs", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def ensure_mkdocs_config(project_dir):
    """Ensure mkdocs.yml exists in the project directory."""
    mkdocs_path = project_dir / "mkdocs.yml"

    if not mkdocs_path.exists():
        logger.info("Creating default mkdocs.yml configuration...")

        default_config = """site_name: Project Documentation
site_description: Documentation for the project
docs_dir: docs
theme: readthedocs

nav:
  - Home: index.md

plugins:
  - search

markdown_extensions:
  - toc:
      permalink: true
  - admonition
  - pymdownx.highlight
  - pymdownx.superfences

extra_javascript:
  - https://unpkg.com/mermaid@9.4.3/dist/mermaid.min.js
  - js/mermaid-init.js
"""
        with open(mkdocs_path, "w") as f:
            f.write(default_config)

        # Create default index.md if it doesn't exist
        docs_dir = project_dir / "docs"
        docs_dir.mkdir(exist_ok=True)

        index_path = docs_dir / "index.md"
        if not index_path.exists():
            with open(index_path, "w") as f:
                f.write(
                    "# Project Documentation\n\nWelcome to the project documentation.\n\n## Diagrams\n\n"
                )


def setup_mermaid_docs(project_dir: Path):
    """Setup proper mermaid support in the docs directory."""

    # Ensure project_dir is a Path object
    # project_dir = Path(project_dir)

    # Make sure mkdocs configuration exists
    ensure_mkdocs_config(project_dir)

    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    js_dir = docs_dir / "js"
    js_dir.mkdir(exist_ok=True)

    mermaid_js = """
    document.addEventListener('DOMContentLoaded', function() {
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: { useMaxWidth: false, htmlLabels: true }
        });
        
        // Force render after page loads
        setTimeout(function() {
            mermaid.init(undefined, '.mermaid');
        }, 500);
    });
    """

    with open(js_dir / "mermaid-init.js", "w") as f:
        f.write(mermaid_js)

    html_dir = docs_dir / "html"
    html_dir.mkdir(exist_ok=True)

    diagrams_dir = project_dir / "planning" / "diagrams"
    if diagrams_dir.exists():
        for diagram_file in diagrams_dir.glob("*.mmd"):
            with open(diagram_file, "r") as f:
                diagram_content = f.read()

            html_content = f"""<!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{diagram_file.stem}</title>
                <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                <script>
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'default',
                        securityLevel: 'loose',
                        flowchart: {{ useMaxWidth: false, htmlLabels: true }}
                    }});
                </script>
                <style>
                    body {{ margin: 20px; font-family: Arial, sans-serif; }}
                    .diagram-container {{ margin: 20px auto; max-width: 1000px; }}
                </style>
            </head>
            <body>
                <h1>{diagram_file.stem}</h1>
                <div class="diagram-container">
                    <div class="mermaid">
            {diagram_content}
                    </div>
                </div>
            </body>
            </html>"""

            with open(html_dir / f"{diagram_file.stem}.html", "w") as f:
                f.write(html_content)

    # Now append mermaid diagrams to index.md
    index_path = docs_dir / "index.md"
    if index_path.exists():
        # Check if content already contains diagrams section
        with open(index_path, "r") as f:
            content = f.read()

        # Add diagrams from planning directory to index.md
        diagrams_section = "\n\n## Mermaid Diagrams\n\n"
        has_diagrams = False

        if diagrams_dir.exists():
            for diagram_file in diagrams_dir.glob("*.mmd"):
                with open(diagram_file, "r") as f:
                    diagram_content = f.read()

                diagrams_section += f"### {diagram_file.stem}\n\n"
                diagrams_section += "```mermaid\n"
                diagrams_section += diagram_content + "\n"
                diagrams_section += "```\n\n"
                has_diagrams = True

        # Only add diagrams section if it doesn't already exist and we have diagrams
        if "## Mermaid Diagrams" not in content and has_diagrams:
            with open(index_path, "a") as f:
                f.write(diagrams_section)

        # Add HTML links section
        html_links = "\n\n## Direct HTML Diagrams\n\nIf the diagrams below don't render correctly, try these direct HTML versions:\n\n"
        has_html_files = False

        for html_file in html_dir.glob("*.html"):
            html_links += f"- [{html_file.stem}](html/{html_file.name})\n"
            has_html_files = True

        if "## Direct HTML Diagrams" not in content and has_html_files:
            with open(index_path, "a") as f:
                f.write(html_links)

    logger.info("Enhanced mermaid support configured successfully")


def build_docs(project_dir):
    """Build the mkdocs documentation."""
    project_dir = Path(project_dir)

    if not check_mkdocs_installed():
        logger.error(
            "mkdocs is not installed. Please install it with 'pip install mkdocs'"
        )
        return False

    # Ensure mkdocs config exists
    ensure_mkdocs_config(project_dir)

    try:
        result = subprocess.run(
            ["mkdocs", "build"], cwd=project_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("Documentation built successfully")
            return True
        else:
            logger.error(f"Error building documentation: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error building documentation: {str(e)}")
        return False


def serve_docs(project_dir: Path):
    """Serve the mkdocs documentation in background mode."""
    console = Console()
    # project_dir = Path(project_dir)

    # First, check if mkdocs is installed
    if not check_mkdocs_installed():
        console.print("[bold red]Error: mkdocs is not installed![/bold red]")
        console.print("Please install mkdocs using: [cyan]pip install mkdocs[/cyan]")
        console.print("HTML versions of diagrams are still available in docs/html/")

        # Open the HTML directory directly instead
        html_dir = project_dir / "docs" / "html"
        if html_dir.exists() and any(html_dir.glob("*.html")):
            first_html = next(html_dir.glob("*.html"))
            try:
                webbrowser.open(f"file://{first_html.absolute()}")
                console.print(f"[green]Opened HTML diagram: {first_html.name}[/green]")
            except Exception as e:
                logger.error(f"Error opening HTML file: {str(e)}")

        return False

    # Ensure mkdocs config exists
    ensure_mkdocs_config(project_dir)

    try:
        console.print("[bold blue]Starting documentation server...[/bold blue]")

        process = subprocess.Popen(
            ["mkdocs", "serve"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setpgrp,
        )

        # Check if process started successfully by waiting briefly and checking returncode
        time.sleep(1)
        if process.poll() is not None:
            stderr = (
                process.stderr.read().decode("utf-8")
                if process.stderr
                else "Unknown error"
            )
            console.print(
                f"[bold red]Error starting mkdocs server: {stderr}[/bold red]"
            )

            # Fallback to opening HTML files directly
            html_dir = project_dir / "docs" / "html"
            if html_dir.exists() and any(html_dir.glob("*.html")):
                first_html = next(html_dir.glob("*.html"))
                try:
                    webbrowser.open(f"file://{first_html.absolute()}")
                    console.print(
                        f"[green]Opened HTML diagram: {first_html.name}[/green]"
                    )
                except Exception as e:
                    logger.error(f"Error opening HTML file: {str(e)}")

            return False

        time.sleep(1)  # Give the server a bit more time to start up

        try:
            webbrowser.open("http://localhost:8000")
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")
            pass  # If browser opening fails, continue anyway

        pid_file = project_dir / ".mkdocs_server_pid"
        with open(pid_file, "w") as f:
            f.write(str(process.pid))

        console.print("[green]Documentation server started in background![/green]")
        console.print("Access the documentation at [cyan]http://localhost:8000[/cyan]")
        console.print(f"Server PID: {process.pid}")
        console.print("To stop the server later, run: [cyan]kill {process.pid}[/cyan]")

        return True
    except FileNotFoundError:
        console.print("[bold red]Error: mkdocs command not found![/bold red]")
        console.print("Please install mkdocs using: [cyan]pip install mkdocs[/cyan]")
        return False
    except Exception as e:
        console.print(
            f"[bold red]Error starting documentation server: {str(e)}[/bold red]"
        )

        # Fallback to opening HTML files directly
        html_dir = project_dir / "docs" / "html"
        if html_dir.exists() and any(html_dir.glob("*.html")):
            first_html = next(html_dir.glob("*.html"))
            try:
                webbrowser.open(f"file://{first_html.absolute()}")
                console.print(f"[green]Opened HTML diagram: {first_html.name}[/green]")
            except Exception as browser_e:
                logger.error(f"Error opening HTML file: {str(browser_e)}")

        return False


def stop_docs_server(project_dir):
    """Stop a running mkdocs server."""
    try:
        console = Console()
        pid_file = project_dir / ".mkdocs_server_pid"
        if not pid_file.exists():
            console.print("[yellow]No documentation server PID file found.[/yellow]")
            return False

        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        try:
            os.kill(pid, signal.SIGTERM)
            pid_file.unlink()
            console.print("[green]Documentation server stopped.[/green]")
            return True
        except ProcessLookupError:
            console.print(
                "[yellow]Documentation server process not found. It may have already stopped.[/yellow]"
            )
            pid_file.unlink()
            return False
        except Exception as e:
            console.print(
                f"[bold red]Error stopping documentation server: {str(e)}[/bold red]"
            )
            return False

    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        return False
