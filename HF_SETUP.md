# Using Your Fine-Tuned Model - Setup Guide

## Problem: HuggingFace Authentication Required

The Qwen/Qwen2.5-3B-Instruct base model requires HuggingFace authentication to download.

## Solution: Choose One Approach

### Option A: Login to HuggingFace (Recommended)

1. Get a HuggingFace token:
   - Go to https://huggingface.co/settings/tokens
   - Create a new token (read access is sufficient)
   - Copy the token

2. Login via CLI:
```powershell
huggingface-cli login
# Paste your token when prompted
```

3. Update profile to use HF backend:
Edit `.agent/profile.yaml`:
```yaml
models:
  backend: hf
```

4. Run the agent:
```powershell
C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/.venv/Scripts/python.exe -m src.agent.main "Your prompt here"
```

### Option B: Use Ollama (Temporary Workaround)

The agent currently defaults to Ollama. Install Ollama and pull a model:

```powershell
# Install Ollama from https://ollama.ai
ollama pull llama3.1

# Then run the agent
python -m src.agent.main "Create a notes file about freelancing"
```

### Option C: Download Base Model Manually (Advanced)

If you have the base model files from Kaggle or elsewhere:

1. Copy the base model directory to your local machine
2. Update `.agent/profile.yaml`:
```yaml
models:
  backend: hf
  hf:
    base_model: "/path/to/local/Qwen2.5-3B-Instruct"
    adapter_dir: "C:/Users/KAYAS/Desktop/kayasWorkPlace/kayas/brain_training/brain-lora-3b-single-gpu/kaggle/working/brain-lora-3b-single-gpu/checkpoint-297"
```

## Current Status

- Your fine-tuned LoRA adapter is ready at:
  `brain_training/brain-lora-3b-single-gpu/kaggle/working/brain-lora-3b-single-gpu/checkpoint-297`

- Agent is temporarily set to use Ollama backend (you can switch back to `hf` after auth)

- Config files updated:
  - Planning mode: `structured` (faster JSON tool calls)
  - Max steps: 15 (increased from default)
  - All dependencies installed

## Next Steps

1. **Quick test with Ollama** (if installed):
   ```powershell
   python -m src.agent.main "Create a notes file about AI trends"
   ```

2. **Or setup HF auth** and switch to your trained model:
   - Follow Option A above
   - Change `backend: hf` in `.agent/profile.yaml`
   - Rerun the agent

## Files Modified

- `.agent/profile.yaml` - persistent config (HF paths set, temporarily using ollama)
- `src/agent/hf_llm.py` - HF backend loader
- `src/agent/actions.py` - robust JSON parsing
- `requirements.txt` - added HF deps
