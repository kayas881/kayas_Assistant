# 🤖 Advanced Autonomous Agent - ReAct Mode

## Overview

Your Kayas assistant now has **advanced autonomous capabilities** using the **ReAct (Reasoning and Acting) agent model**. This enables it to handle complex, multi-step tasks that require:

- 👁️ **Visual perception** (seeing what's on screen)
- 🧠 **Step-by-step reasoning** (thinking about what to do next)
- 🎯 **Action execution** (clicking buttons, adjusting sliders, navigating UIs)
- 🔄 **Iterative learning** (observing results and adapting)

## What's New?

### 1. Multi-Step Task Execution

The agent can now handle tasks like:

```
"open settings and lower my brightness"
```

**What happens behind the scenes:**

1. **Thought**: "I need to open the Settings app first"
2. **Action**: Opens Settings (`ms-settings:`)
3. **Observation**: Takes screenshot, analyzes UI → sees "System", "Display", etc.
4. **Thought**: "I can see Settings. Brightness is under System → Display"
5. **Action**: Clicks "System" button
6. **Observation**: Takes screenshot → sees "Display", "Sound", "Power"
7. **Thought**: "Perfect, now I click Display"
8. **Action**: Clicks "Display"
9. **Observation**: Takes screenshot → sees brightness slider
10. **Thought**: "Found the brightness slider"
11. **Action**: `uia.set_slider_value(target="Brightness", value=30)`
12. **Finish**: "I've lowered your brightness to 30%"

### 2. Vision-Powered UI Understanding

The agent can now "see" your screen using AI vision models:

- Takes screenshots after each action
- Uses LLaVA vision model to analyze what's visible
- Identifies buttons, sliders, text fields, menus
- Understands UI layout and navigation paths

### 3. Advanced UI Controls

New tools for manipulating complex UI elements:

- **`uia.set_slider_value()`** - Adjust sliders (brightness, volume, etc.)
- **`uia.select_dropdown()`** - Select items from dropdowns/comboboxes
- **`uia.check_checkbox()`** - Check/uncheck checkboxes
- **`perception.smart_click()`** - Click buttons intelligently (tries multiple methods)
- **`perception.get_screen_elements()`** - List all clickable elements

### 4. Web Automation

Handle web-based tasks like:

```
"open chatgpt and ask it about quantum computing"
```

The agent will:
1. Open browser and navigate to ChatGPT
2. Find the input field
3. Type your question
4. Click send
5. Read and return the response

## How to Use

### Enable ReAct Mode

ReAct mode is configured in `.agent/profile.yaml`:

```yaml
planning:
  mode: "react"  # Enable ReAct mode
  react:
    max_steps: 10  # Max reasoning steps
    beam_width: 3  # Actions to consider per step

desktop:
  enabled: true  # Required for UI tasks
```

### Example Commands

#### Desktop UI Tasks

```
✅ "open settings and lower brightness"
✅ "go to control panel and change display settings"
✅ "find the volume control and set it to 50%"
✅ "adjust my screen brightness to maximum"
✅ "open task manager and show me running processes"
```

#### Web Tasks

```
✅ "open chatgpt and ask about AI safety"
✅ "go to youtube and search for python tutorials"
✅ "open gmail and show me unread messages"
✅ "open whatsapp web and send a message"
```

#### Complex Multi-Step Tasks

```
✅ "open chrome, go to github, and create a new repository"
✅ "take a screenshot, analyze it, and tell me what you see"
✅ "open settings, navigate to display, and enable dark mode"
```

## Architecture

### ReAct Loop

```
┌─────────────────────────────────────────┐
│  User: "open settings and lower         │
│         brightness"                      │
└──────────────┬──────────────────────────┘
               │
               ▼
        ┌──────────────┐
        │   THOUGHT    │  "I need to open Settings"
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │   ACTION     │  process.start_program('ms-settings:')
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ OBSERVATION  │  📸 Screenshot → 🤖 Vision Analysis
        └──────┬───────┘  "I see Settings with System, Network..."
               │
               ▼
        ┌──────────────┐
        │   THOUGHT    │  "I found Settings. Now click System"
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │   ACTION     │  perception.smart_click('System')
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ OBSERVATION  │  📸 Screenshot → 🤖 Vision Analysis
        └──────┬───────┘  "I see Display, Sound, Power..."
               │
               ▼
             (continues until task complete)
```

### Perception Engine Layers

The agent tries multiple methods to interact with UI (in order):

1. **Layer A - UI Automation** (pywinauto): Most reliable, uses Windows APIs
2. **Layer B - App-Specific** (Selenium for browsers): Browser automation
3. **Layer C - Computer Vision** (OpenCV): Template/image matching
4. **Layer D - OCR** (Tesseract): Text-based fallback

### Tools Available to ReAct Agent

**Process Control:**
- `process.start_program` - Launch applications
- `process.kill_process` - Close applications
- `process.list_processes` - Show running processes

**Perception & UI:**
- `perception.smart_click` - Click UI elements
- `perception.smart_type` - Type text into fields
- `perception.smart_read` - Read screen text
- `perception.get_screen_elements` - List clickable elements

**UI Automation:**
- `uia.click_button` - Click buttons
- `uia.type_text` - Type into text fields
- `uia.set_slider_value` - Adjust sliders
- `uia.select_dropdown` - Select dropdown items
- `uia.check_checkbox` - Check/uncheck boxes

**Browser:**
- `browser.run_steps` - Execute browser automation scripts
  - `goto` - Navigate to URL
  - `click` - Click element
  - `fill` - Fill form field
  - `type` - Type text
  - `extract_text` - Get text from page

**Computer Vision:**
- `cv.find_image` - Find image on screen
- `cv.click_image` - Click on image
- `cv.screenshot` - Capture screen

**OCR:**
- `ocr.find_text` - Find text on screen
- `ocr.click_text` - Click on text
- `ocr.read_screen` - Read all screen text

## Requirements

### Software

1. **Python 3.13+** with virtual environment
2. **Ollama** with models:
   - `llama3.1` - Main reasoning model
   - `llava` - Vision model for screen analysis
3. **Desktop automation enabled**

### Install Vision Model

```powershell
ollama pull llava
```

### Enable Desktop Automation

```powershell
$env:DESKTOP_AUTOMATION_ENABLED = "1"
```

## Testing

Run the comprehensive test suite:

```powershell
$env:DESKTOP_AUTOMATION_ENABLED = "1"
.\.venv\Scripts\python.exe test_advanced_agent.py
```

This tests:
- ✅ ReAct mode initialization
- ✅ Complex task detection
- ✅ Perception tools availability
- ✅ Slider/control manipulation
- ✅ Vision model availability
- ✅ ReAct workflow simulation

## Configuration

### Planning Mode

Choose between two modes in `.agent/profile.yaml`:

**Structured Mode** (default for simple tasks):
```yaml
planning:
  mode: "structured"
```
- One-shot planning
- Fast execution
- Best for single-step tasks

**ReAct Mode** (for complex tasks):
```yaml
planning:
  mode: "react"
```
- Iterative reasoning
- Vision-based observation
- Best for multi-step, UI navigation tasks

### Auto-Detection

The agent automatically chooses the right mode:

**Simple tasks** → Structured mode:
- "open chrome"
- "copy this text"
- "check my CPU"

**Complex tasks** → ReAct mode:
- "open settings and lower brightness"
- "find the volume button and click it"
- "open chatgpt and ask about AI"

## Troubleshooting

### Vision Model Errors

**Problem**: `model 'llava' not found`

**Solution**:
```powershell
ollama pull llava
```

### UI Automation Unavailable

**Problem**: `UI Automation not available: [WinError -2147417850]`

**Solution**: This is expected. The agent uses the UIA proxy subprocess, which works around this issue. UI automation will still function via the perception engine.

### Desktop Automation Disabled

**Problem**: Tasks fail with "desktop automation not enabled"

**Solution**:
```powershell
$env:DESKTOP_AUTOMATION_ENABLED = "1"
```

Or set in `.agent/profile.yaml`:
```yaml
desktop:
  enabled: true
```

### Ollama Not Running

**Problem**: Connection errors or "model not found"

**Solution**:
```powershell
ollama serve
```

## Limitations

1. **Vision analysis requires Ollama** to be running locally
2. **Screen observation adds latency** (~2-3 seconds per step)
3. **Max steps limited** to prevent infinite loops (default: 10)
4. **Windows only** for desktop UI automation
5. **Some UIs** may not be accessible via automation (DRM, games, etc.)

## Future Enhancements

- 🔮 **Memory across sessions**: Remember previous interactions
- 🎯 **User preference learning**: Adapt to your workflow patterns
- 🌐 **Cloud vision models**: Faster, more accurate screen analysis
- 📱 **Mobile app support**: Extend to Android/iOS automation
- 🤝 **Collaborative agents**: Multiple agents working together

## Examples in Action

### Example 1: Brightness Control

**User**: "lower my screen brightness"

**ReAct Execution**:
```json
{
  "step": 1,
  "thought": "Need to open Windows Settings to access display controls",
  "action": {"tool": "process.start_program", "args": {"program": "ms-settings:"}},
  "observation": "Screenshot shows Settings app with categories: System, Devices, Network..."
}
{
  "step": 2,
  "thought": "I can see Settings opened. Brightness is under System → Display",
  "action": {"tool": "perception.smart_click", "args": {"target": "System"}},
  "observation": "Screenshot shows System page with Display, Sound, Notifications..."
}
{
  "step": 3,
  "thought": "Found System settings. Now click Display",
  "action": {"tool": "perception.smart_click", "args": {"target": "Display"}},
  "observation": "Screenshot shows Display settings with brightness slider visible"
}
{
  "step": 4,
  "thought": "Perfect! I can see the brightness slider. Setting it to 40%",
  "action": {"tool": "uia.set_slider_value", "args": {"window_title": "Settings", "target": "Brightness", "value": 40}},
  "observation": "Slider set successfully"
}
{
  "finish": "I've lowered your screen brightness to 40%"
}
```

### Example 2: ChatGPT Query

**User**: "open chatgpt and ask about quantum computing"

**ReAct Execution**:
```json
{
  "step": 1,
  "thought": "This is a web task. I'll use browser automation",
  "action": {"tool": "browser.run_steps", "args": {"steps": [
    {"action": "goto", "args": {"url": "https://chat.openai.com"}}
  ]}},
  "observation": "Browser opened ChatGPT website"
}
{
  "step": 2,
  "thought": "Now I need to find the chat input and type the question",
  "action": {"tool": "browser.run_steps", "args": {"steps": [
    {"action": "fill", "args": {"selector": "textarea", "text": "Explain quantum computing"}},
    {"action": "click", "args": {"selector": "button[type='submit']"}}
  ]}},
  "observation": "Question submitted, ChatGPT is responding"
}
{
  "step": 3,
  "thought": "Let me wait for the response and extract it",
  "action": {"tool": "browser.run_steps", "args": {"steps": [
    {"action": "wait", "args": {"milliseconds": 3000}},
    {"action": "extract_text", "args": {"selector": ".response-text"}}
  ]}},
  "observation": "Response text: 'Quantum computing is...'"
}
{
  "finish": "ChatGPT responded: [response text here]"
}
```

---

## 🎉 Start Using It!

1. Make sure Ollama is running: `ollama serve`
2. Pull vision model: `ollama pull llava`
3. Enable desktop automation: `$env:DESKTOP_AUTOMATION_ENABLED = "1"`
4. Launch GUI: `python kayas.py --gui`
5. Try: **"open settings and lower brightness"**

Your agent is now truly autonomous! 🚀
