# Kayas AI Assistant: Virtual Agent with Voice & Desktop Control

A comprehensive AI assistant that combines voice interaction, desktop automation, web browsing, and API integrations. Talk to Kayas naturally or type commands - it can control your computer, browse the web, manage your calendar, and much more.

## ✨ Key Features
- 🗣️ **Voice Interaction**: Natural speech-to-text (Whisper) and text-to-speech conversation
- 🖥️ **Desktop Control**: Full Windows automation with OCR, image recognition, and clicking
- 🌐 **Web Browsing**: Interactive browser automation with session persistence
- 📅 **Integrations**: Google Calendar, Slack, Spotify control
- 🧠 **Smart Memory**: Persistent conversations with context awareness
- 🎯 **Local LLM**: Powered by Ollama (privacy-focused, runs offline)

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Install Ollama and Voice Components
```powershell
# Install Ollama (https://ollama.ai) and pull a model
ollama pull llama3.1

# Install Playwright browsers
python -m playwright install

# Optional: Install Tesseract for OCR (download from GitHub releases)
# Add tesseract.exe to your PATH
```

### 3. Enable Desktop Automation (Optional but Recommended)
```powershell
Set-Item Env:DESKTOP_AUTOMATION_ENABLED "1"
```

### 4. Launch Kayas
```powershell
# GUI Mode (recommended)
python kayas.py --gui

# Voice CLI Mode  
python kayas.py --continuous

# Text-only Mode
python kayas.py --no-voice
```

## 💬 Usage Examples

Once running, you can say or type:

**Desktop Control:**
- "Take a screenshot"
- "Click on the Start button"
- "Type 'hello world' and press Enter"
- "Find the text 'Settings' and click on it"

**Web Browsing:**
- "Go to google.com and search for Python tutorials"
- "Fill out the login form with my email"
- "Take a screenshot of this webpage"

**Productivity:**
- "Create a calendar event for tomorrow at 2 PM"
- "Send a Slack message to #general saying hello"
- "Play some jazz music on Spotify"

**File Management:**
- "Create a notes file about today's meeting"
- "Search my files for documents about Python"

## 🎙️ Voice Modes

### GUI Mode (Easiest)
```powershell
python kayas.py --gui
```
- Point-and-click interface
- Push-to-talk voice button
- Real-time conversation display

### Continuous Listening
```powershell
python kayas.py --continuous
```
- Always listening for wake words: "Hey Kayas", "Kayas"
- Hands-free operation
- Say "stop listening" to exit

### Push-to-Talk CLI
```powershell
python kayas.py
```
- Press Enter to start speaking
- Type messages directly
- Most reliable for noisy environments

## Run API server
```powershell
$env:OLLAMA_MODEL = "llama3.1"
uvicorn src.server.api:app --reload --port 8000
```
Then POST a goal:
```powershell
Invoke-RestMethod -Uri http://localhost:8000/agent/run -Method Post -Body (@{goal='Kayas, make a notes file about freelancing'} | ConvertTo-Json) -ContentType 'application/json'
```

### Tool routes
- Web fetch:
```powershell
Invoke-RestMethod -Uri http://localhost:8000/tools/web/fetch -Method Post -Body (@{url='https://example.com'} | ConvertTo-Json) -ContentType 'application/json'
```
- Local search:
```powershell
Invoke-RestMethod -Uri http://localhost:8000/tools/local/search -Method Post -Body (@{query='freelancing'} | ConvertTo-Json) -ContentType 'application/json'
```
- Email send:
```powershell
Invoke-RestMethod -Uri http://localhost:8000/tools/email/send -Method Post -Body (@{to='you@example.com'; subject='Hi'; body='Hello'} | ConvertTo-Json) -ContentType 'application/json'
```

- Google Calendar:
```powershell
# List upcoming events (7 days)
Invoke-RestMethod -Uri http://localhost:8000/tools/calendar/list_events -Method Post -Body (@{calendar_id='primary'; max_results=5; days_ahead=7} | ConvertTo-Json) -ContentType 'application/json'

# Create an event (ISO 8601 UTC times)
Invoke-RestMethod -Uri http://localhost:8000/tools/calendar/create_event -Method Post -Body (@{summary='Focus block'; start_time='2025-09-22T09:00:00Z'; end_time='2025-09-22T10:00:00Z'; description='Deep work'} | ConvertTo-Json) -ContentType 'application/json'
```

- Slack:
```powershell
# Send a message
Invoke-RestMethod -Uri http://localhost:8000/tools/slack/send_message -Method Post -Body (@{channel='#general'; text='Hello from agent'} | ConvertTo-Json) -ContentType 'application/json'

# List channels
Invoke-RestMethod -Uri http://localhost:8000/tools/slack/list_channels -Method Post -Body (@{types='public_channel,private_channel'; limit=50} | ConvertTo-Json) -ContentType 'application/json'
```

- Spotify:
```powershell
# Search tracks
Invoke-RestMethod -Uri http://localhost:8000/tools/spotify/search -Method Post -Body (@{query='jazz focus'; search_type='track'; limit=5} | ConvertTo-Json) -ContentType 'application/json'

# Play a specific track by URI
Invoke-RestMethod -Uri http://localhost:8000/tools/spotify/play -Method Post -Body (@{track_uri='spotify:track:xxxxxxxx'; device_id=$null} | ConvertTo-Json) -ContentType 'application/json'

# Play top result for a query
Invoke-RestMethod -Uri http://localhost:8000/tools/spotify/play_query -Method Post -Body (@{query='jazz for focus'} | ConvertTo-Json) -ContentType 'application/json'

# Currently playing
Invoke-RestMethod -Uri http://localhost:8000/tools/spotify/current -Method Get
```

- Browser automation (Playwright):
```powershell
# Example: go to example.com, take a screenshot
$steps = @(
  @{ action = 'goto'; args = @{ url = 'https://example.com' } },
  @{ action = 'wait_for_selector'; args = @{ selector = 'h1'; state = 'visible' } },
  @{ action = 'screenshot'; args = @{ full_page = $true; filename = 'example_home.png' } }
)
Invoke-RestMethod -Uri http://localhost:8000/tools/browser/run_steps -Method Post -Body (@{ steps = $steps; headless = $true } | ConvertTo-Json -Depth 6) -ContentType 'application/json'
```
Session persistence and login flow
```powershell
# Persisted session across runs (cookies/localStorage saved under .agent\browser_sessions\mySite.json)
$loginSteps = @(
  @{ action = 'goto'; args = @{ url = 'https://example.com/login' } },
  @{ action = 'login_flow'; args = @{ 
        url = 'https://example.com/login';
        username_selector = '#email';
        password_selector = '#password';
        username = 'user@example.com';
        password = 'P@ssw0rd!';
        submit_selector = 'button[type=submit]';
        success_selector = 'nav .profile';
        error_selector = '.error, .alert-danger';
        retry_count = 2; retry_delay_ms = 1500; wait_success_ms = 8000 } },
  @{ action = 'screenshot'; args = @{ filename = 'after_login.png' } }
)
Invoke-RestMethod -Uri http://localhost:8000/tools/browser/run_steps -Method Post -Body (
  @{ steps = $loginSteps; headless = $true; session_name = 'mySite'; persist_session = $true } | ConvertTo-Json -Depth 6
) -ContentType 'application/json'

# Next run can reuse session without re-login
$steps = @(
  @{ action = 'goto'; args = @{ url = 'https://example.com/account' } },
  @{ action = 'wait_for_selector'; args = @{ selector = 'h1'; state = 'visible' } },
  @{ action = 'screenshot'; args = @{ filename = 'account.png' } }
)
Invoke-RestMethod -Uri http://localhost:8000/tools/browser/run_steps -Method Post -Body (
  @{ steps = $steps; headless = $true; session_name = 'mySite' } | ConvertTo-Json -Depth 6
) -ContentType 'application/json'
```

Install Playwright (Windows):
```powershell
python -m pip install playwright
python -m playwright install
```

## Desktop automation (Windows)

Danger: This gives the agent control of your mouse and keyboard. Keep it disabled unless you understand the risks.

Enable (env or profile):
```powershell
$env:DESKTOP_AUTOMATION_ENABLED = "1"
```

Install packages:
```powershell
python -m pip install pyautogui opencv-python pytesseract pyperclip pygetwindow
```

Optional OCR on Windows: Install Tesseract and add to PATH
- Download: https://github.com/tesseract-ocr/tesseract (Windows installer)
- After installing, restart shell so `tesseract` is on PATH

Run steps via API:
```powershell
$steps = @(
  @{ action = 'screenshot'; args = @{ filename = 'desktop_before.png' } },
  @{ action = 'move_to'; args = @{ x = 100; y = 100; duration = 0.2 } },
  @{ action = 'click' },
  @{ action = 'write'; args = @{ text = 'hello world' } },
  @{ action = 'hotkey'; args = @{ keys = @('ctrl','s') } },
  @{ action = 'screenshot'; args = @{ filename = 'desktop_after.png' } }
)
Invoke-RestMethod -Uri http://localhost:8000/tools/desktop/run_steps -Method Post -Body (@{ steps = $steps } | ConvertTo-Json -Depth 6) -ContentType 'application/json'
```

Available actions (high-level):
- Mouse: `move_to(x,y,duration)`, `move_rel(dx,dy,duration)`, `click([x],[y])`, `double_click([x],[y])`, `right_click([x],[y])`, `middle_click([x],[y])`, `drag_to(x,y,duration)`, `drag_rel(dx,dy,duration)`
- Keyboard: `write(text)`, `paste([text])`, `hotkey(keys=[...])`, `key_down(key)`, `key_up(key)`
- Scrolling: `scroll(clicks,[x],[y])`, `hscroll(clicks,[x],[y])` (horizontal; may not be supported on all platforms)
- Screen/Image: `screenshot([filename],[region])`, `locate_on_screen(image,confidence)`, `wait_for_image(image,confidence,timeout_ms)`
- OCR/Text: `ocr_region(region,[lang])`, `find_text(text,[region],[lang])`, `locate_by_text(text,[region],[lang],[match],[return])`, `click_text(text,[region],[lang])`
- Clipboard: `get_clipboard`, `set_clipboard(text)`
- Windows: `list_windows`, `focus_window(title)`, `bring_to_front(title)`, `move_window(title,x,y)`

Example: Image wait + text click + hscroll
```powershell
$steps = @(
  @{ action = 'wait_for_image'; args = @{ image = 'c:/path/to/template.png'; confidence = 0.9; timeout_ms = 10000 } },
  @{ action = 'click_text'; args = @{ text = 'Settings'; lang = 'eng' } },
  @{ action = 'hscroll'; args = @{ clicks = -300 } }
)
Invoke-RestMethod -Uri http://localhost:8000/tools/desktop/run_steps -Method Post -Body (@{ steps = $steps } | ConvertTo-Json -Depth 6) -ContentType 'application/json'
```

Example: Locate text without clicking
```powershell
$steps = @(
  @{ action = 'locate_by_text'; args = @{ text = 'Download'; lang = 'eng'; match = 'equals'; return = 'first' } }
)
Invoke-RestMethod -Uri http://localhost:8000/tools/desktop/run_steps -Method Post -Body (@{ steps = $steps } | ConvertTo-Json -Depth 6) -ContentType 'application/json'
```

Example: Window control
```powershell
$steps = @(
  @{ action = 'bring_to_front'; args = @{ title = 'Notepad' } },
  @{ action = 'move_window'; args = @{ title = 'Notepad'; x = 50; y = 50 } }
)
Invoke-RestMethod -Uri http://localhost:8000/tools/desktop/run_steps -Method Post -Body (@{ steps = $steps } | ConvertTo-Json -Depth 6) -ContentType 'application/json'
```

Caveats:
- Horizontal scrolling (`hscroll`) might not be supported depending on your environment.
- Window control requires `pygetwindow`; some apps may block programmatic focusing/moving.
- OCR requires Tesseract installed and on PATH. Accuracy depends on font size, contrast, and language.
- The automation uses your real mouse/keyboard. Move your mouse to a screen corner to trigger PyAutoGUI FAILSAFE.

## Setup API integrations

Install extras:
```powershell
python -m pip install -r requirements.txt
```

Environment variables (PowerShell):
```powershell
# Google Calendar
$env:GOOGLE_CALENDAR_CREDENTIALS = "C:\path\to\client_secret.json"
$env:GOOGLE_CALENDAR_TOKEN = ".agent\google_token.json"

# Slack
$env:SLACK_BOT_TOKEN = "xoxb-..."
$env:SLACK_USER_TOKEN = "xoxp-..."

# Spotify
$env:SPOTIFY_CLIENT_ID = "your_client_id"
$env:SPOTIFY_CLIENT_SECRET = "your_client_secret"
$env:SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"
```

Notes:
- First-time Google Calendar use opens a browser for consent; a token is stored at `GOOGLE_CALENDAR_TOKEN`.
- Spotify playback requires an active device (e.g., open Spotify on your desktop or phone).
- Slack operations require the bot to be in the channel and proper OAuth scopes.
```

### API Integration routes
- Calendar events: `POST /tools/calendar/list_events`, `POST /tools/calendar/create_event`
- Slack messaging: `POST /tools/slack/send_message`, `POST /tools/slack/list_channels`
- Spotify control: `POST /tools/spotify/search`, `GET /tools/spotify/current`

See [API_INTEGRATIONS.md](API_INTEGRATIONS.md) for detailed setup and usage.

## Configuration
- `OLLAMA_MODEL` (default: `llama3.1`)
- `AGENT_LLM_BACKEND` (default: `ollama`; set to `hf` to use a Hugging Face model)
- HF backend (when `AGENT_LLM_BACKEND=hf`):
  - `HF_MERGED_MODEL_DIR` (preferred) path to a merged model directory
  - or `HF_BASE_MODEL` + `HF_ADAPTER_DIR` (LoRA adapter path)
  - `HF_USE_4BIT` (default: `1`) enable 4-bit loading when supported
- `AGENT_ARTIFACTS_DIR` (default: `artifacts`)
- `AGENT_DB_PATH` (default: `.agent/agent.db`)
- `CHROMA_DIR` (default: `.agent/chroma`)
- `EMBED_MODEL` (default: `nomic-embed-text`)
- `SEARCH_ROOT` (default: current directory)
- `PLANNING_MODE` (default: `structured`, options: `structured`, `react`)
- SMTP:
  - `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` (true)
- API Integrations (see [API_INTEGRATIONS.md](API_INTEGRATIONS.md)):
  - Google Calendar: `GOOGLE_CALENDAR_*` variables
  - Slack: `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN`
  - Spotify: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, etc.

## Notes
- Playwright not required; a lightweight web fetch/scrape path is included. You can add Playwright later for JS-heavy pages.
- Vector memory stores prior tasks/results and is consulted before planning to enable reuse.

## Use your fine-tuned model in the Agent (HF backend)

You can run Kayas with your fine-tuned QLoRA model (either merged or with an adapter):

```powershell
# Use a merged model directory
$env:AGENT_LLM_BACKEND = "hf"
$env:HF_MERGED_MODEL_DIR = "C:\\path\\to\\kayas-assistant-3b-merged"
$env:HF_USE_4BIT = "1"  # optional

# Or with base + adapter
$env:AGENT_LLM_BACKEND = "hf"
$env:HF_BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
$env:HF_ADAPTER_DIR = "C:\\path\\to\\checkpoint-297"
```

Then run the agent normally (GUI/CLI/API). The planner is already configured to emit JSON tool calls, and the parser was hardened to accept slightly noisy outputs.
