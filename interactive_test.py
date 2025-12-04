#!/usr/bin/env python3
"""
Interactive Agent Test - Type commands and see real-time execution
Model: final_merged (Qwen 2.5 3B - 15,000 samples trained)

Type exit/quit to stop
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent.main import run_agent

def print_header():
    print("\n" + "=" * 90)
    print(" " * 20 + "KAYAS - Interactive Agent Test")
    print(" " * 15 + "Model: final_merged (Qwen 2.5 3B - Checkpoint 1500)")
    print("=" * 90)
    print("\n📝 TYPE A COMMAND BELOW:\n")
    print("💡 Examples:")
    print("   • open notepad")
    print("   • search for python tutorials")
    print("   • create a file called notes.txt with content hello world")
    print("   • open chrome")
    print("   • save this information to a file")
    print("\nType 'exit' or 'quit' to stop.\n")
    print("-" * 90)

def format_response(response):
    """Format and display agent response"""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except:
            if response:
                print(f"\n📝 {response}\n")
            return
    
    if isinstance(response, dict):
        if 'response' in response:
            resp_text = response['response']
            if len(resp_text) > 500:
                resp_text = resp_text[:500] + "..."
            print(f"\n📝 {resp_text}\n")
        
        if 'actions' in response:
            actions = response['actions']
            print(f"🔧 Executed {len(actions)} action(s):")
            for i, action in enumerate(actions[:10], 1):
                tool = action.get('tool', 'unknown')
                print(f"   {i}. {tool}")
            print()

def main():
    print_header()
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n✓ Goodbye!\n")
                break
            
            print(f"\n⏳ Processing...\n")
            
            response = run_agent(user_input)
            format_response(response)
            
    except KeyboardInterrupt:
        print("\n\n✓ Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    main()
