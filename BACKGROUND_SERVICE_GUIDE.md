# 🎤 Kayas Always-On Background Service

Your AI assistant that wakes up when you say "Kayas" + your command!

## 🚀 Quick Start

### 1. Install Dependencies (if not already installed)

```powershell
pip install pystray pillow SpeechRecognition pyaudio pyttsx3
```

Or install all:
```powershell
pip install -r requirements.txt
```

### 2. Start the Background Service

**Option A: Simple Console Mode**
```powershell
python kayas_background.py
```

**Option B: System Tray (with icon)**
```powershell
python kayas_tray.py
```

**Option C: Double-click the batch file**
- `START_KAYAS_BACKGROUND.bat`

## 💬 How to Use

Once running, simply say:

```
"Kayas, [your command]"
```

### Examples:
- "Kayas, create a todo list"
- "Kayas, open Chrome and search for AI news"
- "Kayas, play some music on Spotify"
- "Kayas, what's my schedule today?"
- "Kayas, take a screenshot"

### Stop Listening:
- Say: "Kayas, stop listening"
- Or press `Ctrl+C` in the console

## 🔧 Auto-Start on Windows Boot

Run this to make Kayas start automatically when Windows starts:

```powershell
ENABLE_STARTUP.bat
```

This creates a shortcut in your Startup folder.

### Disable Auto-Start:
1. Press `Win+R`
2. Type: `shell:startup`
3. Delete `Kayas Background.lnk`

## ⚙️ Configuration

Edit `.agent/profile.yaml` to customize:

```yaml
models:
  backend: hf  # Uses your trained 3B model

voice:
  enabled: true
  response_style: "concise"
```

### Wake Words

Default wake words (case-insensitive):
- "kayas"
- "hey kayas"
- "okay kayas"

To change, edit `kayas_background.py`:
```python
voice_activation_keywords=["kayas", "hey kayas", "computer"]
```

## 🎯 Features

✅ **Always Listening** - Runs quietly in background  
✅ **Wake Word Activation** - Only responds when you say "Kayas"  
✅ **Voice Responses** - Speaks back to you  
✅ **Full Tool Access** - File operations, web browsing, automation, etc.  
✅ **System Tray** - Minimize to tray icon  
✅ **Auto-Start** - Start on Windows boot  

## 🛠️ Troubleshooting

### "Microphone not found" or "No audio input"
1. Check microphone is plugged in and not muted
2. Windows: Go to Settings → Privacy → Microphone → Allow apps
3. Install PyAudio: `pip install pyaudio`
   - On Windows, you may need: `pip install pipwin; pipwin install pyaudio`

### "pystray not installed"
```powershell
pip install pystray pillow
```

### Service crashes or doesn't respond
- Check `.agent/agent.db` (delete to reset)
- Restart: Stop the service (Ctrl+C) and run again
- Check microphone privacy settings in Windows

### High CPU usage
- Normal during voice processing
- Consider using system tray mode instead of console

## 📁 Files

| File | Purpose |
|------|---------|
| `kayas_background.py` | Main background service script |
| `kayas_tray.py` | System tray application |
| `START_KAYAS_BACKGROUND.bat` | Quick launcher |
| `ENABLE_STARTUP.bat` | Auto-start setup |

## 🔊 Voice Settings

The service uses:
- **Speech Recognition**: Google Web Speech API (requires internet)
- **Text-to-Speech**: pyttsx3 (offline, uses Windows voices)

For better offline recognition, install Whisper:
```powershell
pip install openai-whisper
```

## 🧠 Using Your Trained Model

The service automatically uses your trained 3B model configured in `.agent/profile.yaml`:

```yaml
models:
  backend: hf
  hf:
    base_model: "Qwen/Qwen2.5-3B-Instruct"
    adapter_dir: "brain_training/brain-lora-3b-single-gpu/kaggle/working/brain-lora-3b-single-gpu/checkpoint-297"
    use_4bit: true
```

First activation will load the model (~12 seconds), then all commands are fast!

## 💡 Tips

- **Speak clearly** and pause slightly after "Kayas"
- **Background noise**: Works best in quiet environments
- **Multiple commands**: Say "Kayas" for each new command
- **Wake word only**: Say just "Kayas" and it will prompt for your command

## 🎮 Advanced Usage

### Run as Windows Service

For true background operation, consider using NSSM (Non-Sucking Service Manager):

1. Download NSSM: https://nssm.cc/download
2. Install service:
   ```powershell
   nssm install Kayas "D:\kayas\.venv\Scripts\python.exe" "D:\kayas\kayas_background.py"
   nssm start Kayas
   ```

### Custom Actions

The agent supports all tool categories:
- File operations (create, read, delete, search)
- Process management (start programs, run commands)
- Web automation (browser control, searches)
- Desktop automation (click, type, screenshots)
- Integrations (Calendar, Slack, Spotify, Email)

Say "Kayas" + natural language and the 3B model will plan the actions!

