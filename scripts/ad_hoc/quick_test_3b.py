"""
Quick test of your 3B model (perfect for 4GB GPU).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.hf_llm import HFLLM


def main():
    print("\n" + "=" * 70)
    print("  🚀 Testing Kayas 3B Model (4GB GPU Friendly)")
    print("=" * 70)
    print()
    
    print("📥 Loading your merged 3B model...")
    print("   Location: brain_training/kayas-brain-3b-merged")
    print()
    
    try:
        llm = HFLLM(
            base_or_merged=str(Path(__file__).parent / "brain_training/kayas-brain-3b-merged"),
            adapter_dir=None,  # Already merged
            use_4bit=True,
            attn_eager=True
        )
        
        print("✅ Model loaded successfully!\n")
        
        # Test prompts
        test_prompts = [
            "Create a file called notes.txt with my daily tasks",
            "What are the top AI trends in 2024?",
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
        print("\nCheck that the model exists at:")
        print("  brain_training/kayas-brain-3b-merged")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
