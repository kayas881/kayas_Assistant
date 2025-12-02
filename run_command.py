#!/usr/bin/env python3
"""
Quick test command for the agent with your 3B model.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.main import run_agent


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_command.py 'your command here'")
        print("\nExamples:")
        print("  python run_command.py 'create a todo list'")
        print("  python run_command.py 'search for Python tutorials'")
        print("  python run_command.py 'open Chrome and go to YouTube'")
        sys.exit(1)
    
    command = " ".join(sys.argv[1:])
    
    print(f"🎯 Command: {command}\n")
    
    try:
        result = run_agent(command)
        print("\n" + "=" * 80)
        print("📋 RESULT")
        print("=" * 80)
        print(f"Status: {result.get('status', 'unknown')}")
        if result.get('error'):
            print(f"Error: {result['error']}")
        if result.get('output'):
            print(f"Output:\n{result['output']}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

