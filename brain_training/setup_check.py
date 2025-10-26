"""
🚀 Quick Setup Script for AI Brain Training

This script checks prerequisites and helps you get started.
"""

import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor} (need 3.9+)")
        return False


def check_gpu():
    """Check if GPU is available"""
    print("\n🎮 Checking GPU...")
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"   ✅ {gpu_name} ({gpu_memory:.1f} GB)")
            
            if gpu_memory < 20:
                print(f"   ⚠️ WARNING: GPU has less than 20GB. Training may be slow.")
                print(f"      Recommended: L4 24GB or better")
            return True
        else:
            print("   ❌ No GPU detected")
            print("      This script requires a GPU for training.")
            print("      Recommended: L4 24GB")
            return False
    except ImportError:
        print("   ❌ PyTorch not installed")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required = {
        "torch": "PyTorch",
        "transformers": "Hugging Face Transformers",
        "datasets": "Hugging Face Datasets",
        "accelerate": "Accelerate",
        "bitsandbytes": "BitsAndBytes (4-bit quantization)",
        "peft": "PEFT (LoRA)",
        "trl": "TRL (Instruction fine-tuning)",
    }
    
    missing = []
    for package, name in required.items():
        try:
            __import__(package)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} - MISSING")
            missing.append(package)
    
    return missing


def check_training_data():
    """Check if training data exists"""
    print("\n📊 Checking training data...")
    
    data_dir = Path(__file__).parent / "training_data"
    base_file = data_dir / "brain_training_base.jsonl"
    aug_file = data_dir / "brain_training_augmented.jsonl"
    
    if aug_file.exists():
        print(f"   ✅ Augmented dataset found")
        # Count lines
        with open(aug_file, 'r') as f:
            count = sum(1 for _ in f)
        print(f"      {count} training examples")
        return True
    elif base_file.exists():
        print(f"   ⚠️ Only base dataset found")
        print(f"      Run augmentation for better results")
        return True
    else:
        print(f"   ❌ No training data found")
        print(f"      Run: python generate_training_data.py")
        return False


def install_dependencies():
    """Install missing dependencies"""
    print("\n📥 Installing dependencies...")
    print("   This may take 5-10 minutes...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("   ❌ requirements.txt not found")
        return False
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("   ✅ Dependencies installed!")
        return True
    except subprocess.CalledProcessError:
        print("   ❌ Installation failed")
        return False


def main():
    print("=" * 80)
    print("🧠 KAYAS AI BRAIN - SETUP CHECK")
    print("=" * 80)
    
    # Check Python
    if not check_python_version():
        print("\n❌ FAILED: Python version too old")
        print("   Install Python 3.9 or higher")
        return
    
    # Check GPU
    gpu_ok = check_gpu()
    
    # Check dependencies
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️ Missing {len(missing)} package(s)")
        response = input("Install now? (y/n): ")
        if response.lower() == 'y':
            if install_dependencies():
                print("\n✅ Dependencies installed! Rerun this script to verify.")
            else:
                print("\n❌ Installation failed. Install manually:")
                print("   pip install -r requirements.txt")
            return
        else:
            print("\n❌ Cannot proceed without dependencies")
            print("   Install with: pip install -r requirements.txt")
            return
    
    # Check training data
    data_ok = check_training_data()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    
    all_ok = gpu_ok and not missing and data_ok
    
    if all_ok:
        print("✅ ALL CHECKS PASSED!")
        print("\n🚀 You're ready to train!")
        print("\nNext steps:")
        print("   1. python generate_training_data.py  (if you haven't)")
        print("   2. python finetune_brain.py")
        print("   3. Wait ~2-3 hours")
        print("   4. python test_brain.py")
    else:
        print("⚠️ SOME CHECKS FAILED")
        if not gpu_ok:
            print("   - GPU required for training")
        if missing:
            print(f"   - Install dependencies: pip install -r requirements.txt")
        if not data_ok:
            print("   - Generate training data: python generate_training_data.py")
    
    print("\n" + "=" * 80)
    
    # GPU-specific recommendations
    if gpu_ok:
        import torch
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        print("\n💡 TRAINING TIPS:")
        print(f"   GPU Memory: {gpu_memory:.1f} GB")
        
        if gpu_memory >= 24:
            print("   ✅ Perfect for training!")
            print("   Use default settings in finetune_brain.py")
        elif gpu_memory >= 16:
            print("   ⚠️ Reduce batch_size to 1 in finetune_brain.py")
            print("   Increase gradient_accumulation_steps to 16")
        else:
            print("   ⚠️ GPU may be too small")
            print("   Consider using a cloud GPU (L4 24GB recommended)")
        
        print("\n📊 ESTIMATED TRAINING TIME:")
        if gpu_memory >= 24:
            print("   ~2-3 hours (batch_size=2)")
        elif gpu_memory >= 16:
            print("   ~4-5 hours (batch_size=1)")
        else:
            print("   ~6+ hours (may run out of memory)")


if __name__ == "__main__":
    main()
