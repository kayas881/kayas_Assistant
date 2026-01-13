# 🤖 Kayas AI Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![LLM](https://img.shields.io/badge/LLM-Qwen3--32B-orange.svg)
![Voice](https://img.shields.io/badge/Voice-Edge%20TTS-green.svg)

**An intelligent, voice-enabled AI assistant that understands you, remembers everything, and automates your digital life.**

[Features](#-features) • [Demo](#-demo) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [Voice Mode](#-voice-mode)

</div>

---

## 🎥 Demo

<div align="center">
  <video src="https://github.com/user-attachments/assets/84f3ddf8-f055-472e-9134-be1e9cbe1cfa" width="60%"> </video>
</div>

---

## 🎯 Overview

Kayas is a **fully autonomous AI assistant** — not just a chatbot, but an actual AI friend that:

- 🧠 **Understands Context** — Uses Qwen3-32B with deep reasoning capabilities
- 💬 **Remembers Everything** — Persistent memory across sessions (1000+ messages)
- 🎤 **Natural Voice** — Microsoft Edge neural TTS + wake word detection ("Hey Kayas")
- 🖥️ **Controls Your PC** — Desktop automation, web browsing, file management
- 📱 **App Integrations** — WhatsApp, Spotify, GitHub, Jira, Notion, Calendar, and more
- 🔧 **Function Calling** — Reliable structured tool execution via JSON

---

## ✨ Features

### 🧠 AI Brain (Qwen3-32B-AWQ)
- **Thinking Mode** — Deep reasoning with `<think>` blocks for complex tasks
- **Function Calling** — Structured JSON tool calls for reliable execution
- **Personality System** — Remembers your name, preferences, relationships
- **Session Continuity** — Picks up where you left off, even after restarts

### 🎙️ Voice Interface (NEW!)
- **Edge TTS** — Natural Microsoft neural voices (Jenny, Aria, Guy)
- **Wake Word Detection** — "Hey Kayas" activation with accent support
- **Continuous Listening** — Always-on mode with low CPU usage
- **faster-whisper STT** — Accurate speech recognition (small model, 484MB)

### 🖥️ Desktop Automation
- **UI Automation** (pywinauto) — Control any Windows application
- **Multi-Layer Perception** — UIA + OCR + Computer Vision combined
- **Smart Clicking** — Handles dropdowns, menus, dynamic elements
- **Screenshot Analysis** — OCR-based fallback for any screen element

### 🌐 Web & App Control
- **Playwright Browser** — Headless or visible Chrome/Firefox
- **WhatsApp Web** — Full messaging, media, groups, reply-to-message
- **Spotify** — Playback control, search, playlists
- **GitHub/Jira/Notion** — Issue tracking, project management

### 📊 Memory System
- **SQLite Database** — Persistent conversation history
- **User Profile** — Name, preferences, timezone, interests
- **Contact Relationships** — Remembers who your friends are
- **Vector Memory** — Semantic search over past conversations

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KAYAS ASSISTANT                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Voice Mode  │    │   CLI Mode   │    │   Web GUI    │       │
│  │(Edge TTS+STT)│    │   (Rich)     │    │   (HTML)     │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         └───────────────────┴───────────────────┘               │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                   DIRECT AGENT                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │    │
│  │  │SmartExecutor │  │   Planner    │  │    Safety    │   │    │
│  │  │(Tool Router) │  │  (Thinking)  │  │  Guardrails  │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                    LLM BACKEND                          │    │
│  │  ┌────────────────────────────────────────────────┐     │    │
│  │  │   vLLM (Qwen3-32B-AWQ) via ngrok/Kaggle        │     │    │
│  │  │   - Function calling with tools                │     │    │
│  │  │   - Thinking mode for complex reasoning        │     │    │
│  │  │   - Custom fine-tuned adapter                  │     │    │
│  │  └────────────────────────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                     EXECUTORS                           │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐    │    │
│  │  │Desktop  │  │ Browser │  │WhatsApp │  │ Spotify  │    │    │
│  │  │(UIA+CV) │  │(Playwrt)│  │  (Web)  │  │  (API)   │    │    │
│  │  ├─────────┤  ├─────────┤  ├─────────┤  ├──────────┤    │    │
│  │  │Explorer │  │  GitHub │  │  Jira   │  │  Notion  │    │    │
│  │  │  (UIA)  │  │  (API)  │  │  (API)  │  │  (API)   │    │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                      MEMORY                             │    │
│  │  ┌────────────────┐  ┌─────────────┐  ┌─────────────┐   │    │
│  │  │ SQLite Memory  │  │User Profile │  │  Contacts   │   │    │
│  │  │ (1000+ msgs)   │  │(Name, Prefs)│  │(Friendships)│   │    │
│  │  └────────────────┘  └─────────────┘  └─────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.10+**
- **Windows 10/11** (for desktop automation)
- **Tesseract OCR** — [Download](https://github.com/UB-Mannheim/tesseract/wiki)
- **Chrome** (for browser automation)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/kayas881/kayas.git
cd kayas

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the assistant
python kayas.py
```

### Voice Mode Dependencies

```bash
# For voice features
pip install edge-tts faster-whisper sounddevice pygame
```

### Configuration

Create a `.env` file:

```env
# LLM Backend (vLLM via ngrok)
VLLM_BASE_URL=https://your-ngrok-url.ngrok-free.dev
VLLM_MODEL=Qwen/Qwen3-32B-AWQ

# Optional integrations
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
GITHUB_TOKEN=ghp_...
```

---

## 💻 Usage

### Command Line Modes

```bash
# Interactive CLI (default)
python kayas.py

# Voice mode with wake word
python kayas.py --continuous

# Text-only mode
python kayas.py --no-voice

# Push-to-talk voice
python kayas.py
```

### Example Commands

```
# Casual conversation
"Hey, how's it going?"
"Remember my friend Abdus? He's the one I play games with."

# Desktop Automation
"Open Notepad and type Hello World"
"Take a screenshot and save it"

# WhatsApp
"Send a message to Abdus saying I'll be online soon"
"Read my unread WhatsApp messages"

# Web
"Search Google for Python tutorials"
"Open YouTube and play some music"

# Productivity
"What's on my calendar today?"
"Create a Jira ticket for the login bug"
```

---

## 🎙️ Voice Mode

### Wake Word Activation

Say **"Hey Kayas"** (or variations like "Hey Guys", "Hey Kaya") to activate.

Supported wake words:
- "Hey Kayas", "Hi Kayas", "Kayas"
- "Hey Guys" (common Whisper transcription for accents)
- "Hey Chaos", "Hey Kaya", "Hey Gaia"

### Voice Settings

- **TTS Voice**: Microsoft Jenny (natural, friendly)
- **STT Model**: faster-whisper small (484MB, good accuracy)
- **Wake Word**: Whisper tiny for low-latency detection

### Accent Support

The wake word detector includes phonetic variations for Indian and other accents. If Whisper transcribes "Kayas" differently, it will still trigger.

---

## 🧠 AI Capabilities

### Thinking Mode
For complex tasks, Kayas uses deep reasoning:
```
User: "Should I learn React or Vue for my project?"

Kayas: <think>
Let me consider the user's context...
- They mentioned being a beginner earlier
- React has more job opportunities
- Vue is easier to learn
</think>

Given that you're just starting out, I'd recommend Vue first...
```

### Function Calling
Reliable tool execution via structured JSON:
```json
{
  "tool": "whatsapp.send_message",
  "args": {
    "contact": "Abdus",
    "message": "Hey, I'll be online in 10 mins!"
  }
}
```

### Memory & Personalization
- Remembers your name, preferences, timezone
- Tracks relationships (friends, family, colleagues)
- References past conversations naturally

---

## 📁 Project Structure

```
kayas/
├── kayas.py                 # Main entry point
├── requirements.txt         # Dependencies
├── index.html               # Web GUI
├── src/
│   ├── agent/               # AI core
│   │   ├── direct_agent.py  # Main agent class
│   │   ├── smart_executor.py # Function calling
│   │   ├── planner.py       # Task planning
│   │   ├── http_llm.py      # vLLM backend
│   │   └── safety.py        # Safety checks
│   ├── executors/           # Tool implementations
│   │   ├── whatsapp_exec.py # WhatsApp automation
│   │   ├── desktop_exec.py  # Windows UI control
│   │   ├── browser_exec.py  # Web automation
│   │   ├── spotify_exec.py  # Music control
│   │   └── ...              # 15+ more
│   ├── voice/               # Voice interface
│   │   ├── edge_tts.py      # Microsoft neural TTS
│   │   ├── wake_word.py     # Wake word detection
│   │   ├── enhanced_voice.py # Combined voice agent
│   │   └── chat_agent.py    # Voice + AI integration
│   └── memory/              # Persistence
│       ├── sqlite_memory.py # Conversation DB
│       ├── user_profile.py  # User preferences
│       └── session_continuity.py # Session awareness
└── brain_training/          # Fine-tuning
    ├── finetuning.py        # LoRA training
    └── final_adapter/       # Trained weights
```

---

## 🔌 Integrations

| Integration | Status | Description |
|-------------|--------|-------------|
| **WhatsApp Web** | ✅ Complete | Messages, media, groups, reply-to |
| **Spotify** | ✅ Complete | Playback, search, playlists |
| **GitHub** | ✅ Complete | Issues, PRs, repos |
| **Jira** | ✅ Complete | Issues, status, search |
| **Notion** | ✅ Complete | Pages, databases |
| **Google Calendar** | ✅ Complete | Events, reminders |
| **File Explorer** | ✅ Complete | Navigate, create, organize |
| **Desktop Apps** | ✅ Complete | Any Windows application |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Qwen3-32B-AWQ via vLLM |
| **Inference** | Kaggle GPU + ngrok tunnel |
| **TTS** | Microsoft Edge TTS (neural voices) |
| **STT** | faster-whisper (OpenAI Whisper) |
| **Desktop Automation** | pywinauto + PyAutoGUI |
| **Web Automation** | Playwright |
| **OCR** | Tesseract + EasyOCR |
| **Computer Vision** | OpenCV |
| **Database** | SQLite |
| **Vector Search** | ChromaDB |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Ayan (Kayas)** — [GitHub](https://github.com/kayas881)

---

<div align="center">

**Built with ❤️ and Python**

*Kayas — Your AI friend that actually understands.*

</div>
