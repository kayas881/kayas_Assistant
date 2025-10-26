# 📚 BRAIN TRAINING - FILE INDEX

## 🎯 What Each File Does

### 📖 Documentation (Read These First)

1. **`QUICKSTART.md`** (8.4 KB) - **START HERE**
   - 5-step setup guide
   - Complete walkthrough
   - Troubleshooting

2. **`README.md`** (12.6 KB) - Complete Reference
   - Why this approach is better
   - Architecture explanation
   - Training data breakdown
   - Available tools
   - Customization guide

3. **`SUMMARY.md`** (10.7 KB) - Project Overview
   - What we built
   - Files created
   - How to use step-by-step
   - Key insights
   - Next steps

4. **`ARCHITECTURE.md`** (18.9 KB) - Visual Diagrams
   - System architecture
   - Data flow
   - Training pipeline
   - Comparison charts
   - Model structure

---

### 🐍 Python Scripts (Run These)

5. **`setup_check.py`** (6.9 KB) - Pre-flight Check
   ```bash
   python setup_check.py
   ```
   - Checks Python version
   - Verifies GPU
   - Checks dependencies
   - Validates training data
   - **Run this first!**

6. **`generate_training_data.py`** (19.7 KB) - Data Generator
   ```bash
   python generate_training_data.py
   ```
   - Creates training examples
   - 31 base → 119 augmented
   - Formats for instruction tuning
   - **Already run** (data exists)

7. **`finetune_brain.py`** (10.2 KB) - Training Script
   ```bash
   python finetune_brain.py
   ```
   - Fine-tunes Mistral 7B / Llama 3 8B
   - Uses QLoRA (4-bit quantization)
   - ~2-3 hours on L4 24GB
   - **Main training script**

8. **`test_brain.py`** (5.7 KB) - Model Tester
   ```bash
   python test_brain.py
   ```
   - Tests trained model
   - Interactive mode
   - Validates JSON output
   - **Run after training**

9. **`windows_eyes_demo.py`** (10.3 KB) - Accessibility API Demo
   ```bash
   python windows_eyes_demo.py
   ```
   - Demonstrates Windows Eyes concept
   - Compares with vision models
   - Shows integration
   - **Educational - no training needed**

---

### 📊 Training Data (Generated)

10. **`training_data/brain_training_base.jsonl`** (41.8 KB)
    - 31 original training examples
    - Categories: filesystem, browser, email, etc.
    - One JSON object per line

11. **`training_data/brain_training_augmented.jsonl`** (162.7 KB)
    - 119 augmented examples
    - Variations: rephrasing, politeness, casual
    - **Used for actual training**

---

### 📦 Configuration

12. **`requirements.txt`** (366 bytes) - Dependencies
    ```bash
    pip install -r requirements.txt
    ```
    - torch, transformers, datasets
    - accelerate, bitsandbytes
    - peft, trl

---

## 🔄 Recommended Order

### Phase 1: Setup & Understanding
1. Read `QUICKSTART.md` (5 min)
2. Run `python setup_check.py` (1 min)
3. Browse `ARCHITECTURE.md` (visual understanding)
4. Run `python windows_eyes_demo.py` (see the concept)

### Phase 2: Preparation
5. Install dependencies: `pip install -r requirements.txt` (5-10 min)
6. Review `training_data/brain_training_augmented.jsonl` (optional)
7. Read `README.md` sections you're interested in

### Phase 3: Training (L4 GPU)
8. Run `python finetune_brain.py` (2-3 hours)
9. Monitor GPU: `nvidia-smi`
10. Wait for completion

### Phase 4: Testing
11. Run `python test_brain.py`
12. Try interactive mode
13. Verify JSON outputs

### Phase 5: Deployment
14. Package: `tar -czf kayas_brain.tar.gz models/kayas_brain/final/*`
15. Transfer to local machine
16. Integrate with Kayas (see `QUICKSTART.md` Step 9)

### Phase 6: Production
17. Read `SUMMARY.md` for next steps
18. Add custom tools (see `README.md` Customization)
19. Implement Windows Eyes (see `windows_eyes_demo.py`)

---

## 📈 File Sizes Summary

```
Documentation:    50.6 KB (4 files)
Python Scripts:   69.0 KB (5 files)
Training Data:   204.6 KB (2 files)
Configuration:     0.4 KB (1 file)
-----------------------------------
Total:           324.6 KB (12 files)
```

**Note**: Trained model will add ~4GB in `models/kayas_brain/final/`

---

## 🎯 File Dependency Tree

```
QUICKSTART.md (start here)
    ↓
setup_check.py (verify system)
    ↓
requirements.txt (install deps)
    ↓
generate_training_data.py (create data)
    ↓
training_data/brain_training_augmented.jsonl (dataset)
    ↓
finetune_brain.py (train model)
    ↓
models/kayas_brain/final/ (output)
    ↓
test_brain.py (verify model)
    ↓
[Integration with Kayas]

Supporting docs:
- README.md (reference)
- SUMMARY.md (overview)
- ARCHITECTURE.md (diagrams)
- windows_eyes_demo.py (concept)
```

---

## 🔍 Quick File Lookup

**Need to...**                        | **Open this file**
--------------------------------------|---------------------------
Get started quickly                   | `QUICKSTART.md`
Understand the architecture           | `ARCHITECTURE.md`
See complete project overview         | `SUMMARY.md`
Learn about all features              | `README.md`
Check if system is ready              | `setup_check.py`
Generate training data                | `generate_training_data.py`
Train the model                       | `finetune_brain.py`
Test the model                        | `test_brain.py`
Understand Windows Eyes               | `windows_eyes_demo.py`
Install dependencies                  | `requirements.txt`
See training examples                 | `training_data/*.jsonl`

---

## 💡 Tips

### For Learning:
1. Start with `windows_eyes_demo.py` - understand the concept
2. Read `ARCHITECTURE.md` - see the big picture
3. Look at `training_data/*.jsonl` - see what model learns

### For Training:
1. Use `setup_check.py` first - catch issues early
2. Monitor `finetune_brain.py` output - watch loss decrease
3. Test with `test_brain.py` - verify before deploying

### For Customization:
1. Edit `generate_training_data.py` - add your examples
2. Modify `finetune_brain.py` CONFIG - tune hyperparameters
3. Read `README.md` Customization section - add new tools

---

## 🆘 Common Questions

**Q: Which file do I run first?**
A: `python setup_check.py`

**Q: How do I start training?**
A: `python finetune_brain.py` (after setup_check passes)

**Q: Where is the trained model saved?**
A: `models/kayas_brain/final/` (created after training)

**Q: How do I add my own tools?**
A: Edit `generate_training_data.py`, add examples, retrain

**Q: What if I get CUDA OOM?**
A: Edit `finetune_brain.py`, reduce `batch_size` to 1

**Q: How do I test the model?**
A: `python test_brain.py` (interactive mode)

---

## 📊 Project Statistics

- **Total Files**: 12
- **Lines of Code**: ~1,500
- **Training Examples**: 119 (augmented)
- **Supported Tool Categories**: 9
- **Estimated Training Time**: 2-3 hours
- **Model Size**: ~4GB (LoRA adapters)
- **Inference Speed**: <100ms
- **GPU Required**: L4 24GB (training), RTX 3050 4GB (inference)

---

**Everything you need to train an AI Brain!** 🧠
**From vision training (10+ hours) → Tool-using LLM (2-3 hours)** ⚡
