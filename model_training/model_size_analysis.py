"""
Analyze which Qwen2-VL models can fit in 24GB VRAM with QLoRA
"""

print("🔍 Model Size Analysis for 24GB VRAM with QLoRA\n")
print("="*70)

models = [
    {
        "name": "Qwen2-VL-2B-Instruct",
        "params": "2B",
        "base_size_gb": 4.8,
        "4bit_size_gb": 1.2,
        "recommended_vram_gb": 6,
        "training_vram_gb": 8,
        "speed": "⚡⚡⚡ Very Fast",
        "quality": "⭐⭐⭐ Good",
        "batch_size": "4-6",
        "notes": "Current choice - fast, efficient, good for UI tasks"
    },
    {
        "name": "Qwen2-VL-7B-Instruct",
        "params": "7B",
        "base_size_gb": 16.0,
        "4bit_size_gb": 4.0,
        "recommended_vram_gb": 12,
        "training_vram_gb": 16,
        "speed": "⚡⚡ Fast",
        "quality": "⭐⭐⭐⭐ Better",
        "batch_size": "2-3",
        "notes": "Fits in 24GB! Better quality, still fast"
    },
    {
        "name": "Qwen2-VL-72B-Instruct",
        "params": "72B",
        "base_size_gb": 144.0,
        "4bit_size_gb": 36.0,
        "recommended_vram_gb": 48,
        "training_vram_gb": 80,
        "speed": "⚡ Slow",
        "quality": "⭐⭐⭐⭐⭐ Best",
        "batch_size": "1 (gradient accum)",
        "notes": "❌ TOO LARGE for 24GB even with 4-bit"
    }
]

print("\n📊 Available Models:\n")

for model in models:
    print(f"🤖 {model['name']} ({model['params']})")
    print(f"   Base size: {model['base_size_gb']} GB")
    print(f"   4-bit quantized: {model['4bit_size_gb']} GB")
    print(f"   Training VRAM needed: ~{model['training_vram_gb']} GB")
    print(f"   Speed: {model['speed']}")
    print(f"   Quality: {model['quality']}")
    print(f"   Batch size with 24GB: {model['batch_size']}")
    print(f"   {model['notes']}")
    
    # Check if fits
    if model['training_vram_gb'] <= 24:
        print(f"   ✅ FITS in 24GB L4!")
    else:
        print(f"   ❌ Does NOT fit in 24GB")
    print()

print("="*70)
print("\n🎯 RECOMMENDATION for 24GB L4:\n")

print("Option 1: Qwen2-VL-2B (Current) ⚡")
print("   Pros:")
print("   • Trains FAST (~2-3 hours)")
print("   • Higher batch size (4-6)")
print("   • Less prone to overfitting")
print("   • Good enough for UI element detection")
print("   Cons:")
print("   • Smaller capacity")
print("   • May miss complex UI patterns")
print()

print("Option 2: Qwen2-VL-7B (Upgrade) ⭐")
print("   Pros:")
print("   • Better understanding of complex UIs")
print("   • Better generalization")
print("   • More robust to variations")
print("   • Still fits in 24GB with QLoRA!")
print("   Cons:")
print("   • Slower training (~4-5 hours)")
print("   • Smaller batch size (2-3)")
print("   • Download size: 16GB")
print()

print("="*70)
print("\n💡 MY RECOMMENDATION:")
print()
print("   🏆 Go with Qwen2-VL-7B-Instruct!")
print()
print("   Why?")
print("   • You have 24GB VRAM - use it!")
print("   • 7B is the sweet spot for vision-language tasks")
print("   • Better quality worth the extra time")
print("   • Still trains in 4-5 hours (fits in your 8-hour window)")
print("   • Your dataset is rich (1M+ elements) - 7B can leverage it better")
print()
print("   When to stick with 2B:")
print("   • If you need rapid iteration/experimentation")
print("   • If training time is critical")
print("   • If you're doing multiple training runs")
print()

print("="*70)
print("\n📈 Training Time Estimates (5,114 samples):")
print()
print("   Qwen2-VL-2B:")
print("   • Batch 4, Grad Accum 4 → ~2.5-3 hours")
print("   • Effective batch: 16")
print()
print("   Qwen2-VL-7B:")
print("   • Batch 2, Grad Accum 8 → ~4-5 hours")
print("   • Effective batch: 16")
print()

print("="*70)
print("\n🚀 To switch to 7B, update Cell 5 in your notebook:")
print()
print('   MODEL_NAME = "Qwen/Qwen2-VL-7B-Instruct"')
print('   BATCH_SIZE = 2  # Reduced for 7B')
print('   GRADIENT_ACCUMULATION_STEPS = 8  # Keep effective batch at 16')
print()
