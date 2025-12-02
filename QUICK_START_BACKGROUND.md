# 🎤 Kayas Background Service - Quick Reference

## Start the Service

```powershell
# Option 1: Console mode
python kayas_background.py

# Option 2: System tray (recommended)
python kayas_tray.py

# Option 3: Batch file
START_KAYAS_BACKGROUND.bat
```

## Usage

1. **Start the service** (using one of the commands above)
2. **Wait for** "Listening..." message
3. **Say**: "Kayas, [your command]"

### Examples:
```
Kayas, create a todo list
Kayas, open Chrome and search for Python tutorials
Kayas, play some music
Kayas, take a screenshot
```

## Stop the Service

- Say: "Kayas, stop listening"
- Press: `Ctrl+C`
- System tray: Right-click icon → Quit

## Auto-Start on Boot

Run once:
```powershell
ENABLE_STARTUP.bat
```

## Troubleshooting

**No microphone detected?**
- Check Settings → Privacy → Microphone
- Ensure mic is not muted
- Restart the service

**Not responding?**
- Speak clearly, pause after "Kayas"
- Check if service is running (console or tray icon)

**Full guide:** See `BACKGROUND_SERVICE_GUIDE.md`

---

**Using your trained 3B model!** 🧠  
First command loads the model (~12s), then fast responses.
