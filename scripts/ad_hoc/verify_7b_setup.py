"""
Verify that your 7B model integration is set up correctly.
Run this before testing the model to catch common issues.
"""

import sys
from pathlib import Path
import importlib.util

def check_status(name: str, passed: bool, message: str = "") -> bool:
    """Print a status line"""
    status = "✅" if passed else "❌"
    print(f"{status} {name}")
    if message:
        print(f"   {message}")
    return passed

def main():
    print("\n" + "=" * 70)
    print("  🔍 Verifying 7B Model Integration Setup")
    print("=" * 70)
    print()
    
    all_good = True
    
    # Check Python version
    py_version = sys.version_info
    py_ok = py_version.major == 3 and py_version.minor >= 8
    all_good &= check_status(
        "Python Version",
        py_ok,
        f"Found: {py_version.major}.{py_version.minor}.{py_version.micro}" +
        ("" if py_ok else " (Need 3.8+)")
    )
    
    # Check required packages
    required_packages = [
        ("torch", "PyTorch"),
        ("transformers", "Transformers"),
        ("peft", "PEFT"),
        ("bitsandbytes", "BitsAndBytes (for 4-bit)"),
    ]
    
    for module_name, display_name in required_packages:
        spec = importlib.util.find_spec(module_name)
        installed = spec is not None
        all_good &= check_status(
            f"{display_name} Package",
            installed,
            "" if installed else f"Install with: pip install {module_name}"
        )
    
    # Check CUDA availability
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        check_status(
            "CUDA/GPU Available",
            cuda_available,
            f"GPU: {torch.cuda.get_device_name(0) if cuda_available else 'Not available (will use CPU - slower)'}"
        )
        
        if cuda_available:
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
            mem_ok = gpu_mem >= 6
            check_status(
                "GPU Memory",
                mem_ok,
                f"{gpu_mem:.1f} GB" + ("" if mem_ok else " (Need 6GB+ for 7B model)")
            )
    except ImportError:
        all_good &= check_status("CUDA/GPU Available", False, "PyTorch not installed")
    
    # Check profile configuration
    profile_path = Path(".agent/profile.yaml")
    profile_exists = profile_path.exists()
    all_good &= check_status(
        "Profile Configuration",
        profile_exists,
        str(profile_path) if profile_exists else "Missing .agent/profile.yaml"
    )
    
    if profile_exists:
        import yaml
        try:
            with open(profile_path) as f:
                profile = yaml.safe_load(f)
            
            # Check backend
            backend = profile.get("models", {}).get("backend")
            backend_ok = backend == "hf"
            check_status(
                "Backend Configuration",
                backend_ok,
                f"Using: {backend}" + ("" if backend_ok else " (Expected: hf)")
            )
            
            # Check model paths
            hf_config = profile.get("models", {}).get("hf", {})
            base_model = hf_config.get("base_model")
            adapter_dir = hf_config.get("adapter_dir")
            
            check_status(
                "Base Model",
                base_model == "mistralai/Mistral-7B-Instruct-v0.2",
                f"Set to: {base_model}"
            )
            
            check_status(
                "Adapter Directory",
                "kayastune7b_t4" in str(adapter_dir),
                f"Set to: {adapter_dir}"
            )
            
        except Exception as e:
            all_good &= check_status("Profile Parsing", False, str(e))
    
    # Check adapter files exist
    adapter_path = Path("brain_training/kayastune7b_t4/checkpoint-313")
    adapter_exists = adapter_path.exists()
    all_good &= check_status(
        "Adapter Files",
        adapter_exists,
        str(adapter_path) if adapter_exists else f"Not found: {adapter_path}"
    )
    
    if adapter_exists:
        adapter_config = adapter_path / "adapter_config.json"
        adapter_model = adapter_path / "adapter_model.safetensors"
        tokenizer_config = adapter_path / "tokenizer_config.json"
        
        check_status("  - adapter_config.json", adapter_config.exists())
        check_status("  - adapter_model.safetensors", adapter_model.exists())
        check_status("  - tokenizer_config.json", tokenizer_config.exists())
    
    # Check HuggingFace CLI
    import shutil
    hf_cli = shutil.which("huggingface-cli")
    check_status(
        "HuggingFace CLI",
        hf_cli is not None,
        "Found" if hf_cli else "Install with: pip install huggingface-hub[cli]"
    )
    
    # Check if logged in to HuggingFace
    hf_token_path = Path.home() / ".huggingface" / "token"
    hf_logged_in = hf_token_path.exists()
    check_status(
        "HuggingFace Login",
        hf_logged_in,
        "Logged in" if hf_logged_in else "Login with: huggingface-cli login"
    )
    
    # Summary
    print()
    print("=" * 70)
    if all_good and profile_exists and adapter_exists and hf_logged_in:
        print("✅ All checks passed! Your 7B model is ready to use.")
        print()
        print("Next steps:")
        print("  1. Run: python quick_test_7b.py")
        print("  2. Or:  python test_7b_model.py")
        print("  3. Or:  TEST_7B_MODEL.bat")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print()
        print("Common fixes:")
        if not hf_logged_in:
            print("  - Login to HuggingFace: huggingface-cli login")
        if not adapter_exists:
            print("  - Check adapter path: brain_training/kayastune7b_t4/checkpoint-313")
        if not all([importlib.util.find_spec(m) for m, _ in required_packages]):
            print("  - Install requirements: pip install -r requirements.txt")
    print("=" * 70)
    print()
    
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
