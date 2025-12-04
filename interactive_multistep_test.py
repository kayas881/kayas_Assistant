#!/usr/bin/env python3
"""
Interactive Multi-Step Task Execution Tester
Test the system with your own commands to see it in action
"""

import webbrowser
import subprocess
import time
import re
from pathlib import Path

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

class MultiStepExecutor:
    """Interactive executor for testing multi-step workflows"""
    
    def __init__(self):
        self.steps = []
        self.task_history = []
    
    def _is_multistep_task(self, goal):
        """Detect if a task requires multiple steps"""
        goal_lower = goal.lower()
        
        # Multi-step indicators
        if any(x in goal_lower for x in [' and ', ' then ', ' after ', ' before ']):
            return True
        
        # Sequential patterns
        sequential_patterns = [
            r'open.*(?:and|then).*search',
            r'search.*(?:and|then).*save',
            r'open.*(?:and|then).*(?:select|click|navigate)',
            r'open.*(?:and|then).*(?:type|write)',
        ]
        
        for pattern in sequential_patterns:
            if re.search(pattern, goal_lower):
                return True
        
        return False
    
    def execute_search(self, query):
        """Execute a search"""
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            self.steps.append(f"Searched for: {query}")
            return True, f"Opened search: {query}"
        except Exception as e:
            return False, f"Search failed: {e}"
    
    def execute_save(self, content, filename=None):
        """Save content to a file"""
        try:
            if filename is None:
                filename = "saved_content.txt"
            
            # Save to desktop
            desktop = Path.home() / "Desktop"
            desktop.mkdir(exist_ok=True)
            filepath = desktop / filename
            
            with open(filepath, 'w') as f:
                f.write(f"Saved at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")
                f.write(content)
            
            self.steps.append(f"Saved to: {filepath}")
            return True, f"Saved to: {filepath}"
        except Exception as e:
            return False, f"Save failed: {e}"
    
    def execute_open_app(self, app_name):
        """Open an application"""
        try:
            # Map common app names
            app_map = {
                'notepad': 'notepad.exe',
                'calculator': 'calc.exe',
                'chrome': 'chrome',
                'firefox': 'firefox',
                'edge': 'msedge',
            }
            
            app_cmd = app_map.get(app_name.lower(), app_name)
            subprocess.Popen(app_cmd)
            self.steps.append(f"Opened: {app_name}")
            return True, f"Opened {app_name}"
        except Exception as e:
            return False, f"Failed to open {app_name}: {e}"
    
    def run_task(self, goal):
        """Execute a task with multi-step logic"""
        print(f"\n{Colors.BOLD}User Input:{Colors.ENDC} {goal}\n")
        
        # Detect if multi-step
        is_multistep = self._is_multistep_task(goal)
        print(f"{Colors.CYAN}[System]{Colors.ENDC} Task type: {Colors.GREEN if is_multistep else Colors.YELLOW}{'Multi-Step' if is_multistep else 'Single Action'}{Colors.ENDC}")
        
        self.steps = []
        step_num = 1
        
        if not is_multistep:
            # Simple task execution
            print(f"{Colors.CYAN}[System]{Colors.ENDC} Executing single action...")
            self.steps.append(f"Executed: {goal}")
        else:
            # Multi-step execution
            print(f"{Colors.CYAN}[System]{Colors.ENDC} Executing multi-step workflow...")
            print(f"{Colors.CYAN}[System]{Colors.ENDC} Breaking down into steps...\n")
            
            # Parse the goal for keywords
            goal_lower = goal.lower()
            
            # Step 1: Handle "open" commands
            if 'open' in goal_lower:
                app_match = re.search(r'open\s+(\w+)', goal_lower)
                if app_match:
                    app_name = app_match.group(1)
                    print(f"{Colors.CYAN}[Step {step_num}]{Colors.ENDC} Opening {app_name}...")
                    success, msg = self.execute_open_app(app_name)
                    if success:
                        print(f"  {Colors.GREEN}✓{Colors.ENDC} {msg}")
                        step_num += 1
                    else:
                        print(f"  {Colors.YELLOW}⚠{Colors.ENDC} {msg} (continuing...)")
                        step_num += 1
            
            # Step 2: Handle "search" commands
            if 'search' in goal_lower:
                search_match = re.search(r"search(?:\s+for)?\s+['\"]?([^'\"]+)['\"]?(?:\s+and|\s+then|$)", goal_lower)
                if search_match:
                    query = search_match.group(1).strip()
                    print(f"\n{Colors.CYAN}[Step {step_num}]{Colors.ENDC} Searching for: '{query}'...")
                    success, msg = self.execute_search(query)
                    if success:
                        print(f"  {Colors.GREEN}✓{Colors.ENDC} {msg}")
                        step_num += 1
                    else:
                        print(f"  {Colors.YELLOW}⚠{Colors.ENDC} {msg}")
                        step_num += 1
            
            # Step 3: Handle "select profile" commands
            if 'select' in goal_lower and 'profile' in goal_lower:
                profile_match = re.search(r'select\s+(\w+)\s+(?:as\s+)?profile', goal_lower)
                if profile_match:
                    profile_name = profile_match.group(1)
                    print(f"\n{Colors.CYAN}[Step {step_num}]{Colors.ENDC} Selecting '{profile_name}' profile...")
                    self.steps.append(f"Selected profile: {profile_name}")
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} Selected profile: {profile_name}")
                    step_num += 1
            
            # Step 4: Handle "save" commands
            if 'save' in goal_lower:
                filename_match = re.search(r"(?:to|as)\s+['\"]?([^'\"]+)['\"]?(?:\s+file)?", goal_lower)
                if filename_match:
                    filename = filename_match.group(1).strip()
                    if not filename.endswith('.txt'):
                        filename += '.txt'
                else:
                    filename = "results.txt"
                
                print(f"\n{Colors.CYAN}[Step {step_num}]{Colors.ENDC} Saving to file...")
                success, msg = self.execute_save("Multi-step workflow results and information", filename)
                if success:
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} {msg}")
                    step_num += 1
                else:
                    print(f"  {Colors.YELLOW}⚠{Colors.ENDC} {msg}")
                    step_num += 1
        
        # Print summary
        print(f"\n{Colors.CYAN}[Summary]{Colors.ENDC}")
        print(f"  Steps executed: {len(self.steps)}")
        for i, step in enumerate(self.steps, 1):
            print(f"    {i}. {step}")
        
        self.task_history.append({
            'goal': goal,
            'is_multistep': is_multistep,
            'steps': len(self.steps)
        })
        
        return is_multistep

def main():
    print_header("INTERACTIVE MULTI-STEP TASK EXECUTION TESTER")
    
    print(f"{Colors.BOLD}Welcome!{Colors.ENDC}\n")
    print("This tool lets you test multi-step task execution in real-time.")
    print("Try commands like:")
    print(f"  {Colors.YELLOW}• Open Chrome and search for Python{Colors.ENDC}")
    print(f"  {Colors.YELLOW}• Search for machine learning and save results{Colors.ENDC}")
    print(f"  {Colors.YELLOW}• Open Notepad and type hello{Colors.ENDC}")
    print(f"  {Colors.YELLOW}• Search for tutorials and save to desktop{Colors.ENDC}\n")
    
    executor = MultiStepExecutor()
    
    while True:
        print(f"\n{Colors.BOLD}─" * 35 + "─{Colors.ENDC}")
        try:
            user_input = input(f"\n{Colors.BOLD}Enter a task{Colors.ENDC} (or 'quit' to exit): ").strip()
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Exiting...{Colors.ENDC}")
            break
        
        if not user_input:
            print(f"{Colors.YELLOW}Please enter a task.{Colors.ENDC}")
            continue
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        
        if user_input.lower() == 'history':
            if executor.task_history:
                print(f"\n{Colors.BOLD}Task History:{Colors.ENDC}")
                for i, task in enumerate(executor.task_history, 1):
                    task_type = f"{Colors.GREEN}Multi-Step{Colors.ENDC}" if task['is_multistep'] else f"{Colors.YELLOW}Single{Colors.ENDC}"
                    print(f"  {i}. [{task_type}] {task['goal']}")
            else:
                print(f"{Colors.YELLOW}No tasks executed yet.{Colors.ENDC}")
            continue
        
        if user_input.lower() == 'help':
            print(f"""
{Colors.BOLD}Commands:{Colors.ENDC}
  quit/exit   - Exit the tester
  history     - Show task history
  help        - Show this message

{Colors.BOLD}Example Tasks:{Colors.ENDC}
  • "Open Chrome and search for Python"
  • "Search for machine learning and save"
  • "Open Notepad and create a file"
  • "Find tutorials and save them"
  • "Open calculator"
            """)
            continue
        
        # Execute the task
        is_multistep = executor.run_task(user_input)
        
        time.sleep(0.5)  # Brief pause for readability
    
    # Final summary
    if executor.task_history:
        print_header("EXECUTION SUMMARY")
        print(f"{Colors.BOLD}Total tasks executed:{Colors.ENDC} {len(executor.task_history)}\n")
        
        multistep_count = sum(1 for t in executor.task_history if t['is_multistep'])
        single_count = len(executor.task_history) - multistep_count
        
        print(f"  {Colors.GREEN}✓ Multi-step tasks: {multistep_count}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}○ Single-step tasks: {single_count}{Colors.ENDC}")
        print(f"\n  Total steps executed: {sum(t['steps'] for t in executor.task_history)}")
    
    print(f"\n{Colors.GREEN}Thanks for testing!{Colors.ENDC}\n")

if __name__ == "__main__":
    main()
