
# import csv
# from typing import Dict
# import io

# from onyx.ai_task import Claude
# from prompt_loader import get_system_prompt, format_prompt
# from onyx import get_logger, print_fancy

# logger = get_logger(__name__)


# class AppPlanningWorkflow:
#     """Orchestrates a planning workflow for app development."""

#     def __init__(self, project_dir: str):
#         """Initialize the workflow components."""
#         # self.result_processor = ResultProcessor()
#         self.planning_dir = project_dir / "planning"
#         self.planning_dir.mkdir(exist_ok=True)



#     # def generate_user_stories(self, business_plan: str) -> str:
#     #     """Generate user stories, use cases, and product backlog using the Agile Project Planner persona."""
#     #     system_prompt = get_system_prompt("project_manager", "user_stories")
#     #     prompt = format_prompt(
#     #         "project_manager", "user_stories", business_plan=business_plan
#     #     )
#     #     agile_planner = Claude()
#     #     response = agile_planner.send_prompt(prompt, system_prompt=system_prompt)
#     #     return response

#     def select_mvp_features(self, backlog_csv: str, business_plan: str) -> str:
#         """Select MVP features using the Project Manager persona."""
#         system_prompt = get_system_prompt("project_manager", "mvp")
#         prompt = format_prompt(
#             "project_manager",
#             "mvp",
#             business_plan=business_plan,
#             backlog_csv=backlog_csv,
#         )

#         logger.info("Selecting MVP Features...")
#         project_manager = Claude()
#         response = project_manager.send_prompt(prompt, system_prompt=system_prompt)
#         return response

#     def run_workflow(self, app_idea: str, app_name: str) -> Dict[str, str]:
#         """Run the complete app planning workflow, skipping steps if files already exist."""
#         logger.info(f"Starting App Planning Workflow for: {app_idea}")

#         business_plan_path = self.planning_dir / "Business_Plan.md"
#         backlog_path = self.planning_dir / "Agile_Planner.md"
#         mvp_path = self.planning_dir / "MVP.md"

#         # Step 1: Generate or load Business Plan
#         if business_plan_path.exists():
#             print_fancy(
#                 f"Business Plan already exists at {business_plan_path}",
#                 style="yellow",
#             )
#             print_fancy("Loading existing Business Plan...", style="yellow")
#             with open(business_plan_path, "r", encoding="utf-8") as file:
#                 business_plan = file.read()
#         else:
#             business_plan = self.generate_business_plan(app_idea, app_name)
#             if not business_plan:
#                 return {"success": False, "error": "Failed to generate business plan"}

#             with open(business_plan_path, "w", encoding="utf-8") as file:
#                 file.write(business_plan)

#         # Step 2: Generate or load User Stories and Backlog
#         if backlog_path.exists():
#             print_fancy(
#                 f"Product Backlog already exists at [cyan]{backlog_path}[/cyan]",
#                 style="yellow",
#             )
#             print_fancy("Loading existing Product Backlog...", style="yellow")
#             with open(backlog_path, "r", encoding="utf-8") as file:
#                 backlog_csv = file.read()
#         else:
#             logger.info("Generating User Stories and Backlog...")
#             backlog_csv = self.generate_user_stories(business_plan)
#             if not backlog_csv:
#                 return {
#                     "success": False,
#                     "error": "Failed to generate user stories and backlog",
#                 }

#             with open(backlog_path, "w", encoding="utf-8") as file:
#                 file.write(backlog_csv)

#             # try:
#             #     csv_data = backlog_csv
#             #     csv_reader = csv.DictReader(io.StringIO(csv_data))
#             #     rows = list(csv_reader)

#             #     use_cases = [r for r in rows if r["Type"] == "Use Case"]
#             #     user_stories = [r for r in rows if r["Type"] == "User Story"]
#             #     backlog_items = [r for r in rows if r["Type"] == "Backlog Item"]
#             #     logger.info(
#             #         f"Generated {len(use_cases)} Use Cases, {len(user_stories)} User Stories, and {len(backlog_items)} Backlog Items"
#             #     )
#             # except Exception as e:
#             #     logger.warning(f"Could not parse CSV: {str(e)}")

#         logger.info(f"Product Backlog available at [cyan]{backlog_path}[/cyan]")

#         # Step 3: Select or load MVP Features
#         if mvp_path.exists():
#             print_fancy(
#                 f"MVP Plan already exists at [cyan]{mvp_path}[/cyan]",
#                 style="yellow",
#             )
#             logger.info("Loading existing MVP Plan...")
#             with open(mvp_path, "r", encoding="utf-8") as file:
#                 mvp_plan = file.read()
#         else:
#             logger.info("Selecting MVP Features...")
#             mvp_plan = self.select_mvp_features(backlog_csv, business_plan)
#             if not mvp_plan:
#                 return {"success": False, "error": "Failed to select MVP features"}

#             with open(mvp_path, "w", encoding="utf-8") as file:
#                 file.write(mvp_plan)

#         logger.info(f"MVP Plan available at [cyan]{mvp_path}[/cyan]")

#         return {
#             "success": True,
#             "business_plan": business_plan_path,
#             "backlog_csv": backlog_path,
#             "mvp_plan": mvp_path,
#         }


# # def main():
# #     """Main function to run the workflow from command line."""
# #     import argparse

# #     parser = argparse.ArgumentParser(description="App Planning Workflow")
# #     parser.add_argument("app_idea", nargs="?", help="The app idea to plan")
# #     args = parser.parse_args()

# #     workflow = AppPlanningWorkflow(project_dir="/ONYX/Projects/Test")

# #     if not args.app_idea:
# #         print_fancy("Please provide an app idea.", style="yellow")
# #         app_idea = input("Enter your app idea: ")
# #     else:
# #         app_idea = args.app_idea

# #     result = workflow.run_workflow(app_idea)

# #     print(result)
# #     if result["success"]:
# #         logger.info("Workflow completed successfully!")
# #         logger.info("You can now proceed with development using the MVP plan.")

# #     else:
# #         logger.error(f"Workflow failed: {result['error']}")


# # if __name__ == "__main__":
# #     main()
