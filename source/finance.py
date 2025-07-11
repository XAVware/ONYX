#!/usr/bin/env python3

import argparse
import glob
import sys
from pathlib import Path
from typing import List, Optional

# Add the parent directory to the path so we can import onyx modules
script_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(script_dir))
# Also add the onyx directory itself for relative imports
sys.path.append(str(script_dir / "onyx"))

from onyx.ai_task import Claude
from onyx.prompt_loader import get_prompt_and_system
from onyx import get_logger, print_fancy

logger = get_logger(__name__)

def parse_arguments():
    """Parse command-line arguments for financial planning tool."""
    parser = argparse.ArgumentParser(
        description="Generate financial plans and speculations based on business plans and project information"
    )
    parser.add_argument(
        "files", 
        nargs="*", 
        help="File names or paths to include in financial analysis (business plans, project info, etc.)"
    )
    parser.add_argument(
        "--output", 
        "-o", 
        help="Output file path (default: financial_plan.md)"
    )
    parser.add_argument(
        "--root-dir", 
        "-r", 
        help="Root directory to search for files (default: current directory)"
    )
    return parser.parse_args()

def find_files_in_directory(file_names: List[str], root_dir: Path) -> List[Path]:
    """Find files in the root directory by name."""
    found_files = []
    
    for file_name in file_names:
        # If it's already a path, use it directly
        if "/" in file_name or "\\" in file_name:
            file_path = Path(file_name)
            if file_path.is_absolute():
                if file_path.exists():
                    found_files.append(file_path)
                else:
                    logger.warning(f"File not found: {file_path}")
            else:
                # Relative path
                full_path = root_dir / file_path
                if full_path.exists():
                    found_files.append(full_path)
                else:
                    logger.warning(f"File not found: {full_path}")
        else:
            # Search for the file in the root directory
            search_pattern = f"**/{file_name}"
            matching_files = glob.glob(str(root_dir / search_pattern), recursive=True)
            
            if matching_files:
                for match in matching_files:
                    found_files.append(Path(match))
                    logger.info(f"Found file: {match}")
            else:
                logger.warning(f"No files found matching: {file_name}")
    
    return found_files

def read_file_content(file_path: Path) -> str:
    """Read content from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return ""

def collect_file_contents(file_paths: List[Path]) -> str:
    """Collect and format contents from multiple files."""
    contents = []
    
    for file_path in file_paths:
        content = read_file_content(file_path)
        if content:
            contents.append(f"## File: {file_path.name}\n\n{content}\n\n---\n")
    
    return "\n".join(contents)

def create_financial_plan_prompt() -> str:
    """Create the prompt for financial planning."""
    return """You are an expert financial analyst and business strategist. Based on the provided business plan and project information, create a comprehensive financial plan that includes:

1. **Financial Projections**:
   - Revenue projections for the next 1-3 years
   - Cost structure analysis
   - Break-even analysis
   - Cash flow projections

2. **Investment Analysis**:
   - Initial capital requirements
   - Funding sources recommendations
   - ROI projections
   - Risk assessment

3. **Market Analysis**:
   - Market size and potential
   - Competitive landscape impact on financials
   - Pricing strategy recommendations

4. **Financial Speculations**:
   - Best-case scenario projections
   - Worst-case scenario planning
   - Key financial milestones
   - Growth scaling opportunities

5. **Actionable Recommendations**:
   - Key performance indicators (KPIs) to track
   - Financial risk mitigation strategies
   - Investment timeline and phases
   - Exit strategy considerations

Please provide specific numbers, percentages, and timelines where possible. Be realistic but also consider growth potential. Format your response in clear sections with bullet points and tables where appropriate."""

def create_financial_system_prompt() -> str:
    """Create the system prompt for financial planning."""
    return """You are a senior financial analyst with extensive experience in business planning, startup funding, and financial modeling. You have a deep understanding of:

- Financial modeling and projections
- Investment analysis and valuation
- Market analysis and competitive positioning
- Risk assessment and mitigation
- Business development and scaling strategies

Your responses should be:
- Data-driven and analytical
- Realistic yet optimistic about growth potential
- Specific with numbers, percentages, and timelines
- Actionable with clear recommendations
- Professional and suitable for investors or stakeholders

Always consider multiple scenarios and provide comprehensive analysis that helps inform strategic business decisions."""

def generate_financial_plan(business_content: str, output_file: Optional[str] = None) -> str:
    """Generate a financial plan based on business content."""
    system_prompt = create_financial_system_prompt()
    user_prompt = f"{create_financial_plan_prompt()}\n\n## Business Information:\n\n{business_content}"
    
    logger.info("Generating financial plan and speculations...")
    
    # Initialize Claude AI
    claude = Claude()
    
    # Send the prompt and get response
    response = claude.send_prompt(user_prompt, system_prompt=system_prompt, maximize=True)
    
    # Save to file if specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(response)
        
        logger.info(f"Financial plan saved to: {output_path}")
    
    return response

def main():
    """Main function to orchestrate the financial planning process."""
    args = parse_arguments()
    
    # Set root directory
    root_dir = Path(args.root_dir) if args.root_dir else Path(".")
    root_dir = root_dir.resolve()
    
    # Handle file inputs
    if not args.files:
        print_fancy("No files provided. Please specify business plan or project files.", "yellow", panel=True)
        return
    
    # Find files
    file_paths = find_files_in_directory(args.files, root_dir)
    
    if not file_paths:
        print_fancy("No files found. Please check your file names and paths.", "red", panel=True)
        return
    
    # Collect file contents
    print_fancy(f"Processing {len(file_paths)} files...", "cyan", panel=True)
    business_content = collect_file_contents(file_paths)
    
    if not business_content.strip():
        print_fancy("No content found in the specified files.", "red", panel=True)
        return
    
    # Generate financial plan
    output_file = args.output or "financial_plan.md"
    financial_plan = generate_financial_plan(business_content, output_file)
    
    print_fancy("Financial plan generated successfully!", "green", panel=True)
    print("\n" + "="*50)
    print(financial_plan)
    print("="*50)

if __name__ == "__main__":
    main()