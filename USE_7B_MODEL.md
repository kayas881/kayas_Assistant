# Using Your Trained 7B Model (kayastune7b_t4)

Your fine-tuned **Mistral-7B** model is now integrated into the Kayas AI Assistant! 🎉

## Model Details

- **Base Model**: `mistralai/Mistral-7B-Instruct-v0.2`
- **Fine-tuned Adapter**: `brain_training/kayastune7b_t4/checkpoint-313`
- **Training**: LoRA fine-tuning with DeepSpeed Zero Stage 2
- **Quantization**: 4-bit (NF4) for memory efficiency

## Quick Start

### 1. Test the Model Directly

Run the test script to see your model in action:

```powershell
python test_7b_model.py
```

This will:
- Load your trained 7B model
- Run automated tests with various commands
- Enter interactive mode for manual testing

### 2. Use in the Full Agent

The model is already configured in `.agent/profile.yaml`. Just run the agent:

```powershell
python -m src.agent.main "Create a summary file about AI trends in 2024"
```

Or with the voice interface:

```powershell
python kayas.py --gui
```

## Configuration

The model is configured in `.agent/profile.yaml`:

```yaml
models:
  backend: hf
  hf:
    base_model: "mistralai/Mistral-7B-Instruct-v0.2"
    adapter_dir: "brain_training/kayastune7b_t4/checkpoint-313"
    use_4bit: true
```

### Change Checkpoints

You have 3 checkpoints available:
- `checkpoint-250` - Early training checkpoint
- `checkpoint-300` - Mid training checkpoint  
- `checkpoint-313` - **Latest (currently active)**

To switch checkpoints, edit `.agent/profile.yaml`:

```yaml
adapter_dir: "brain_training/kayastune7b_t4/checkpoint-250"
```

## Memory Requirements

The 7B model with 4-bit quantization requires:
- **GPU**: ~5-6 GB VRAM (with 4-bit quantization)
- **CPU**: Will work but be slower
- **RAM**: 8-16 GB recommended

If you get OOM (Out of Memory) errors:
1. Close other applications
2. Reduce `max_new_tokens` in generation
3. Consider using a smaller model (3B version)

## Model Capabilities

Your 7B model was trained to:
- ✅ Generate structured JSON tool calls
- ✅ Route commands to appropriate executors
- ✅ Understand file operations, web tasks, desktop automation
- ✅ Handle multi-step planning
- ✅ Provide intelligent command interpretation

## Comparison with Other Models

| Model | Size | Speed | Accuracy | Memory |
|-------|------|-------|----------|--------|
| **kayastune7b_t4** | 7B | Medium | High | 6GB |
| kayas-brain-3b | 3B | Fast | Good | 3GB |
| Ollama (llama3) | 8B+ | Fast | Good | Varies |

## Advanced Usage

### Using with HF Inference Server

Start the inference server for remote access:

```powershell
python -m src.server.hf_inference_server
```

Then configure another machine to use it:

```yaml
models:
  backend: http
  remote:
    base_url: "http://your-server-ip:8000"
```

### Merge Adapter (Optional)

For faster loading, merge the LoRA adapter into the base model:

```powershell
cd brain_training
python merge_adapter.py ^
  --base_model "mistralai/Mistral-7B-Instruct-v0.2" ^
  --adapter_path "kayastune7b_t4/checkpoint-313" ^
  --output_dir "kayas-brain-7b-merged"
```

Then update `.agent/profile.yaml`:

```yaml
models:
  hf:
    base_model: "brain_training/kayas-brain-7b-merged"
    adapter_dir: ""  # Leave empty for merged models
```

## Troubleshooting

### Model Loading Errors

**Problem**: `OSError: Can't load config for 'mistralai/Mistral-7B-Instruct-v0.2'`

**Solution**: Login to HuggingFace:
```powershell
huggingface-cli login
```

### Out of Memory

**Problem**: CUDA out of memory error

**Solutions**:
1. Enable 4-bit quantization (should already be on)
2. Close other GPU applications
3. Reduce batch size if training
4. Use CPU inference (slower):
   ```yaml
   hf:
     use_4bit: false
   ```

### Slow Generation

**Problem**: Model takes too long to respond

**Solutions**:
1. Reduce `max_new_tokens` in generation
2. Use beam width = 1 for faster inference
3. Consider the 3B model for faster responses
4. Ensure you're using GPU, not CPU

### Wrong Responses

**Problem**: Model gives incorrect or nonsensical responses

**Solutions**:
1. Check if using the correct checkpoint (313 is latest)
2. Adjust temperature (lower = more deterministic)
3. Verify training data quality
4. Retrain with more epochs if needed

## Next Steps

1. **Test thoroughly**: Try various command types
2. **Compare checkpoints**: Test all 3 checkpoints to find the best
3. **Collect feedback**: Save failed commands for retraining
4. **Fine-tune further**: Use the feedback to improve the model

## Training History

Your model was trained with:
- DeepSpeed Zero Stage 2 optimization
- LoRA rank 8, alpha 32
- Target modules: q_proj, v_proj
- Multiple training checkpoints saved

See `brain_training/kayastune7b_t4/checkpoint-313/trainer_state.json` for detailed training metrics.

## Files Created/Modified

- ✅ `.agent/profile.yaml` - Configuration for 7B model
- ✅ `test_7b_model.py` - Direct model testing script
- ✅ `USE_7B_MODEL.md` - This guide
- ✅ `src/agent/hf_llm.py` - Already supports LoRA adapters
- ✅ `src/agent/config.py` - Already supports HF backend

Your 7B model is ready to use! 🚀
