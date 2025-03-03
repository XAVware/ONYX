"""
AppPlanningWorkflow.py - Orchestrates a planning workflow for app development

This script creates a structured planning process using three Claude personas:
1. Tech Entrepreneur - Creates a business plan and app summary
2. Agile Project Planner - Generates use cases, user stories and product backlog
3. Project Manager - Selects features for the MVP

The output of each step feeds into the next, creating a complete planning pipeline
before development begins.
"""

import logging
import csv
import time
import os
from pathlib import Path
from typing import Dict, List, Optional
import io
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from Claude import Claude
from ResultProcessor import ResultProcessor
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("appplanner")
console = Console()

class AppPlanningWorkflow:
    """Orchestrates a planning workflow for app development."""
    
    def __init__(self, 
                 project_dir: str):
        """Initialize the workflow components."""
        self.result_processor = ResultProcessor()
        # Create planning directory
        self.planning_dir = project_dir / "planning"
        self.planning_dir.mkdir(exist_ok=True)
    
    def generate_business_plan(self, app_idea: str) -> str:
        """Generate a business plan using the Tech Entrepreneur persona."""
        system_prompt = """
        You are an experienced Tech Entrepreneur with expertise in mobile app business planning.
        When given an app idea, create a comprehensive business plan including:
        
        1. Executive Summary
        2. Problem Statement
        3. Solution Overview
        4. Target Market Analysis
        5. Competitive Analysis
        6. Revenue Model
        7. Marketing Strategy
        8. Development Roadmap
        9. Key Metrics for Success
        
        Format your response in Markdown with clear sections and bullet points where appropriate.
        Be concise but thorough, focusing on practical, actionable insights.
        """
        
        prompt = f"Create a comprehensive business plan for this mobile app idea: {app_idea}"
        
        console.print("[bold blue]Generating Business Plan...[/bold blue]")
        
        tech_entrepreneur = Claude()
        response = tech_entrepreneur.send_prompt(prompt, system_prompt=system_prompt)
        return response
        
    
    def generate_user_stories(self, business_plan: str) -> str:
        """Generate user stories, use cases, and product backlog using the Agile Project Planner persona."""
        system_prompt = """
        You are an expert Agile Project Planner specializing in mobile app development.
        Based on the provided business plan, create a structured CSV list of:
        
        1. Use Cases - High-level descriptions of how users interact with the system
        2. User Stories - Specific requirements in the format "As a [role], I want [feature], so that [benefit]"
        3. Product Backlog Items - Detailed tasks that need to be implemented
        
        Format your response as a CSV with the following columns:
        Type,ID,Title,Description,Priority,Complexity,Dependencies
        
        Where:
        - Type: "Use Case", "User Story", or "Backlog Item"
        - ID: A unique identifier (e.g., UC-01, US-01, PBI-01)
        - Title: A short descriptive title
        - Description: Full description (user story format for User Stories)
        - Priority: "High", "Medium", or "Low"
        - Complexity: "High", "Medium", or "Low" 
        - Dependencies: IDs of any items this depends on, comma-separated if multiple
        
        Create at least:
        - 5-8 Use Cases
        - 12-15 User Stories
        - 20-25 Product Backlog Items
        
        Return ONLY the CSV content without additional explanations.
        """
        
        prompt = f"Create user stories, use cases, and product backlog items based on this business plan:\n\n{business_plan}"
        
        console.print("[bold blue]Generating User Stories and Backlog...[/bold blue]")
        
        agile_planner = Claude()
        response = agile_planner.send_prompt(prompt, system_prompt=system_prompt)
        return response
    
    def select_mvp_features(self, backlog_csv: str, business_plan: str) -> str:
        """Select MVP features using the Project Manager persona."""
        system_prompt = """
        You are an experienced Project Manager specializing in mobile app development.
        Based on the provided business plan and product backlog, identify the features 
        that should be included in the Minimum Viable Product (MVP).
        
        Your task is to:
        1. Analyze the business plan to understand core value propositions
        2. Review the backlog to identify high-priority, low-complexity items
        3. Select a coherent set of features that deliver core value while minimizing development time
        4. Provide a clear rationale for your selections
        
        Format your response in Markdown with:
        1. MVP Overview (1-2 paragraphs)
        2. Selected Features list (include ID and Title from the backlog)
        3. Implementation Timeline estimate
        4. Key Metrics for MVP Success
        5. Rationale for Selections
        """
        
        prompt = f"""
        Select the features for a Minimum Viable Product (MVP) based on this business plan and product backlog.
        
        Business Plan:
        {business_plan}
        
        Product Backlog (CSV):
        {backlog_csv}
        """
        
        console.print("[bold blue]Selecting MVP Features...[/bold blue]")
        
        project_manager = Claude()
        response = project_manager.send_prompt(prompt, system_prompt=system_prompt)
        return response
    
    def run_workflow(self, app_idea: str) -> Dict[str, str]:
        """Run the complete app planning workflow, skipping steps if files already exist."""
        console.print(f"[bold]Starting App Planning Workflow for:[/bold] {app_idea}")
        
        # Define file paths
        business_plan_path = self.planning_dir / "Business_Plan.md"
        backlog_path = self.planning_dir / "Agile_Planner.md"
        mvp_path = self.planning_dir / "MVP.md"
        
        # Step 1: Generate or load Business Plan
        if business_plan_path.exists():
            console.print(f"[yellow]Business Plan already exists at [/yellow][cyan]{business_plan_path}[/cyan]")
            console.print("[yellow]Loading existing Business Plan...[/yellow]")
            with open(business_plan_path, "r", encoding="utf-8") as file:
                business_plan = file.read()
        else:
            business_plan = self.generate_business_plan(app_idea)
            if not business_plan:
                return {"success": False, "error": "Failed to generate business plan"}
            
            with open(business_plan_path, "w", encoding="utf-8") as file:
                file.write(business_plan)

        console.print(Panel(
            Markdown(business_plan),
            title="Business Plan",
            border_style="green"
        ))

        # Step 2: Generate or load User Stories and Backlog
        if backlog_path.exists():
            console.print(f"[yellow]Product Backlog already exists at [/yellow][cyan]{backlog_path}[/cyan]")
            console.print("[yellow]Loading existing Product Backlog...[/yellow]")
            with open(backlog_path, "r", encoding="utf-8") as file:
                backlog_csv = file.read()
        else:
            console.print("[bold blue]Generating User Stories and Backlog...[/bold blue]")
            backlog_csv = self.generate_user_stories(business_plan)
            if not backlog_csv:
                return {"success": False, "error": "Failed to generate user stories and backlog"}
            
            with open(backlog_path, "w", encoding="utf-8") as file:
                file.write(backlog_csv)
            
            # Try to parse the CSV to show a summary (only if generating new)
            try:
                csv_data = backlog_csv
                csv_reader = csv.DictReader(io.StringIO(csv_data))
                rows = list(csv_reader)
                
                use_cases = [r for r in rows if r["Type"] == "Use Case"]
                user_stories = [r for r in rows if r["Type"] == "User Story"]
                backlog_items = [r for r in rows if r["Type"] == "Backlog Item"]
                
                console.print(f"[green]Generated {len(use_cases)} Use Cases, {len(user_stories)} User Stories, and {len(backlog_items)} Backlog Items[/green]")
            except Exception as e:
                console.print(f"[yellow]Could not parse CSV: {str(e)}[/yellow]")

        console.print(f"[green]Product Backlog available at [/green][cyan]{backlog_path}[/cyan]")

        # Step 3: Select or load MVP Features
        if mvp_path.exists():
            console.print(f"[yellow]MVP Plan already exists at [/yellow][cyan]{mvp_path}[/cyan]")
            console.print("[yellow]Loading existing MVP Plan...[/yellow]")
            with open(mvp_path, "r", encoding="utf-8") as file:
                mvp_plan = file.read()
        else:
            console.print("[bold blue]Selecting MVP Features...[/bold blue]")
            mvp_plan = self.select_mvp_features(backlog_csv, business_plan)
            if not mvp_plan:
                return {"success": False, "error": "Failed to select MVP features"}
            
            with open(mvp_path, "w", encoding="utf-8") as file:
                file.write(mvp_plan)

        console.print(f"[green]MVP Plan available at [/green][cyan]{mvp_path}[/cyan]")
        
        console.print(Panel(
            Markdown(mvp_plan),
            title="MVP Feature Selection",
            border_style="green"
        ))
        
        # Return the complete workflow results
        return {
            "success": True,
            "business_plan": business_plan_path,
            "backlog_csv": backlog_path,
            "mvp_plan": mvp_path
        }

def main():
    """Main function to run the workflow from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="App Planning Workflow")
    parser.add_argument("app_idea", nargs="?", help="The app idea to plan")
    args = parser.parse_args()
    
    workflow = AppPlanningWorkflow(project_dir='/ONYX/Projects/Test')
    
    if not args.app_idea:
        console.print("[bold yellow]Please provide an app idea.[/bold yellow]")
        app_idea = input("Enter your app idea: ")
    else:
        app_idea = args.app_idea
    
    result = workflow.run_workflow(app_idea)

    print(result)
    if result["success"]:
        console.print("[bold green]Workflow completed successfully![/bold green]")
        console.print("You can now proceed with development using the MVP plan.")

    else:
        console.print(f"[bold red]Workflow failed: {result['error']}[/bold red]")

if __name__ == "__main__":
    main()
