# 🧠 Kayas AI Brain Training

**Train a small, fast LLM to be an expert "Tool User" for your AI assistant.**

Instead of training a vision model to guess what's on screen, we:
1. **Use Windows Accessibility API** (the "Eyes") - 100% accurate, instant, free
2. **Train an LLM** (the "Brain") - Learns to call the right tools for any command

---

## 🎯 Why This Approach is Better

### ❌ Old Approach: Vision Model
- Train AI to "see" pixels → guess what buttons are
- Requires: Expensive GPU training (10+ hours)
- Accuracy: ~80-90%
- Inference: Slow (100-500ms)
- Cost: High

### ✅ New Approach: Accessibility API + Tool-Using LLM
- **Eyes (Accessibility API)**: OS already knows what's on screen
  - 100% accurate
  - Instant (<1ms)
  - Free
- **Brain (Fine-tuned LLM)**: Learns to call the right tools
  - Faster training (2-3 hours)
  - Better at reasoning
  - Works on your RTX 3050 locally

---

## 🏗️ Architecture

```
USER COMMAND
    ↓
BRAIN (Fine-tuned Mistral 7B)
    ↓ (outputs JSON tool calls)
    ↓
ROUTER (src/agent/actions.py)
    ↓
EXECUTORS (filesystem, browser, email, uiautomation, etc.)
    ↓ (use Accessibility API for UI)
    ↓
EYES (Windows UIAutomation)
    ↓
ACTION EXECUTED ✅
```

### Example Flow:

1. **User says**: "Kayas, save this file"
2. **Brain decides**: `[{"tool": "uia.click_button", "args": {"window_title": "Notepad", "button_text": "Save"}}]`
3. **Eyes execute**: Find Notepad → Find "Save" button → Click at exact coordinates
4. **Result**: File saved ✅

---

## 📦 What's Included

### 1. `generate_training_data.py`
- Creates synthetic training examples
- Teaches LLM to output JSON tool calls
- Categories: filesystem, browser, email, process, clipboard, UI automation, etc.
- **Augmentation**: Generates variations (rephrasing, politeness, casual)

**Output**: `training_data/brain_training_augmented.jsonl` (~200+ examples)

### 2. `finetune_brain.py`
- Fine-tunes **Mistral 7B** or **Llama 3 8B**
- Uses **QLoRA** (4-bit quantization) - fits in 24GB GPU
- **Training time**: ~2-3 hours on L4 24GB
- **Result**: Small, fast LLM that outputs perfect JSON tool calls

### 3. `test_brain.py`
- Test your trained model
- Interactive mode for live testing
- Validates JSON output

### 4. `windows_eyes_demo.py`
- Demonstrates Windows Accessibility API
- Shows why it's better than vision models
- Integration guide

---

## 🚀 Quick Start

### Step 1: Generate Training Data

```bash
cd brain_training
python generate_training_data.py
```

**Output**:
- `training_data/brain_training_base.jsonl` - Base examples (~50)
- `training_data/brain_training_augmented.jsonl` - Augmented (~250+)

### Step 2: Install Dependencies (on L4 GPU machine)

```bash
pip install -r requirements.txt
```

**Required packages**:
- `torch` - PyTorch
- `transformers` - Hugging Face models
- `datasets` - Data loading
- `accelerate` - Distributed training
- `bitsandbytes` - 4-bit quantization
- `peft` - LoRA adapters
- `trl` - Instruction fine-tuning

### Step 3: Train the Brain (L4 24GB GPU)

```bash
python finetune_brain.py
```

**Configuration** (in `finetune_brain.py`):
```python
CONFIG = {
    "model_name": "mistralai/Mistral-7B-Instruct-v0.2",  # or Llama 3 8B
    "batch_size": 2,
    "gradient_accumulation_steps": 8,  # Effective batch = 16
    "num_epochs": 3,
    "learning_rate": 2e-4,
    "max_seq_length": 2048,
    "lora_r": 16,
    "lora_alpha": 32,
}
```

**Expected**:
- Training time: ~2-3 hours
- Memory usage: ~20-22GB VRAM
- Final model size: ~4GB (LoRA adapters only)

### Step 4: Test the Model

```bash
python test_brain.py
```

**Interactive mode**:
```
You: Create a file called todo.txt
AI Brain: [{"tool": "filesystem.create_file", "args": {"filename": "todo.txt", "content": ""}}]

You: Open YouTube and search for AI tutorials
AI Brain: [{"tool": "browser.run_steps", "args": {"steps": [...]}}]
```

### Step 5: Copy to Local Machine (RTX 3050)

The trained model is small (~4GB) and will run on your RTX 3050:

```bash
# On L4 machine
cd brain_training/models/kayas_brain/final
tar -czf kayas_brain.tar.gz *

# Copy to local machine
scp kayas_brain.tar.gz user@local-machine:~/

# On local machine
tar -xzf kayas_brain.tar.gz
```

### Step 6: Integrate with Kayas Assistant

Update `src/agent/planner.py` to use the trained Brain:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

class BrainPlanner:
    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
        base_model = AutoModelForCausalLM.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.2",
            device_map="auto",
            torch_dtype=torch.float16
        )
        self.model = PeftModel.from_pretrained(base_model, model_path)
        self.model.eval()
    
    def plan(self, user_command: str) -> List[Action]:
        # Generate tool calls
        response = self._generate(user_command)
        # Parse JSON
        tools = json.loads(response)
        return [Action(tool=t["tool"], args=t["args"]) for t in tools]
```

---

## 📊 Training Data Breakdown

### Categories:
- **Filesystem** (5 examples → 25 augmented): Create, append, delete, archive files
- **Browser** (3 → 15): Navigate, search, fill forms
- **Email** (2 → 10): Send emails
- **Process** (4 → 20): Start programs, run commands
- **Clipboard** (3 → 15): Copy, paste, history
- **UI Automation** (5 → 25): Click buttons, type text, close windows
- **Multi-step** (4 → 20): Complex workflows
- **Spotify** (3 → 15): Play, pause, search music
- **Slack** (2 → 10): Send messages, search

**Total**: ~50 base → ~250+ augmented examples

### Example Training Sample:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are Kayas, an AI assistant that helps users by calling tools..."
    },
    {
      "role": "user",
      "content": "Create a new file called meeting_notes.txt"
    },
    {
      "role": "assistant",
      "content": "[{\"tool\": \"filesystem.create_file\", \"args\": {\"filename\": \"meeting_notes.txt\", \"content\": \"\"}}]"
    }
  ],
  "category": "filesystem",
  "explanation": "Direct file creation command"
}
```

---

## 🎮 Available Tools (Your Executors)

The Brain can call any of these tools:

### Filesystem
- `filesystem.create_file` - Create new file
- `filesystem.append_file` - Add content to file
- `filesystem.delete_file` - Delete file
- `filesystem.archive_file` - Move to archive

### Browser
- `browser.run_steps` - Execute browser automation (goto, click, fill, etc.)

### Email
- `email.send` - Send email

### Process
- `process.start_program` - Launch application
- `process.run_command` - Execute shell command
- `process.get_system_info` - Get CPU/RAM/disk info
- `process.kill_process` - Terminate process
- `process.list_processes` - List running processes

### Clipboard
- `clipboard.copy_text` - Copy text
- `clipboard.paste_text` - Get clipboard content
- `clipboard.get_history` - Clipboard history

### UI Automation (uses Accessibility API)
- `uia.click_button` - Click button by text/ID
- `uia.type_text` - Type into input field
- `uia.close_window` - Close window
- `uia.list_windows` - Get all open windows
- `uia.get_control_tree` - Get accessibility tree
- `uia.find_window` - Find window by title

### Spotify
- `spotify.play_query` - Search and play
- `spotify.pause_playback` - Pause
- `spotify.get_current_playing` - Current track

### Slack
- `slack.send_message` - Post to channel
- `slack.search_messages` - Search history

### Others
- `local.search` - Search local files
- And more in `src/executors/`...

---

## 🧪 Example Outputs

### Simple Command
**Input**: "Create a todo list"
**Output**:
```json
[
  {
    "tool": "filesystem.create_file",
    "args": {
      "filename": "todo.txt",
      "content": ""
    }
  }
]
```

### Complex Command
**Input**: "Open Chrome, search for Python tutorials, and take a screenshot"
**Output**:
```json
[
  {
    "tool": "process.start_program",
    "args": {
      "program": "chrome.exe",
      "background": true
    }
  },
  {
    "tool": "browser.run_steps",
    "args": {
      "steps": [
        {"action": "goto", "args": {"url": "https://www.google.com/search?q=Python+tutorials"}},
        {"action": "wait", "args": {"seconds": 2}},
        {"action": "screenshot", "args": {"filename": "python_search.png"}}
      ]
    }
  }
]
```

---

## 🔧 Customization

### Add Your Own Tools

1. **Create executor** in `src/executors/`:
```python
class MyCustomExecutor:
    def my_action(self, arg1: str, arg2: int) -> Dict[str, Any]:
        # Your code here
        return {"status": "success"}
```

2. **Register in Router** (`src/agent/actions.py`):
```python
if t == "custom.my_action":
    return self.executors["custom"].my_action(a["arg1"], a["arg2"])
```

3. **Add training examples** (`generate_training_data.py`):
```python
CUSTOM_EXAMPLES = [
    TrainingExample(
        user_command="Do my custom action",
        tools_sequence=[
            {"tool": "custom.my_action", "args": {"arg1": "test", "arg2": 42}}
        ],
        explanation="Custom action example",
        category="custom"
    ),
]
```

4. **Retrain the model** with new examples

---

## 💡 Tips & Tricks

### For Better Results:
1. **Add more examples** for tasks you do often
2. **Use augmentation** to create variations
3. **Test early** - catch issues before full training
4. **Start small** - Test with base dataset first
5. **Lower temperature** (0.1-0.3) for more deterministic output

### Memory Optimization:
- Already using QLoRA (4-bit) - fits in 24GB
- Gradient checkpointing enabled
- Batch size 2 + grad accumulation 8 = effective batch 16

### Speed Optimization:
- Sequences are short (tool calls ~100-300 tokens)
- Max length 2048 (vs 8192 for vision models)
- No image processing overhead
- Training: ~2-3 hours on L4

---

## 🐛 Troubleshooting

### CUDA Out of Memory
- Reduce `batch_size` to 1
- Increase `gradient_accumulation_steps` to 16
- Already using 4-bit quantization (lowest possible)

### Model outputs invalid JSON
- Lower temperature (0.1-0.3)
- Add more examples with correct JSON format
- Use `json.loads()` validation in training data generation

### Tool not working
- Check if tool is registered in `src/agent/actions.py`
- Verify executor exists in `src/executors/`
- Add examples for that specific tool

---

## 📚 Resources

### Windows Accessibility API:
- **pywinauto**: https://pywinauto.readthedocs.io/
- **UIAutomation**: https://docs.microsoft.com/en-us/windows/win32/winauto/uiauto-uiautomationoverview

### Model Training:
- **QLoRA Paper**: https://arxiv.org/abs/2305.14314
- **PEFT Library**: https://github.com/huggingface/peft
- **TRL (Transformer RL)**: https://github.com/huggingface/trl

### Your Existing Code:
- Executors: `src/executors/`
- Router: `src/agent/actions.py`
- Planner: `src/agent/planner.py`

---

## 🎯 Roadmap

### Phase 1: Core Brain ✅
- [x] Generate training data
- [x] Fine-tune Mistral 7B
- [x] Test model outputs
- [x] Validate JSON format

### Phase 2: Integration (Next)
- [ ] Replace old planner with Brain
- [ ] Add Brain to voice pipeline
- [ ] Test end-to-end: Voice → Brain → Tools → Action

### Phase 3: Eyes Implementation
- [ ] Implement Windows Eyes (pywinauto)
- [ ] Parse accessibility tree
- [ ] Integrate with UIAutomation executor

### Phase 4: Mobile (Future)
- [ ] Android Eyes (Accessibility Service)
- [ ] iOS Eyes (NSAccessibility)

---

## 🤝 Contributing

Add more training examples! Categories to expand:
- Calendar actions
- GitHub integration
- Jira/Notion
- Computer vision (for when Accessibility API isn't enough)
- Video/audio processing

---

## 📄 License

Same as main Kayas project.

---

## 🙏 Acknowledgments

This approach is inspired by:
- **Screen readers** (pioneered Accessibility APIs)
- **Tool-using LLMs** (GPT-4 function calling, ReAct paper)
- **QLoRA** (makes LLM training accessible)

---

**Built with ❤️ for Kayas AI Assistant**
