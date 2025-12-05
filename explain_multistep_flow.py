#!/usr/bin/env python3
"""
DEMONSTRATION: How Multi-Step Tasks Flow Through the System
Shows the actual execution path for real tasks
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'─'*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'─'*70}{Colors.ENDC}\n")

@dataclass
class TaskFlow:
    """Models how a task flows through the system"""
    user_input: str
    is_multistep: bool
    detected_steps: List[str]
    actual_execution_path: List[str]

def demo_task_1():
    """Demo: Open Chrome and search for Python"""
    print_section("EXAMPLE 1: Open Chrome and Search for Python")
    
    user_input = "Open Chrome and search for Python machine learning"
    
    print(f"{Colors.BOLD}User Input:{Colors.ENDC}")
    print(f"  {Colors.YELLOW}\"{user_input}\"{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}Step 1: Detection{Colors.ENDC}")
    print(f"  {Colors.CYAN}[DirectAgent._is_multistep_task()]{Colors.ENDC}")
    print(f"  ├─ Contains 'and': {Colors.GREEN}✓{Colors.ENDC}")
    print(f"  ├─ Pattern: 'open' + 'search': {Colors.GREEN}✓{Colors.ENDC}")
    print(f"  └─ Result: {Colors.GREEN}Multi-step task{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}Step 2: Routing{Colors.ENDC}")
    print(f"  {Colors.CYAN}[DirectAgent.run()]{Colors.ENDC}")
    print(f"  └─ is_multistep=True → Use MultiStepRunner\n")
    
    print(f"{Colors.BOLD}Step 3: Execution Loop{Colors.ENDC}")
    print(f"  {Colors.CYAN}[MultiStepRunner.run_task()]{Colors.ENDC}")
    print(f"  │")
    print(f"  ├─ {Colors.YELLOW}Iteration 1:{Colors.ENDC}")
    print(f"  │  ├─ Action: Start Chrome")
    print(f"  │  ├─ Router executes: process.start('chrome')")
    print(f"  │  ├─ Result: Chrome process started")
    print(f"  │  └─ Ask LLM: 'Is task complete?'")
    print(f"  │     └─ {Colors.YELLOW}LLM Response: No, still need to search{Colors.ENDC}")
    print(f"  │")
    print(f"  ├─ {Colors.YELLOW}Iteration 2:{Colors.ENDC}")
    print(f"  │  ├─ Action: Search for 'Python machine learning'")
    print(f"  │  ├─ Router executes: browser.search(query)")
    print(f"  │  ├─ Result: Google search opened with results")
    print(f"  │  └─ Ask LLM: 'Is task complete?'")
    print(f"  │     └─ {Colors.GREEN}LLM Response: Yes, both steps done!{Colors.ENDC}")
    print(f"  │")
    print(f"  └─ Return to user: 'Done! I opened Chrome and searched for Python machine learning'\n")
    
    print(f"{Colors.BOLD}Key Files Involved:{Colors.ENDC}")
    print(f"  {Colors.CYAN}src/voice/direct_agent.py{Colors.ENDC}")
    print(f"    └─ run() method detects multi-step → routes to runner")
    print(f"  {Colors.CYAN}src/agent/multi_step_runner.py{Colors.ENDC}")
    print(f"    ├─ run_task() implements execution loop")
    print(f"    ├─ _execute_action_batch() runs actions")
    print(f"    └─ _should_continue() asks LLM 'what's next?'")
    print(f"  {Colors.CYAN}src/agent/actions.py (Router){Colors.ENDC}")
    print(f"    └─ Executes actual browser/process/desktop actions\n")

def demo_task_2():
    """Demo: Open Chrome and select profile"""
    print_section("EXAMPLE 2: Open Chrome and Select Profile")
    
    user_input = "Open Chrome and select the kayas profile"
    
    print(f"{Colors.BOLD}User Input:{Colors.ENDC}")
    print(f"  {Colors.YELLOW}\"{user_input}\"{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}Execution Flow:{Colors.ENDC}")
    print(f"  {Colors.YELLOW}1. Detect Multi-Step{Colors.ENDC}")
    print(f"     └─ Contains: 'open' AND 'select' → {Colors.GREEN}Multi-step{Colors.ENDC}\n")
    
    print(f"  {Colors.YELLOW}2. Execute Step 1: Open Chrome{Colors.ENDC}")
    print(f"     ├─ Router: process_executor.start_process('chrome')")
    print(f"     └─ Result: Chrome window appears with profile selector\n")
    
    print(f"  {Colors.YELLOW}3. Check Completion{Colors.ENDC}")
    print(f"     ├─ LLM sees: Chrome open + profile dialog visible")
    print(f"     ├─ Goal: 'select kayas profile'")
    print(f"     └─ Decision: {Colors.YELLOW}Not complete yet, need to click profile{Colors.ENDC}\n")
    
    print(f"  {Colors.YELLOW}4. Execute Step 2: Click Profile{Colors.ENDC}")
    print(f"     ├─ Router: ui_automation.click_element('kayas_profile')")
    print(f"     └─ Result: Profile selected, Chrome logs in\n")
    
    print(f"  {Colors.YELLOW}5. Final Check{Colors.ENDC}")
    print(f"     ├─ Chrome running with kayas account")
    print(f"     └─ Decision: {Colors.GREEN}Complete!{Colors.ENDC}\n")

def demo_task_3():
    """Demo: Search and save"""
    print_section("EXAMPLE 3: Search for Python and Save to Notepad")
    
    user_input = "Search for Python tutorials and save results to notepad"
    
    print(f"{Colors.BOLD}User Input:{Colors.ENDC}")
    print(f"  {Colors.YELLOW}\"{user_input}\"{Colors.ENDC}\n")
    
    steps = [
        ("1", "Open Search Engine", "browser_executor.open_url('google.com')"),
        ("2", "Search Query", "browser_executor.search('Python tutorials')"),
        ("3", "Collect Results", "perception_executor.capture_text_from_page()"),
        ("4", "Open Notepad", "process_executor.start_process('notepad.exe')"),
        ("5", "Paste Results", "ui_automation.paste_clipboard()"),
    ]
    
    print(f"{Colors.BOLD}Multi-Step Execution Chain:{Colors.ENDC}")
    for step_num, action, executor in steps:
        print(f"  {Colors.YELLOW}Step {step_num}: {action}{Colors.ENDC}")
        print(f"    └─ {Colors.CYAN}{executor}{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}LLM Decision at Each Step:{Colors.ENDC}")
    print(f"  After Step 1: {Colors.YELLOW}Not complete{Colors.ENDC} (need to search)")
    print(f"  After Step 2: {Colors.YELLOW}Not complete{Colors.ENDC} (need to save)")
    print(f"  After Step 3: {Colors.YELLOW}Not complete{Colors.ENDC} (need to open notepad)")
    print(f"  After Step 4: {Colors.YELLOW}Not complete{Colors.ENDC} (need to paste)")
    print(f"  After Step 5: {Colors.GREEN}Complete!{Colors.ENDC}\n")

def demo_comparison():
    """Show before and after"""
    print_section("BEFORE vs AFTER: The Fix")
    
    task = "Open Chrome and search for Python"
    
    print(f"{Colors.BOLD}OLD BEHAVIOR (Before Fix):{Colors.ENDC}\n")
    print(f"  {Colors.YELLOW}1. DirectAgent.run(goal) called{Colors.ENDC}")
    print(f"  {Colors.YELLOW}2. Generate single action: 'Start Chrome'{Colors.ENDC}")
    print(f"  {Colors.YELLOW}3. Execute action{Colors.ENDC}")
    print(f"  {Colors.YELLOW}4. Return response: 'Done! I started Chrome'{Colors.ENDC}")
    print(f"  {Colors.RED}❌ Result: Search never happens{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}NEW BEHAVIOR (After Fix):{Colors.ENDC}\n")
    print(f"  {Colors.YELLOW}1. DirectAgent.run(goal) called{Colors.ENDC}")
    print(f"  {Colors.YELLOW}2. Detect: is_multistep_task() → True{Colors.ENDC}")
    print(f"  {Colors.YELLOW}3. Route to MultiStepRunner{Colors.ENDC}")
    print(f"  {Colors.YELLOW}4. Loop:{Colors.ENDC}")
    print(f"     ├─ Execute: Start Chrome")
    print(f"     ├─ Ask: Is task complete?")
    print(f"     ├─ Response: No, need to search")
    print(f"     ├─ Execute: Search for Python")
    print(f"     ├─ Ask: Is task complete?")
    print(f"     └─ Response: Yes!")
    print(f"  {Colors.GREEN}✓ Result: Both actions executed{Colors.ENDC}\n")

def demo_code_flow():
    """Show actual code flow"""
    print_section("CODE FLOW: How It Works Internally")
    
    print(f"{Colors.BOLD}1. In src/voice/direct_agent.py:{Colors.ENDC}\n")
    print(f"""{Colors.CYAN}def run(self, goal, conversation_context=None):
    is_multistep = self._is_multistep_task(goal)
    
    if is_multistep:
        # Multi-step workflow
        return self.multi_step_runner.run_task(goal)
    else:
        # Single action
        return self.execute_single_action(goal){Colors.ENDC}\n""")
    
    print(f"{Colors.BOLD}2. In src/agent/multi_step_runner.py:{Colors.ENDC}\n")
    print(f"""{Colors.CYAN}def run_task(self, goal, max_steps=10):
    execution_context = ExecutionContext(goal)
    
    while not execution_context.completed:
        # Execute actions
        results = self._execute_action_batch(plan)
        
        # Ask LLM: should we continue?
        should_continue = self._should_continue(
            goal=goal,
            completed_steps=results,
            context=execution_context
        )
        
        if not should_continue:
            break
    
    return self._generate_final_response(){Colors.ENDC}\n""")
    
    print(f"{Colors.BOLD}3. The Loop keeps going until:{Colors.ENDC}")
    print(f"  • LLM says task is complete")
    print(f"  • Max steps reached (default 10)")
    print(f"  • Error occurs\n")

def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'MULTI-STEP EXECUTION: HOW IT WORKS'.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}This document shows how real tasks flow through the system{Colors.ENDC}\n")
    
    # Run demos
    demo_task_1()
    
    input(f"\n{Colors.BOLD}Press Enter to see Example 2...{Colors.ENDC}")
    demo_task_2()
    
    input(f"\n{Colors.BOLD}Press Enter to see Example 3...{Colors.ENDC}")
    demo_task_3()
    
    input(f"\n{Colors.BOLD}Press Enter to see Before vs After...{Colors.ENDC}")
    demo_comparison()
    
    input(f"\n{Colors.BOLD}Press Enter to see Code Flow...{Colors.ENDC}")
    demo_code_flow()
    
    print_section("SUMMARY")
    print(f"{Colors.GREEN}{Colors.BOLD}✓ Your system now:{Colors.ENDC}")
    print(f"  1. Detects multi-step tasks automatically")
    print(f"  2. Routes them to the MultiStepRunner")
    print(f"  3. Executes actions in a loop")
    print(f"  4. Asks LLM 'is task done?' after each step")
    print(f"  5. Continues until the goal is truly complete\n")
    
    print(f"{Colors.BOLD}Result:{Colors.ENDC}")
    print(f"  Workflows like 'Open Chrome and search' now work end-to-end!")
    print(f"  No more partial execution.\n")

if __name__ == "__main__":
    main()
