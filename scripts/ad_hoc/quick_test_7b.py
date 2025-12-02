"""
Quick test of the 7B model without loading the full agent.
Faster way to verify your model is working.
"""

import sys
import torch
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.hf_llm import HFLLM


def main():
    print("\n" + "=" * 70)
    print("  🚀 Quick Test: Kayas 7B Model")
    print("=" * 70)
    print()
    
    # Initialize the model (uses your profile.yaml config)
    print("📥 Loading your trained 7B model...")
    print("   Base: mistralai/Mistral-7B-Instruct-v0.2")
    print("   Adapter: brain_training/kayastune7b_t4/checkpoint-313")
    print()
    
    try:
        llm = HFLLM(
            base_or_merged="mistralai/Mistral-7B-Instruct-v0.2",
            adapter_dir=str(Path(__file__).parent / "brain_training/kayastune7b_t4/checkpoint-313"),
            use_4bit=True,
            attn_eager=True
        )
        
        print("✅ Model loaded successfully!\n")
        
        # Test prompts
        test_prompts = [
            "Create a file called test.txt with hello world",
            "What are the top 3 AI trends in 2024?",
            "Open Chrome and search for Python tutorials",
        ]
        
        system_prompt = "You are Kayas, an intelligent AI assistant. Be concise and helpful."
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"[Test {i}] User: {prompt}")
            print("Kayas: ", end="", flush=True)
            
            try:
                response = llm.generate(
                    prompt=prompt,
                    system=system_prompt,
                    temperature=0.3,
                    max_tokens=256
                )
                print(response)
                print()
            except Exception as e:
                print(f"Error: {e}")
                print()
        
        # Interactive mode
        print("=" * 70)
        print("💬 Interactive Mode (type 'quit' to exit)")
        print("=" * 70)
        print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                print("Kayas: ", end="", flush=True)
                response = llm.generate(
                    prompt=user_input,
                    system=system_prompt,
                    temperature=0.3,
                    max_tokens=256
                )
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}\n")
    
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're logged in to HuggingFace: huggingface-cli login")
        print("2. Check that the adapter path exists: brain_training/kayastune7b_t4/checkpoint-313")
        print("3. Ensure you have enough GPU memory (6GB+ recommended)")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
