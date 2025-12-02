"""
Try to use the 7B model with aggressive memory optimization.
This may work on a 4GB GPU but could fail with OOM errors.
"""

import sys
import torch
from pathlib import Path
import gc

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.hf_llm import HFLLM


def main():
    print("\n" + "=" * 70)
    print("  ⚠️  Testing 7B Model on 4GB GPU (Experimental)")
    print("=" * 70)
    print()
    print("Your GPU has 4GB VRAM, but 7B models typically need 6GB+")
    print("This test will try aggressive optimization. If it fails,")
    print("use the 3B model instead (which works great on 4GB).")
    print()
    
    # Clear GPU memory
    torch.cuda.empty_cache()
    gc.collect()
    
    try:
        print("📥 Loading 7B model with maximum optimization...")
        
        llm = HFLLM(
            base_or_merged="mistralai/Mistral-7B-Instruct-v0.2",
            adapter_dir=str(Path(__file__).parent / "brain_training/kayastune7b_t4/checkpoint-313"),
            use_4bit=True,
            attn_eager=True
        )
        
        print("✅ Model loaded! Testing generation...")
        print()
        
        # Test with short generation
        prompt = "Create a file called test.txt"
        system = "You are Kayas, a helpful AI assistant."
        
        print(f"User: {prompt}")
        print("Kayas: ", end="", flush=True)
        
        response = llm.generate(
            prompt=prompt,
            system=system,
            temperature=0.3,
            max_tokens=128  # Keep it short to save memory
        )
        
        print(response)
        print()
        print("=" * 70)
        print("✅ Success! Your 4GB GPU can handle the 7B model!")
        print("   You can use it, but keep max_tokens low to avoid OOM.")
        print("=" * 70)
        
    except torch.cuda.OutOfMemoryError:
        print()
        print("=" * 70)
        print("❌ Out of Memory Error")
        print()
        print("Your 4GB GPU cannot fit the 7B model, even with 4-bit.")
        print()
        print("✅ SOLUTION: Use your 3B model instead!")
        print()
        print("The 3B model is already configured in .agent/profile.yaml")
        print("It works great on 4GB GPUs and is still very capable.")
        print()
        print("Test it with: python quick_test_3b.py")
        print("=" * 70)
        return 1
        
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        print()
        print("Try using the 3B model instead (configured in profile.yaml)")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
