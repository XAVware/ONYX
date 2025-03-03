def setup_mermaid_docs(project_dir):
    """Setup proper mermaid support in the docs directory."""
    from pathlib import Path
    import os
    
    # Create javascript directory for custom scripts
    js_dir = project_dir / "docs" / "js"
    js_dir.mkdir(exist_ok=True)
    
    # Create mermaid initialization script
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
    
    # Create a direct HTML version for diagrams
    html_dir = project_dir / "docs" / "html"
    html_dir.mkdir(exist_ok=True)
    
    # Find all mermaid files
    diagrams_dir = project_dir / "planning" / "diagrams"
    if diagrams_dir.exists():
        for diagram_file in diagrams_dir.glob("*.mmd"):
            with open(diagram_file, "r") as f:
                diagram_content = f.read()
            
            # Create standalone HTML for this diagram
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
    
    # Update mkdocs.yml to include the custom JS
    mkdocs_path = project_dir / "mkdocs.yml"
    if mkdocs_path.exists():
        with open(mkdocs_path, "r") as f:
            content = f.read()
        
        # Replace the extra_javascript section
        if "extra_javascript:" in content:
            lines = content.split('\n')
            new_lines = []
            in_js_section = False
            
            for line in lines:
                if line.strip() == "extra_javascript:":
                    in_js_section = True
                    new_lines.append(line)
                    new_lines.append("  - https://unpkg.com/mermaid@9.4.3/dist/mermaid.min.js")
                    new_lines.append("  - js/mermaid-init.js")
                elif in_js_section and (line.strip().startswith("- ") or line.strip().startswith("  - ")):
                    # Skip existing JS entries
                    continue
                else:
                    in_js_section = False
                    new_lines.append(line)
            
            with open(mkdocs_path, "w") as f:
                f.write('\n'.join(new_lines))
        else:
            # Add extra_javascript section if it doesn't exist
            with open(mkdocs_path, "a") as f:
                f.write("\nextra_javascript:\n")
                f.write("  - https://unpkg.com/mermaid@9.4.3/dist/mermaid.min.js\n")
                f.write("  - js/mermaid-init.js\n")
    
    # Update index.md to include direct HTML links
    index_path = project_dir / "docs" / "index.md"
    if index_path.exists():
        with open(index_path, "r") as f:
            content = f.read()
        
        html_links = "\n\n## Direct HTML Diagrams\n\nIf the diagrams below don't render correctly, try these direct HTML versions:\n\n"
        for html_file in html_dir.glob("*.html"):
            html_links += f"- [{html_file.stem}](html/{html_file.name})\n"
        
        with open(index_path, "w") as f:
            f.write(content + html_links)
    
    print("Enhanced mermaid support configured successfully")

def build_docs(project_dir):
    """Build the mkdocs documentation."""
    try:
        import subprocess
        result = subprocess.run(
            ["mkdocs", "build"], 
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("Documentation built successfully")
            return True
        else:
            print(f"Error building documentation: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error building documentation: {str(e)}")
        return False

def serve_docs(project_dir):
    """Serve the mkdocs documentation in background mode."""
    try:
        import subprocess
        import webbrowser
        import time
        import os
        import signal
        import platform
        from rich.console import Console
        
        console = Console()
        console.print("[bold blue]Starting documentation server...[/bold blue]")
        

        # Unix-like systems (macOS, Linux)
        process = subprocess.Popen(
            ["mkdocs", "serve"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setpgrp  # This detaches the process from parent
        )
        
        # Wait briefly for server to start
        time.sleep(2)
        
        # Try to open in browser
        try:
            webbrowser.open("http://localhost:8000")
        except:
            pass  # If browser opening fails, continue anyway
        
        # Store the PID for future reference
        pid_file = project_dir / ".mkdocs_server_pid"
        with open(pid_file, "w") as f:
            f.write(str(process.pid))
        
        console.print("[green]Documentation server started in background![/green]")
        console.print("Access the documentation at [cyan]http://localhost:8000[/cyan]")
        console.print(f"Server PID: {process.pid}")
        console.print("To stop the server later, run: [cyan]kill {process.pid}[/cyan]")
        
        return True
    except Exception as e:
        console.print(f"[bold red]Error starting documentation server: {str(e)}[/bold red]")
        return False

def stop_docs_server(project_dir):
    """Stop a running mkdocs server."""
    try:
        import os
        import signal
        import platform
        from rich.console import Console
        
        console = Console()
        
        # Check for PID file
        pid_file = project_dir / ".mkdocs_server_pid"
        if not pid_file.exists():
            console.print("[yellow]No documentation server PID file found.[/yellow]")
            return False
        
        # Read PID
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
        
        # Kill process
        try:
            if platform.system() == 'Windows':
                import subprocess
                subprocess.run(["taskkill", "/F", "/PID", str(pid)])
            else:
                os.kill(pid, signal.SIGTERM)
            
            # Remove PID file
            pid_file.unlink()
            console.print("[green]Documentation server stopped.[/green]")
            return True
        except ProcessLookupError:
            console.print("[yellow]Documentation server process not found. It may have already stopped.[/yellow]")
            pid_file.unlink()
            return False
        except Exception as e:
            console.print(f"[bold red]Error stopping documentation server: {str(e)}[/bold red]")
            return False
            
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        return False
