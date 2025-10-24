# 🚀 Quick Start: Advanced Autonomous Agent

## Prerequisites Check

```powershell
# 1. Check Ollama is running
ollama list

# 2. Pull required models
ollama pull llama3.1
ollama pull llava

# 3. Enable desktop automation
$env:DESKTOP_AUTOMATION_ENABLED = "1"

# 4. Run test suite
.\.venv\Scripts\python.exe test_advanced_agent.py
```

## Launch the Agent

```powershell
$env:DESKTOP_AUTOMATION_ENABLED = "1"
.\.venv\Scripts\python.exe kayas.py --gui
```

## Try These Commands

### 🖥️ Desktop UI Control

```
"open settings and lower my brightness"
"adjust volume to 50%"
"show me display settings"
"open control panel and change display"
"find the brightness slider and set it to maximum"
```

### 🌐 Web Automation

```
"open chatgpt and ask about artificial intelligence"
"go to youtube and search for python tutorials"
"open gmail and show unread emails"
"open whatsapp web"
```

### 🔄 Multi-Step Tasks

```
"take a screenshot and tell me what you see"
"open chrome, go to github, and show my repositories"
"navigate to display settings and enable dark mode"
"open task manager and show me CPU usage"
```

## How It Works

1. **You ask**: "open settings and lower brightness"
2. **Agent thinks**: "I need to open Settings first"
3. **Agent acts**: Opens Settings app
4. **Agent observes**: Takes screenshot, sees UI elements
5. **Agent thinks**: "I see System button, that's where Display is"
6. **Agent acts**: Clicks System
7. **Agent observes**: Takes screenshot, sees Display option
8. **Agent thinks**: "Now I click Display"
9. **Agent acts**: Clicks Display
10. **Agent observes**: Takes screenshot, sees brightness slider
11. **Agent acts**: Adjusts slider to lower value
12. **Agent finishes**: "I've lowered your brightness"

## Configuration Files

**`.agent/profile.yaml`** - Enable ReAct mode:
```yaml
planning:
  mode: "react"  # Use ReAct for complex tasks
  react:
    max_steps: 10
    beam_width: 3

desktop:
  enabled: true  # Required for UI tasks
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "model llava not found" | `ollama pull llava` |
| "Ollama connection error" | `ollama serve` |
| "Desktop automation disabled" | `$env:DESKTOP_AUTOMATION_ENABLED = "1"` |
| Vision analysis fails | Make sure Ollama is running with llava model |

## What's Different?

### Before (Structured Mode)

```
User: "open chrome"
Agent: [plans one action] → [executes] → Done
```

### After (ReAct Mode)

```
User: "open settings and lower brightness"
Agent: [thinks] → [acts] → [observes] → 
       [thinks] → [acts] → [observes] →
       [thinks] → [acts] → [observes] → Done
```

The agent can now:
- 👁️ **See** your screen after each action
- 🧠 **Reason** about what to do next
- 🔄 **Adapt** based on what it observes
- 🎯 **Navigate** complex UIs step-by-step

## Test It's Working

```powershell
# Run quick test
.\.venv\Scripts\python.exe -c "from src.voice.direct_agent import DirectAgent; agent = DirectAgent(); print(f'ReAct mode: {agent.planning_mode}'); print(f'ReAct agent available: {agent.react_agent is not None}')"

# Should show:
# [DirectAgent] Planning mode: react
# ReAct mode: react
# ReAct agent available: True
```

## Need Help?

See full documentation: `ADVANCED_AGENT.md`

---

**Ready?** Just say: **"open settings and lower my brightness"** 🎉
