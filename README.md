# 🤖 Kayas AI Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![LLM](https://img.shields.io/badge/LLM-Qwen2.5-orange.svg)

**An intelligent, voice-enabled AI assistant that can automate your desktop, browse the web, and integrate with your favorite apps.**

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [Integrations](#-integrations)

</div>

---

## 🎯 Overview

Kayas is a **fully autonomous AI assistant** built from scratch that combines:

- 🎤 **Voice Control** — Natural speech input via Whisper ASR + Text-to-Speech responses
- 🖥️ **Desktop Automation** — Control any Windows application via UI Automation & PyAutoGUI
- 🌐 **Web Automation** — Playwright-based browser control with visual perception
- 🧠 **Local LLM** — Runs entirely offline using quantized Qwen2.5-3B with custom LoRA fine-tuning
- 🔌 **Multi-Platform Integrations** — WhatsApp, Slack, Spotify, GitHub, Jira, Notion, Google Calendar, and more

**No cloud APIs required** — your data stays on your machine.

### 🎥 Demo Video

<div align="center">
  <video width="560" height="315" controls>
    <source src="https://github.com/kayas881/kayas_Assistant/raw/main/demo/kayas_assistant%20-%20Made%20with%20Clipchamp.mp4" type="video/mp4">
    Your browser does not support the video tag.
  </video>
</div>

---

## ✨ Features

### 🎙️ Voice Interface
- **Wake-word detection** with continuous listening mode
- **Whisper-based STT** for accurate speech recognition
- **Natural TTS responses** via pyttsx3
- **Conversation memory** — remembers context across sessions

### 🖥️ Desktop Automation
- **UI Automation** (pywinauto) — Interact with any Windows application
- **OCR-based fallback** (Tesseract) — Read text from any screen element
- **Computer Vision** — OpenCV-powered visual element detection
- **Multi-layer perception engine** — Combines UIA + OCR + Vision for maximum reliability

### 🌐 Web Automation
- **Playwright browser control** — Headless or visible Chrome/Firefox
- **Session persistence** — Stay logged in across restarts
- **Smart element detection** — CSS selectors + visual matching
- **WhatsApp Web automation** — Full messaging, media, groups, and more

### 🧠 AI Planning & Execution
- **Structured JSON tool-calls** — Reliable, parseable output format
- **ReAct reasoning mode** — Think step-by-step for complex tasks
- **Multi-step execution** — Break down complex goals into subtasks
- **Safety guardrails** — Blocks dangerous operations

### 📊 Memory & Learning
- **SQLite conversation memory** — Persistent chat history
- **Vector memory** (ChromaDB) — Semantic search over past interactions
- **Fine-tuning pipeline** — Train custom LoRA adapters on your usage patterns

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KAYAS ASSISTANT                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Voice UI   │    │   Chat GUI   │    │   CLI Mode   │       │
│  │   (STT/TTS)  │    │  (Tkinter)   │    │   (Rich)     │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │               │
│         └───────────────────┴───────────────────┘               │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                    AGENT CORE                           │    │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐   │    │
│  │  │ Planner │  │ Executor │  │ Router  │  │  Safety  │   │    │
│  │  │  (LLM)  │  │ Manager  │  │         │  │ Checker  │   │    │
│  │  └─────────┘  └──────────┘  └─────────┘  └──────────┘   │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                    LLM BACKENDS                         │    │
│  │  ┌──────────┐  ┌───────────────┐  ┌─────────────────┐   │    │
│  │  │  Ollama  │  │  HuggingFace  │  │   HTTP Remote   │   │    │
│  │  │  (API)   │  │  (4-bit+LoRA) │  │   (Any API)     │   │    │
│  └──────────┘  └───────────────┘  └─────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                     EXECUTORS                           │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐    │    │
│  │  │Desktop  │  │ Browser │  │WhatsApp │  │ Spotify  │    │    │
│  │  │(UIA+CV) │  │(Playwrt)│  │  (Web)  │  │  (API)   │    │    │
│  │  ├─────────┤  ├─────────┤  ├─────────┤  ├──────────┤    │    │
│  │  │  Slack  │  │  GitHub │  │  Jira   │  │  Notion  │    │    │
│  │  │  (SDK)  │  │  (API)  │  │  (API)  │  │  (API)   │    │    │
│  │  ├─────────┤  ├─────────┤  ├─────────┤  ├──────────┤    │    │
│  │  │Calendar │  │  Email  │  │Filesys  │  │  Audio   │    │    │
│  │  │(Google) │  │ (SMTP)  │  │ (Local) │  │(Record)  │    │    │
│  └─────────┘  └─────────┘  └─────────┘  └──────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                      MEMORY                             │    │
│  │  ┌────────────────┐        ┌─────────────────────────┐  │    │
│  │  │ SQLite Memory  │        │  ChromaDB Vector Store  │  │    │
│  │  │ (Conversations)│        │  (Semantic Search)      │  │    │
│  └────────────────┘        └─────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.10+**
- **Windows 10/11** (for desktop automation features)
- **Tesseract OCR** — [Download here](https://github.com/UB-Mannheim/tesseract/wiki)
- **Chrome/Chromium** (for browser automation)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/kayas881/kayas_Assistant.git
cd kayas_Assistant

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the assistant
python kayas.py
```

### Configuration

Create a `.env` file for API keys (optional):

```env
# Optional integrations
SLACK_BOT_TOKEN=xoxb-...
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
GITHUB_TOKEN=ghp_...
JIRA_API_TOKEN=...
NOTION_TOKEN=...
```

---

## 💻 Usage

### Command Line

```bash
# Interactive CLI mode
python kayas.py

# GUI mode
python kayas.py --gui

# Voice-enabled mode
python kayas.py --continuous

# Disable voice (text-only)
python kayas.py --no-voice
```

### Example Commands

```
# Desktop Automation
"Open Notepad and type Hello World"
"Take a screenshot and save it to my desktop"
"Find the Chrome window and click the search bar"

# Web Automation
"Search Google for Python tutorials"
"Open YouTube and play some music"

# WhatsApp (NEW!)
"Send a WhatsApp message to John saying I'll be late"
"Read my unread WhatsApp messages"
"Send image C:\Photos\vacation.jpg to Family Group"

# Productivity
"Add a meeting to my calendar for tomorrow at 3pm"
"Create a new Jira ticket for the login bug"
"Send a Slack message to #general"

# Media
"Play my liked songs on Spotify"
"Skip to the next track"

# System
"What processes are using the most CPU?"
"Open the folder D:\Projects"
```

---

## 🔌 Integrations

| Integration | Status | Description |
|-------------|--------|-------------|
| **WhatsApp Web** | ✅ Complete | Send/receive messages, media, groups, contacts |
| **Spotify** | ✅ Complete | Playback control, playlists, search |
| **Slack** | ✅ Complete | Send messages, read channels, manage threads |
| **GitHub** | ✅ Complete | Create issues, PRs, manage repos |
| **Google Calendar** | ✅ Complete | Create/read/update events |
| **Jira** | ✅ Complete | Create issues, update status, search |
| **Notion** | ✅ Complete | Create pages, update databases |
| **Email (SMTP)** | ✅ Complete | Send emails with attachments |
| **Trello** | ✅ Complete | Create cards, manage boards |
| **Local Files** | ✅ Complete | Read, write, search, organize |

---

## 🧠 LLM Configuration

Kayas supports multiple LLM backends:

### 1. Ollama (Recommended for beginners)
```bash
# Install Ollama, then:
ollama pull qwen2.5:3b
```

### 2. HuggingFace Local (Best performance)
- Uses 4-bit quantization for low VRAM usage
- Custom LoRA fine-tuning included
- Runs entirely offline

### 3. Remote HTTP API
- Connect to any OpenAI-compatible API
- Use cloud models when needed

---

## 📁 Project Structure

```
kayas/
├── kayas.py                 # Main entry point
├── requirements.txt         # Python dependencies
├── src/
│   ├── agent/               # Core AI agent logic
│   │   ├── planner.py       # LLM-based task planning
│   │   ├── actions.py       # Action router
│   │   ├── execution_manager.py
│   │   ├── llm.py           # Ollama backend
│   │   ├── hf_llm.py        # HuggingFace backend
│   │   └── safety.py        # Safety guardrails
│   ├── executors/           # Platform integrations
│   │   ├── desktop_exec.py  # Windows UI automation
│   │   ├── browser_exec.py  # Playwright web control
│   │   ├── whatsapp_exec.py # WhatsApp Web automation
│   │   ├── spotify_exec.py  # Spotify control
│   │   └── ...              # 15+ more executors
│   ├── voice/               # Voice interface
│   │   ├── stt.py           # Speech-to-text (Whisper)
│   │   ├── tts.py           # Text-to-speech
│   │   └── gui.py           # Tkinter GUI
│   └── memory/              # Persistence layer
│       ├── sqlite_memory.py # Conversation storage
│       └── vector_memory.py # Semantic search
├── brain_training/          # Fine-tuning pipeline
│   ├── finetuning.py        # LoRA training script
│   └── final_adapter/       # Trained model weights
└── artifacts/               # Generated outputs
```

---

## 🎓 Technical Highlights

### Multi-Layer Perception Engine
The desktop automation uses a **3-layer perception system**:

1. **UI Automation (pywinauto)** — Direct access to Windows accessibility APIs
2. **OCR (Tesseract)** — Extract text from any visual element
3. **Computer Vision (OpenCV)** — Template matching and visual detection

This ensures maximum reliability across all Windows applications.

### Structured Tool Calling
The LLM outputs structured JSON tool calls:
```json
{
  "tool": "whatsapp.send_message",
  "args": {
    "contact": "John",
    "message": "Hey, running late!"
  }
}
```

This is more reliable than free-form text parsing and enables complex multi-step workflows.

### Session Persistence
- Browser sessions saved to disk — stay logged into WhatsApp, etc.
- Conversation memory persists across restarts
- Vector embeddings enable semantic search over history

---

## 🛠️ Development

### Running Tests
```bash
pytest test_planner.py -v
```

### Fine-tuning the Model
```bash
cd brain_training
python finetuning.py
```

### Adding New Executors
1. Create `src/executors/my_exec.py`
2. Register tools in `src/agent/planner.py`
3. Add routing in `src/agent/actions.py`

---

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Kayas** — [GitHub](https://github.com/kayas881)

---

<div align="center">

**Built with ❤️ and Python**

*If you find this project useful, please give it a ⭐!*

</div>