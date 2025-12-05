#!/usr/bin/env python3
"""
Debug test to see what the model generates for your command
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent.hf_llm import HFLLM
from src.agent.config import hf_merged_model_dir, hf_use_4bit

def test_generation():
    """Test what the model generates for your command"""
    
    print("=" * 80)
    print("MODEL GENERATION DEBUG")
    print("=" * 80)
    
    llm = HFLLM(hf_merged_model_dir(), use_4bit=hf_use_4bit())
    
    prompts = [
        "open chrome and search about it jobs and then write it in notepad",
        "step 1: open chrome. step 2: search for it jobs. step 3: open notepad and write the results",
        "I want you to: 1) open browser, 2) search 'IT jobs', 3) copy results, 4) open notepad, 5) paste results",
        "open google chrome, search for information technology jobs, save results, open notepad, type the results",
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'─' * 80}")
        print(f"TEST {i}: {prompt}")
        print(f"{'─' * 80}")
        
        try:
            response = llm.generate(prompt, max_tokens=500, temperature=0.1)
            print(f"\nModel Output:\n{response}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response)
                if isinstance(parsed, list) and len(parsed) > 0:
                    print(f"\n📋 Actions:")
                    for j, action in enumerate(parsed, 1):
                        print(f"   {j}. {action.get('tool')}: {action.get('args')}")
            except:
                pass
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_generation()
