#!/usr/bin/env python3
"""
Debug test to see exact model output for multi-step commands
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent.hf_llm import HFLLM
from src.agent.config import hf_merged_model_dir, hf_use_4bit

def test_model_output():
    """Test what the model actually generates"""
    
    print("=" * 80)
    print("TESTING MODEL OUTPUT FOR MULTI-STEP COMMANDS")
    print("=" * 80)
    
    llm = HFLLM(hf_merged_model_dir(), use_4bit=hf_use_4bit())
    
    test_prompt = """You are a desktop automation agent. Generate a JSON list of actions to accomplish this task:

Task: Open Chrome, search for Python jobs, then save the results to a text file

Available tools:
- process.start_program: Start a program
- browser.search: Search the web
- filesystem.create_file: Create and save a file
- uia.type_text: Type text
- desktop.run_steps: Execute desktop steps

Respond ONLY with a valid JSON array of actions, like:
[{"tool": "process.start_program", "args": {"program": "chrome"}}, ...]"""
    
    print(f"\nPrompt:\n{test_prompt}\n")
    print("=" * 80)
    print("Model Response:\n")
    
    response = llm.generate(test_prompt, max_tokens=800, temperature=0.1)
    print(response)
    
    print("\n" + "=" * 80)
    print("Analysis:\n")
    
    try:
        # Extract JSON from response
        start = response.find('[')
        end = response.rfind(']') + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            actions = json.loads(json_str)
            print(f"✓ Parsed {len(actions)} actions:")
            for i, action in enumerate(actions, 1):
                print(f"   {i}. {action.get('tool')}: {action.get('args')}")
        else:
            print("Could not find JSON in response")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")

if __name__ == "__main__":
    test_model_output()
