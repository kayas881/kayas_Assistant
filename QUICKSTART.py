#!/usr/bin/env python3
"""
QUICK START GUIDE: How to Start Kayas
"""

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

def print_code(code, title=None):
    if title:
        print(f"{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.CYAN}{code}{Colors.ENDC}\n")

def main():
    print_header("HOW TO START KAYAS")
    
    # Option 1
    print(f"{Colors.BOLD}{Colors.GREEN}OPTION 1: Start the Interactive Tester{Colors.ENDC}")
    print(f"(For testing multi-step tasks locally)\n")
    print_code("python interactive_multistep_test.py", "Command:")
    print(f"Then type tasks like:")
    print(f"  {Colors.YELLOW}• open chrome and search for python{Colors.ENDC}")
    print(f"  {Colors.YELLOW}• search for machine learning and save to notepad{Colors.ENDC}")
    print(f"  {Colors.YELLOW}• open notepad and type hello world{Colors.ENDC}\n")
    
    # Option 2
    print(f"{Colors.BOLD}{Colors.GREEN}OPTION 2: Use the Real Agent{Colors.ENDC}")
    print(f"(Full integration with all executors)\n")
    
    print(f"{Colors.BOLD}In Python code:{Colors.ENDC}\n")
    print_code("""from src.agent.main import run_agent

# Run a task
result = run_agent("open chrome and search for python tutorials")
print(result)""")
    
    print(f"{Colors.BOLD}Or via command line:{Colors.ENDC}\n")
    print_code("python real_multistep_executor.py", "Command:")
    print(f"Then enter tasks interactively\n")
    
    # Option 3
    print(f"{Colors.BOLD}{Colors.GREEN}OPTION 3: Start the Full Voice Assistant{Colors.ENDC}")
    print(f"(Voice input + multi-step execution)\n")
    print_code("python kayas.py", "Command:")
    print(f"This starts Kayas with voice input and full multi-step support\n")
    
    # Architecture explanation
    print_header("HOW IT WORKS INTERNALLY")
    
    print(f"{Colors.BOLD}When you start Kayas and give it a task:{Colors.ENDC}\n")
    
    print(f"{Colors.YELLOW}1. Task Detection{Colors.ENDC}")
    print(f"   DirectAgent checks: Is this a multi-step task?")
    print(f"   {Colors.CYAN}→ 'open chrome and search' = YES (multi-step){Colors.ENDC}")
    print(f"   {Colors.CYAN}→ 'what time is it?' = NO (single step){Colors.ENDC}\n")
    
    print(f"{Colors.YELLOW}2. Routing{Colors.ENDC}")
    print(f"   {Colors.CYAN}If multi-step: Use MultiStepRunner{Colors.ENDC}")
    print(f"   {Colors.CYAN}If single: Direct execution{Colors.ENDC}\n")
    
    print(f"{Colors.YELLOW}3. Execution Loop{Colors.ENDC}")
    print(f"   {Colors.CYAN}Step 1: Execute action{Colors.ENDC}")
    print(f"   {Colors.CYAN}Step 2: Ask LLM 'is task complete?'{Colors.ENDC}")
    print(f"   {Colors.CYAN}Step 3: If NO → go to step 1 with next action{Colors.ENDC}")
    print(f"   {Colors.CYAN}Step 4: If YES → return result{Colors.ENDC}\n")
    
    # File structure
    print_header("KEY FILES")
    
    print(f"{Colors.BOLD}Core Multi-Step Implementation:{Colors.ENDC}\n")
    print(f"  {Colors.CYAN}src/agent/multi_step_runner.py{Colors.ENDC}")
    print(f"    └─ Orchestrates multi-step execution\n")
    
    print(f"  {Colors.CYAN}src/voice/direct_agent.py{Colors.ENDC}")
    print(f"    └─ Detects and routes multi-step tasks\n")
    
    print(f"{Colors.BOLD}Main Entry Points:{Colors.ENDC}\n")
    print(f"  {Colors.CYAN}src/agent/main.py{Colors.ENDC}")
    print(f"    └─ run_agent(goal) - Main function\n")
    
    print(f"  {Colors.CYAN}kayas.py{Colors.ENDC}")
    print(f"    └─ Voice interface with full capabilities\n")
    
    print(f"{Colors.BOLD}Testing:{Colors.ENDC}\n")
    print(f"  {Colors.CYAN}interactive_multistep_test.py{Colors.ENDC}")
    print(f"    └─ Interactive test environment\n")
    
    print(f"  {Colors.CYAN}test_multistep_execution.py{Colors.ENDC}")
    print(f"    └─ Automated test suite\n")
    
    # Quick start examples
    print_header("QUICK START EXAMPLES")
    
    print(f"{Colors.BOLD}Example 1: Python Script{Colors.ENDC}\n")
    print_code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent.main import run_agent

# Give Kayas a multi-step task
result = run_agent("Open Chrome and search for Python tutorials")
print(result)
""", "kayas_example.py:")
    
    print(f"{Colors.BOLD}Example 2: Interactive Terminal{Colors.ENDC}\n")
    print_code("""$ python interactive_multistep_test.py

Enter a task: open notepad and create a file
[Step 1] Opening notepad...
  ✓ Opened notepad
[Step 2] Creating a file...
  ✓ File created
""", "Terminal:")
    
    print(f"{Colors.BOLD}Example 3: With Voice (Full Kayas){Colors.ENDC}\n")
    print_code("""$ python kayas.py

Listening for voice...
You: "Open chrome and search for python"
Kayas: "Sure, I'll open Chrome and search for python..."
[Opens Chrome, performs search]
Kayas: "Done! I found Python tutorials for you."
""", "Terminal:")
    
    # Troubleshooting
    print_header("COMMON ISSUES & SOLUTIONS")
    
    issues = [
        {
            "problem": "Import errors when starting",
            "solution": "Make sure you're in the virtual environment:\n   & .venv\\Scripts\\Activate.ps1"
        },
        {
            "problem": "Can't find Chrome or apps",
            "solution": "Apps need to be installed. The system will continue with alternatives."
        },
        {
            "problem": "Multi-step not detecting",
            "solution": "Use 'and', 'then', or 'after' keywords:\n   Good: 'open chrome AND search'\n   Bad: 'open chrome, search'"
        },
        {
            "problem": "LLM/Model not loading",
            "solution": "Check your model configuration in src/agent/config.py"
        }
    ]
    
    for i, issue in enumerate(issues, 1):
        print(f"{Colors.YELLOW}Q{i}: {issue['problem']}{Colors.ENDC}")
        print(f"{Colors.CYAN}→ {issue['solution']}{Colors.ENDC}\n")
    
    # Summary
    print_header("SUMMARY")
    
    print(f"{Colors.GREEN}{Colors.BOLD}✓ To Start Kayas:{Colors.ENDC}\n")
    print(f"  1. {Colors.YELLOW}Activate virtual environment:{Colors.ENDC}")
    print_code("& .venv\\Scripts\\Activate.ps1")
    
    print(f"  2. {Colors.YELLOW}Choose how to start:{Colors.ENDC}")
    print(f"     • Testing: {Colors.CYAN}python interactive_multistep_test.py{Colors.ENDC}")
    print(f"     • Full Agent: {Colors.CYAN}python real_multistep_executor.py{Colors.ENDC}")
    print(f"     • Voice: {Colors.CYAN}python kayas.py{Colors.ENDC}\n")
    
    print(f"  3. {Colors.YELLOW}Give it a task:{Colors.ENDC}")
    print(f"     '{Colors.CYAN}Open notepad and write a hello world program{Colors.ENDC}'")
    print(f"     '{Colors.CYAN}Find all PDFs and organize by date{Colors.ENDC}'")
    print(f"     '{Colors.CYAN}Search for tutorials and save to file{Colors.ENDC}'\n")
    
    print(f"{Colors.GREEN}{Colors.BOLD}✓ That's it! Kayas will handle the rest.{Colors.ENDC}\n")
    print(f"The multi-step execution system will:")
    print(f"  • Detect the task needs multiple steps")
    print(f"  • Execute each step sequentially")
    print(f"  • Check if complete after each step")
    print(f"  • Continue until goal is achieved\n")

if __name__ == "__main__":
    main()
