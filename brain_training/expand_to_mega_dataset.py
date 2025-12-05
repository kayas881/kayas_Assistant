import json
import random
from pathlib import Path
from typing import List, Dict, Any
import itertools
import argparse
from datetime import datetime, timedelta


# Load existing datasets
def load_jsonl(path: Path) -> List[Dict]:
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


# Helper: Generate realistic timestamps and filenames
def get_timestamp() -> str:
    """Random recent timestamp"""
    days_ago = random.randint(0, 30)
    dt = datetime.now() - timedelta(days=days_ago)
    return dt.strftime("%Y%m%d_%H%M%S")

def get_date_str() -> str:
    """Readable date string"""
    days_ago = random.randint(0, 30)
    dt = datetime.now() - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d")

def get_dynamic_filename(base: str, ext: str = "txt") -> str:
    """Generate realistic filenames with timestamps/versions"""
    patterns = [
        f"{base}_{get_timestamp()}.{ext}",
        f"{base}_v{random.randint(1,5)}.{ext}",
        f"{base}_{get_date_str()}.{ext}",
        f"{base}_final.{ext}",
        f"{base}_backup.{ext}",
    ]
    return random.choice(patterns)

def get_project_name() -> str:
    """Realistic project names"""
    projects = [
        "kayas_assistant", "client_portal", "ml_pipeline", "api_gateway",
        "dashboard_v2", "mobile_app", "data_migration", "auth_service",
        "payment_system", "analytics_engine", "notification_service"
    ]
    return random.choice(projects)

def get_person_name() -> str:
    """Common names for emails/messages"""
    names = ["John", "Sarah", "Mike", "Emily", "David", "Lisa", "Alex", "Maria", "Chris", "Nina"]
    return random.choice(names)

def get_email_domain() -> str:
    """Realistic email domains"""
    domains = ["company.com", "team.io", "startup.dev", "enterprise.org", "project.net"]
    return random.choice(domains)


# Semantic paraphrasing templates (not just politeness)
COMMAND_TEMPLATES = [
    # Direct
    "{command}",
    # Natural variations
    "I need to {command}",
    "Help me {command}",
    "Time to {command}",
    "Let's {command}",
    # Contextual
    "Can you {command} for me",
    "Would you {command} real quick",
    "Mind {command}ing",
    # Implicit/indirect
    "I should {command}",
    "Gotta {command}",
    "Need you to {command}",
]


# === DEEP SCENARIO GENERATORS (Dynamic, Realistic) ===

def generate_filesystem_scenarios() -> List[tuple]:
    """Generate diverse filesystem scenarios with realistic args"""
    scenarios = []
    
    # Backups with timestamps
    project = get_project_name()
    scenarios.append((
        f"Create a backup of {project}",
        [{"tool": "filesystem.archive_file", "args": {"filename": f"backups/{project}_backup_{get_timestamp()}.zip"}}]
    ))
    
    # Logs with dates
    scenarios.append((
        f"Save today's work log",
        [{"tool": "filesystem.create_file", "args": {
            "filename": f"logs/work_log_{get_date_str()}.md",
            "content": f"# Work Log - {get_date_str()}\n\n## Tasks Completed\n- \n\n## Notes\n- \n"
        }}]
    ))
    
    # Meeting notes
    person = get_person_name()
    scenarios.append((
        f"Create meeting notes for {person}",
        [{"tool": "filesystem.create_file", "args": {
            "filename": f"meetings/{person}_meeting_{get_date_str()}.txt",
            "content": f"Meeting with {person} - {get_date_str()}\n\nAgenda:\n1. \n\nAction Items:\n- \n"
        }}]
    ))
    
    # Project structure
    scenarios.append((
        "Set up a new project folder",
        [
            {"tool": "filesystem.create_file", "args": {"filename": f"{get_project_name()}/README.md", "content": "# Project\n\n## Setup\n\n## Usage\n"}},
            {"tool": "filesystem.create_file", "args": {"filename": f"{get_project_name()}/requirements.txt", "content": ""}},
        ]
    ))
    
    # Archive old files
    scenarios.append((
        "Archive last month's reports",
        [{"tool": "filesystem.archive_file", "args": {"filename": f"archive/reports_{datetime.now().strftime('%Y_%m')}.zip"}}]
    ))
    
    # Journal entries
    scenarios.append((
        "Add entry to my journal",
        [{"tool": "filesystem.append_file", "args": {
            "filename": "personal/journal.md",
            "content": f"\n\n## {get_date_str()}\n\n"
        }}]
    ))
    
    # Config files
    scenarios.append((
        "Create a config file for the API",
        [{"tool": "filesystem.create_file", "args": {
            "filename": "config/api_config.json",
            "content": '{\n  "host": "localhost",\n  "port": 8000,\n  "debug": true\n}\n'
        }}]
    ))
    
    # Error: missing directory
    scenarios.append((
        "Save the deployment script",
        [{"tool": "filesystem.create_file", "args": {
            "filename": "scripts/deploy.sh",
            "content": "#!/bin/bash\n\necho 'Deploying...'\n"
        }}]
    ))
    
    return scenarios


def generate_browser_scenarios() -> List[tuple]:
    """Generate realistic browser automation scenarios"""
    scenarios = []
    
    # Research tasks
    topics = ["machine learning", "kubernetes deployment", "react hooks", "python async", "database optimization"]
    topic = random.choice(topics)
    scenarios.append((
        f"Search for {topic} documentation",
        [{
            "tool": "browser.run_steps",
            "args": {
                "steps": [
                    {"action": "goto", "args": {"url": f"https://google.com/search?q={topic.replace(' ', '+')}+documentation"}},
                    {"action": "screenshot", "args": {"filename": f"research/{topic.replace(' ', '_')}_search.png"}}
                ]
            }
        }]
    ))
    
    # GitHub workflow
    scenarios.append((
        "Check my GitHub notifications",
        [{
            "tool": "browser.run_steps",
            "args": {
                "steps": [
                    {"action": "goto", "args": {"url": "https://github.com/notifications"}},
                ]
            }
        }]
    ))
    
    # Email check
    scenarios.append((
        "Open my inbox",
        [{
            "tool": "browser.run_steps",
            "args": {
                "steps": [
                    {"action": "goto", "args": {"url": "https://gmail.com"}},
                    {"action": "wait", "args": {"ms": 2000}}
                ]
            }
        }]
    ))
    
    # LinkedIn job search
    scenarios.append((
        "Search for remote developer jobs",
        [{
            "tool": "browser.run_steps",
            "args": {
                "steps": [
                    {"action": "goto", "args": {"url": "https://linkedin.com/jobs"}},
                    {"action": "fill", "args": {"selector": "input.jobs-search-box__text-input", "value": "remote developer"}},
                    {"action": "click", "args": {"selector": "button.jobs-search-box__submit-button"}}
                ]
            }
        }]
    ))
    
    # Stack Overflow
    scenarios.append((
        "Look up Python error handling best practices",
        [{
            "tool": "browser.run_steps",
            "args": {
                "steps": [
                    {"action": "goto", "args": {"url": "https://stackoverflow.com/search?q=python+error+handling+best+practices"}}
                ]
            }
        }]
    ))
    
    # Product search
    scenarios.append((
        "Search Amazon for wireless keyboard",
        [{
            "tool": "browser.run_steps",
            "args": {
                "steps": [
                    {"action": "goto", "args": {"url": "https://amazon.com"}},
                    {"action": "fill", "args": {"selector": "input#twotabsearchtextbox", "value": "wireless keyboard"}},
                    {"action": "click", "args": {"selector": "input#nav-search-submit-button"}}
                ]
            }
        }]
    ))
    
    return scenarios


def generate_process_scenarios() -> List[tuple]:
    """Generate process/system scenarios with edge cases"""
    scenarios = []
    
    # Development tools
    ides = [
        ("Open VS Code", "code.exe"),
        ("Launch PyCharm", "pycharm64.exe"),
        ("Start Visual Studio", "devenv.exe"),
        ("Open Sublime Text", "sublime_text.exe"),
    ]
    cmd, prog = random.choice(ides)
    scenarios.append((cmd, [{"tool": "process.start_program", "args": {"program": prog, "background": True}}]))
    
    # System utilities
    scenarios.append(("Open Task Manager", [{"tool": "process.start_program", "args": {"program": "taskmgr.exe", "background": True}}]))
    scenarios.append(("Launch File Explorer", [{"tool": "process.start_program", "args": {"program": "explorer.exe", "background": True}}]))
    scenarios.append(("Start PowerShell", [{"tool": "process.start_program", "args": {"program": "powershell.exe", "background": True}}]))
    
    # Check system status
    scenarios.append(("Check system resources", [{"tool": "process.get_system_info", "args": {}}]))
    scenarios.append(("List all processes", [{"tool": "process.list_processes", "args": {}}]))
    
    # Run commands
    scenarios.append((
        "Run tests for the project",
        [{"tool": "process.run_command", "args": {"command": "pytest tests/", "cwd": f"./{get_project_name()}"}}]
    ))
    
    scenarios.append((
        "Install dependencies",
        [{"tool": "process.run_command", "args": {"command": "pip install -r requirements.txt", "cwd": "./"}}]
    ))
    
    scenarios.append((
        "Check git status",
        [{"tool": "process.run_command", "args": {"command": "git status", "cwd": "./"}}]
    ))
    
    # Kill process (edge case)
    scenarios.append((
        "Force close Chrome",
        [{"tool": "process.kill_process", "args": {"process_name": "chrome.exe"}}]
    ))
    
    return scenarios


def generate_email_scenarios() -> List[tuple]:
    """Generate realistic email scenarios with varied recipients"""
    scenarios = []
    
    person = get_person_name()
    email = f"{person.lower()}@{get_email_domain()}"
    
    # Project updates
    scenarios.append((
        f"Email {person} about the project status",
        [{
            "tool": "email.send",
            "args": {
                "to": email,
                "subject": f"Project Update - {get_date_str()}",
                "body": f"Hi {person},\n\nJust wanted to share a quick update on the project progress.\n\nWe've completed:\n- Feature A\n- Feature B\n\nNext steps:\n- Testing\n- Deployment\n\nLet me know if you have questions!\n\nBest,\nKayas"
            }
        }]
    ))
    
    # Send reports
    project = get_project_name()
    scenarios.append((
        f"Send the weekly report to the team",
        [{
            "tool": "email.send",
            "args": {
                "to": f"team@{get_email_domain()}",
                "subject": f"Weekly Report - Week of {get_date_str()}",
                "body": "Hi Team,\n\nPlease find attached this week's progress report.\n\nThanks!",
                "attachments": [f"reports/weekly_report_{get_date_str()}.pdf"]
            }
        }]
    ))
    
    # Meeting invites
    scenarios.append((
        f"Email {person} the meeting notes",
        [{
            "tool": "email.send",
            "args": {
                "to": email,
                "subject": "Meeting Notes - Action Items",
                "body": f"Hi {person},\n\nHere are the notes from today's meeting with action items highlighted.\n\nThanks!",
                "attachments": [f"meetings/notes_{get_date_str()}.pdf"]
            }
        }]
    ))
    
    # Code review request
    scenarios.append((
        "Ask for code review",
        [{
            "tool": "email.send",
            "args": {
                "to": f"tech-lead@{get_email_domain()}",
                "subject": f"Code Review Request - {get_project_name()}",
                "body": "Hi,\n\nI've pushed some changes to the feature branch. Could you review when you get a chance?\n\nPR: #123\n\nThanks!"
            }
        }]
    ))
    
    return scenarios


def generate_workflow_scenarios() -> List[tuple]:
    """Generate complex multi-step workflows"""
    scenarios = []
    
    # Morning routine
    scenarios.append((
        "Start my work session",
        [
            {"tool": "process.start_program", "args": {"program": "code.exe", "background": True}},
            {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}},
            {"tool": "spotify.play_query", "args": {"query": "focus music"}},
            {"tool": "filesystem.create_file", "args": {
                "filename": f"logs/daily_{get_date_str()}.md",
                "content": f"# Daily Log - {get_date_str()}\n\n## Goals\n- \n\n## Progress\n- \n"
            }},
            {"tool": "slack.send_message", "args": {"channel": "#standup", "text": "Good morning! Starting my day 🌅"}}
        ]
    ))
    
    # End of day
    scenarios.append((
        "Wrap up for the day",
        [
            {"tool": "process.run_command", "args": {"command": "git add . && git commit -m 'EOD commit'", "cwd": "./"}},
            {"tool": "filesystem.archive_file", "args": {"filename": f"backups/daily_backup_{get_date_str()}.zip"}},
            {"tool": "spotify.pause_playback", "args": {}},
            {"tool": "slack.send_message", "args": {"channel": "#standup", "text": "Wrapped up for the day! See you tomorrow 👋"}}
        ]
    ))
    
    # Deploy workflow
    scenarios.append((
        "Deploy to staging",
        [
            {"tool": "process.run_command", "args": {"command": "git checkout staging", "cwd": "./"}},
            {"tool": "process.run_command", "args": {"command": "git pull origin staging", "cwd": "./"}},
            {"tool": "process.run_command", "args": {"command": "npm run build", "cwd": "./"}},
            {"tool": "process.run_command", "args": {"command": "npm run deploy:staging", "cwd": "./"}},
            {"tool": "slack.send_message", "args": {"channel": "#deployments", "text": "Deployed to staging ✅"}}
        ]
    ))
    
    # Research and document
    scenarios.append((
        "Research and create summary",
        [
            {"tool": "browser.run_steps", "args": {
                "steps": [
                    {"action": "goto", "args": {"url": "https://google.com/search?q=latest+AI+research"}},
                    {"action": "screenshot", "args": {"filename": f"research/ai_research_{get_date_str()}.png"}}
                ]
            }},
            {"tool": "filesystem.create_file", "args": {
                "filename": f"research/summary_{get_date_str()}.md",
                "content": "# Research Summary\n\n## Key Findings\n- \n\n## References\n- \n"
            }},
            {"tool": "email.send", "args": {
                "to": f"team@{get_email_domain()}",
                "subject": "Research Summary",
                "body": "Hi Team,\n\nAttached is the research summary.\n\nBest!",
                "attachments": [f"research/summary_{get_date_str()}.md"]
            }}
        ]
    ))
    
    return scenarios


def generate_planning_scenarios() -> List[tuple]:
    """Multi-step planning scenarios (Jarvis-level)"""
    scenarios = []
    
    person = get_person_name()
    email = f"{person.lower()}@{get_email_domain()}"
    project = get_project_name()
    
    # Find and send
    scenarios.append((
        f"Find the {project} report and email it to {person}",
        [
            {"tool": "local.search", "args": {"query": f"{project} report"}},
            {"tool": "email.send", "args": {
                "to": email,
                "subject": f"{project} Report",
                "body": f"Hi {person},\n\nAttached is the {project} report you requested.\n\nBest,\nKayas",
                "attachments": [f"{project}_report.pdf"]
            }}
        ]
    ))
    
    # Search and open
    scenarios.append((
        "Find my budget spreadsheet and open it",
        [
            {"tool": "local.search", "args": {"query": "budget spreadsheet"}},
            {"tool": "process.start_program", "args": {"program": "excel.exe", "background": True}}
        ]
    ))
    
    # Collect and archive
    scenarios.append((
        "Collect last week's work files and zip them",
        [
            {"tool": "local.search", "args": {"query": "last week files"}},
            {"tool": "filesystem.archive_file", "args": {"filename": f"archive/last_week_{get_date_str()}.zip"}}
        ]
    ))
    
    # Research then notify
    scenarios.append((
        "Check if deployment finished and notify the team",
        [
            {"tool": "browser.run_steps", "args": {
                "steps": [{"action": "goto", "args": {"url": "https://ci-dashboard.company.com/builds"}}]
            }},
            {"tool": "slack.send_message", "args": {"channel": "#deployments", "text": "Build status checked ✓"}}
        ]
    ))
    
    return scenarios



def generate_ui_scenarios() -> List[tuple]:
    """Generate UI automation scenarios"""
    scenarios = []
    
    apps = ["Chrome", "Notepad", "VS Code", "Excel", "PowerPoint"]
    app = random.choice(apps)
    
    scenarios.append((f"Close {app}", [{"tool": "uia.close_window", "args": {"window_title": app}}]))
    scenarios.append((f"Focus on {app}", [{"tool": "uia.focus_window", "args": {"window_title": app}}]))
    scenarios.append(("Show all open windows", [{"tool": "uia.list_windows", "args": {}}]))
    
    text = random.choice(["Hello World", "Test message", "Code snippet", "Meeting notes"])
    scenarios.append((
        f"Type '{text}' in Notepad",
        [{"tool": "uia.type_text", "args": {"window_title": "Notepad", "text": text}}]
    ))
    
    return scenarios


def generate_clipboard_scenarios() -> List[tuple]:
    """Generate clipboard scenarios"""
    scenarios = []
    
    texts = [
        "https://github.com/user/repo",
        "import numpy as np\nimport pandas as pd",
        "Meeting at 3pm tomorrow",
        f"Report for {get_date_str()}",
    ]
    
    for text in texts:
        scenarios.append((
            f"Copy '{text[:30]}...' to clipboard",
            [{"tool": "clipboard.copy_text", "args": {"text": text}}]
        ))
    
    scenarios.append(("What's in my clipboard?", [{"tool": "clipboard.paste_text", "args": {}}]))
    scenarios.append(("Show clipboard history", [{"tool": "clipboard.get_history", "args": {"limit": 10}}]))
    
    return scenarios


def generate_spotify_scenarios() -> List[tuple]:
    """Generate music/Spotify scenarios"""
    scenarios = []
    
    playlists = ["chill vibes", "focus music", "workout mix", "jazz classics", "lofi hip hop"]
    
    for playlist in playlists:
        scenarios.append((
            f"Play {playlist}",
            [{"tool": "spotify.play_query", "args": {"query": playlist}}]
        ))
    
    scenarios.append(("Pause the music", [{"tool": "spotify.pause_playback", "args": {}}]))
    scenarios.append(("Resume playback", [{"tool": "spotify.resume_playback", "args": {}}]))
    scenarios.append(("What's currently playing?", [{"tool": "spotify.get_current_playing", "args": {}}]))
    
    return scenarios


def generate_slack_scenarios() -> List[tuple]:
    """Generate Slack/communication scenarios"""
    scenarios = []
    
    channels = ["#general", "#dev-team", "#standup", "#random", "#deployments"]
    
    messages = [
        "Daily standup completed ✅",
        "Pushed latest changes to main",
        "Build passed! Ready for review",
        "Heading to lunch, back in 30",
        "Fixed the bug in production",
    ]
    
    for _ in range(5):
        channel = random.choice(channels)
        message = random.choice(messages)
        scenarios.append((
            f"Post to {channel}",
            [{"tool": "slack.send_message", "args": {"channel": channel, "text": message}}]
        ))
    
    scenarios.append((
        "Search Slack for 'deployment'",
        [{"tool": "slack.search_messages", "args": {"query": "deployment", "limit": 10}}]
    ))
    
    return scenarios


def generate_calendar_scenarios() -> List[tuple]:
    """Generate calendar/scheduling scenarios"""
    scenarios = []
    
    # Create events
    events = [
        ("team standup", 9, 30),
        ("code review", 14, 60),
        ("client meeting", 15, 90),
        ("1-on-1 with manager", 11, 30),
    ]
    
    for event_name, hour, duration in events:
        start = datetime.now().replace(hour=hour, minute=0, second=0)
        end = start + timedelta(minutes=duration)
        scenarios.append((
            f"Schedule {event_name}",
            [{
                "tool": "calendar.create_event",
                "args": {
                    "summary": event_name.title(),
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "description": f"Scheduled via Kayas"
                }
            }]
        ))
    
    scenarios.append(("Show my calendar for today", [{"tool": "calendar.list_events", "args": {"date": get_date_str()}}]))
    
    return scenarios


def generate_messaging_workflows() -> List[tuple]:
    """Generate deep UI workflows for messaging apps (WhatsApp, Discord, Slack Desktop)
    
    This teaches the model the core pattern:
    Open App → Search/Find Contact → Type Message → Send
    
    Each scenario includes realistic multi-step sequences with timing and waits.
    """
    scenarios = []
    
    contacts = ["Abdus", "Mom", "John", "Team Lead", "Sarah", "Mike", "Emma", "David"]
    messages = [
        "hi", "running late", "check email", "you there?", "files attached",
        "call me when free", "done for today", "see you tomorrow", "thanks", "heads up"
    ]
    
    # === WhatsApp Desktop Workflows ===
    for contact in contacts:
        for msg in messages:
            scenarios.append((
                f"Open WhatsApp and text {contact} '{msg}'",
                [
                    # 1. Launch WhatsApp (if not already open)
                    {"tool": "process.start_program", "args": {"program": "WhatsApp.exe", "background": True}},
                    # 2. Wait for WhatsApp UI to fully load
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 3000}}]}},
                    # 3. Focus the window and search for contact (Ctrl+F or click search)
                    {"tool": "uia.focus_window", "args": {"window_title": "WhatsApp"}},
                    {"tool": "desktop.send_keys", "args": {"keys": "Ctrl+F"}},
                    # 4. Type contact name in search
                    {"tool": "uia.type_text", "args": {"window_title": "WhatsApp", "text": contact, "control_type": "Edit"}},
                    # 5. Wait for search results to appear
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}},
                    # 6. Press Enter to select the first/matching contact
                    {"tool": "desktop.send_keys", "args": {"keys": "Enter"}},
                    # 7. Wait for chat window to load
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1500}}]}},
                    # 8. Click in the message input box
                    {"tool": "perception.smart_click", "args": {"target": "message input", "context": {"window_title": "WhatsApp"}}},
                    # 9. Type the message
                    {"tool": "uia.type_text", "args": {"window_title": "WhatsApp", "text": msg}},
                    # 10. Send (press Enter)
                    {"tool": "desktop.send_keys", "args": {"keys": "Enter"}}
                ]
            ))
    
    # === Discord Desktop Workflows ===
    discord_servers = ["Development", "Community", "Gaming", "Work"]
    discord_channels = ["general", "announcements", "random", "help"]
    
    for server in discord_servers:
        for channel in discord_channels:
            for msg in messages[:5]:  # Fewer variants for Discord
                scenarios.append((
                    f"Open Discord and message {channel} in {server} '{msg}'",
                    [
                        {"tool": "process.start_program", "args": {"program": "Discord.exe", "background": True}},
                        {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                        # Click on server
                        {"tool": "perception.smart_click", "args": {"target": server, "context": {"window_title": "Discord"}}},
                        # Wait for server channels to load
                        {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}},
                        # Click on channel
                        {"tool": "perception.smart_click", "args": {"target": f"#{channel}", "context": {"window_title": "Discord"}}},
                        # Click message input
                        {"tool": "perception.smart_click", "args": {"target": "message input", "context": {}}},
                        # Type message
                        {"tool": "uia.type_text", "args": {"window_title": "Discord", "text": msg}},
                        # Send (Shift+Enter or click send)
                        {"tool": "desktop.send_keys", "args": {"keys": "Enter"}}
                    ]
                ))
    
    # === Slack Desktop Workflows ===
    slack_users = ["Abdus", "Mom", "John", "Team Lead", "Sarah"]
    
    for user in slack_users:
        for msg in messages[:5]:
            scenarios.append((
                f"Open Slack and message {user} '{msg}'",
                [
                    {"tool": "process.start_program", "args": {"program": "slack.exe", "background": True}},
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2500}}]}},
                    # Use Cmd+K (or Ctrl+K on Windows) to open quick switcher
                    {"tool": "desktop.send_keys", "args": {"keys": "Ctrl+K"}},
                    # Type user name
                    {"tool": "uia.type_text", "args": {"window_title": "Slack", "text": user}},
                    # Wait and select
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 800}}]}},
                    {"tool": "desktop.send_keys", "args": {"keys": "Enter"}},
                    # Wait for DM to open
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}},
                    # Click message input
                    {"tool": "perception.smart_click", "args": {"target": "message input", "context": {}}},
                    # Type and send
                    {"tool": "uia.type_text", "args": {"window_title": "Slack", "text": msg}},
                    {"tool": "desktop.send_keys", "args": {"keys": "Enter"}}
                ]
            ))
    
    return scenarios


def generate_spotify_workflows() -> List[tuple]:
    """Generate deep UI workflows for Spotify Desktop
    
    Patterns:
    - Open Spotify → Search Artist/Song → Play
    - Open Spotify → Browse Playlist → Select Song → Play
    - Pause/Resume/Skip current song
    - Create and add to playlist
    """
    scenarios = []
    
    artists = ["The Weeknd", "Drake", "Taylor Swift", "Billie Eilish", "Dua Lipa", "Post Malone"]
    songs = ["Blinding Lights", "Hotline Bling", "Anti-Hero", "Levitating", "Circles", "Driver License"]
    playlists = ["Chill Vibes", "Workout Mix", "Focus", "Party", "Lo-fi Hip Hop"]
    
    # Pattern 1: Open Spotify → Search Song → Play
    for artist in artists:
        for song in songs[:2]:
            scenarios.append((
                f"Open Spotify and play '{song}' by {artist}",
                [
                    {"tool": "process.start_program", "args": {"program": "Spotify.exe", "background": True}},
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 3000}}]}},
                    # Focus Spotify window
                    {"tool": "uia.focus_window", "args": {"window_title": "Spotify"}},
                    # Open search (Ctrl+L typically)
                    {"tool": "desktop.send_keys", "args": {"keys": "Ctrl+L"}},
                    # Type search query
                    {"tool": "uia.type_text", "args": {"window_title": "Spotify", "text": f"{song} {artist}"}},
                    # Wait for search results
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1500}}]}},
                    # Click first result (the song)
                    {"tool": "perception.smart_click", "args": {"target": song, "context": {"window_title": "Spotify"}}},
                    # Spotify auto-plays, but explicitly press spacebar to ensure play
                    {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 500}}]}},
                    {"tool": "desktop.send_keys", "args": {"keys": "space"}}
                ]
            ))
    
    # Pattern 2: Open Spotify → Browse Playlist → Play
    for playlist in playlists:
        scenarios.append((
            f"Open Spotify and play the '{playlist}' playlist",
            [
                {"tool": "process.start_program", "args": {"program": "Spotify.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 3000}}]}},
                {"tool": "uia.focus_window", "args": {"window_title": "Spotify"}},
                # Click on "Search" or navigate to playlists
                {"tool": "perception.smart_click", "args": {"target": "Search", "context": {"window_title": "Spotify"}}},
                # Type playlist name
                {"tool": "uia.type_text", "args": {"window_title": "Spotify", "text": playlist}},
                # Wait and select
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1200}}]}},
                {"tool": "perception.smart_click", "args": {"target": playlist, "context": {}}},
                # Wait for playlist to load
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}},
                # Press spacebar to play
                {"tool": "desktop.send_keys", "args": {"keys": "space"}}
            ]
        ))
    
    # Pattern 3: Control Playback
    scenarios.append((
        "Play Spotify",
        [
            {"tool": "process.start_program", "args": {"program": "Spotify.exe", "background": True}},
            {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
            {"tool": "desktop.send_keys", "args": {"keys": "space"}}
        ]
    ))
    
    scenarios.append((
        "Pause Spotify",
        [
            {"tool": "uia.focus_window", "args": {"window_title": "Spotify"}},
            {"tool": "desktop.send_keys", "args": {"keys": "space"}}
        ]
    ))
    
    scenarios.append((
        "Skip to next song in Spotify",
        [
            {"tool": "uia.focus_window", "args": {"window_title": "Spotify"}},
            {"tool": "desktop.send_keys", "args": {"keys": "ctrl+Right"}}
        ]
    ))
    
    scenarios.append((
        "Go to previous song in Spotify",
        [
            {"tool": "uia.focus_window", "args": {"window_title": "Spotify"}},
            {"tool": "desktop.send_keys", "args": {"keys": "ctrl+Left"}}
        ]
    ))
    
    # Pattern 4: Create playlist and add song
    for playlist in playlists:
        scenarios.append((
            f"Create a new playlist called '{playlist}' in Spotify",
            [
                {"tool": "process.start_program", "args": {"program": "Spotify.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2500}}]}},
                # Right-click on "Your Library" or Playlists section
                {"tool": "perception.smart_click", "args": {"target": "Create Playlist", "context": {"window_title": "Spotify"}}},
                # Type playlist name
                {"tool": "uia.type_text", "args": {"window_title": "Spotify", "text": playlist}},
                # Confirm
                {"tool": "desktop.send_keys", "args": {"keys": "Enter"}}
            ]
        ))
    
    return scenarios


def generate_browser_deep_workflows() -> List[tuple]:
    """Generate deeper browser workflows beyond simple navigation
    
    Patterns:
    - Search → Click Result → Scroll → Find Info → Screenshot
    - Open Multiple Tabs → Switch Between → Extract Info
    - Fill Forms → Submit → Verify Result
    - Login → Navigate → Find Specific Content
    """
    scenarios = []
    
    search_queries = [
        ("python async programming", "Real Python"),
        ("react hooks tutorial", "Official React Docs"),
        ("kubernetes deployment", "Kubernetes.io"),
        ("machine learning basics", "Andrew Ng Course"),
        ("docker tutorial", "Docker Official Docs"),
    ]
    
    # Pattern 1: Google Search → Click Result → Read Content
    for query, expected_site in search_queries:
        scenarios.append((
            f"Search '{query}' on Google, open the first result from {expected_site}, and screenshot",
            [
                {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "goto", "args": {"url": "https://google.com"}},
                    {"action": "fill", "args": {"selector": "input[name='q']", "value": query}},
                    {"action": "press", "args": {"key": "Enter"}}
                ]}},
                # Wait for results
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                # Click first relevant result
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "click", "args": {"selector": "div.g:first-child a"}}
                ]}},
                # Wait for page to load
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2500}}]}},
                # Scroll down to find key info
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "scroll", "args": {"direction": "down", "amount": 3}}
                ]}},
                # Screenshot the result
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "screenshot", "args": {"filename": f"research/{query.replace(' ', '_')}_{get_timestamp()}.png"}}
                ]}}
            ]
        ))
    
    # Pattern 2: GitHub Workflow - Search Repo → Open → Star
    github_repos = ["tensorflow/tensorflow", "facebook/react", "python/cpython", "microsoft/vscode"]
    
    for repo in github_repos:
        scenarios.append((
            f"Find and star the {repo} GitHub repository",
            [
                {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "goto", "args": {"url": f"https://github.com/{repo}"}}
                ]}},
                # Wait for page load
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                # Click star button
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "click", "args": {"selector": ".js-toggler-container button"}}
                ]}}
            ]
        ))
    
    # Pattern 3: Amazon Product Search → Filter → View Details
    product_searches = [
        ("wireless keyboard", "wireless keyboard mechanical"),
        ("laptop stand", "adjustable laptop stand"),
        ("monitor", "4k monitor 27 inch"),
    ]
    
    for search, filter_term in product_searches:
        scenarios.append((
            f"Search for '{search}' on Amazon, filter by '{filter_term}', and view top result",
            [
                {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "goto", "args": {"url": "https://amazon.com"}}
                ]}},
                # Search
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "fill", "args": {"selector": "#twotabsearchtextbox", "value": search}},
                    {"action": "press", "args": {"key": "Enter"}}
                ]}},
                # Wait for results
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                # Click on first product
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "click", "args": {"selector": ".s-result-item:first-child a"}}
                ]}},
                # Screenshot product page
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "screenshot", "args": {"filename": f"shopping/{search}_{get_timestamp()}.png"}}
                ]}}
            ]
        ))
    
    # Pattern 4: YouTube Search → Play Video → Adjust Quality
    video_searches = ["python tutorial", "machine learning explained", "javascript fundamentals"]
    
    for search in video_searches:
        scenarios.append((
            f"Search '{search}' on YouTube and play the first video",
            [
                {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "goto", "args": {"url": "https://youtube.com"}}
                ]}},
                # Search
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "fill", "args": {"selector": "input[name='search_query']", "value": search}},
                    {"action": "press", "args": {"key": "Enter"}}
                ]}},
                # Wait for results
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 2000}}]}},
                # Click first video
                {"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "click", "args": {"selector": "ytd-video-renderer:first-child a"}}
                ]}},
                # Wait for video to load
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 3000}}]}},
                # Play (spacebar)
                {"tool": "desktop.send_keys", "args": {"keys": "space"}}
            ]
        ))
    
    return scenarios


def generate_text_editor_workflows() -> List[tuple]:
    """Generate deep workflows for text editors and IDEs
    
    Patterns:
    - Open VSCode → Create File → Write Code → Save
    - Open Notepad → Write Notes → Save with Timestamp
    - Open IDE → Open Project → Run Tests
    """
    scenarios = []
    
    # Pattern 1: VSCode - Create and Edit File
    file_types = [
        ("python", "hello.py", "print('Hello, World!')"),
        ("javascript", "app.js", "console.log('Hello, World!');"),
        ("html", "index.html", "<h1>Hello, World!</h1>"),
        ("markdown", "README.md", "# My Project\n\nDescription here."),
    ]
    
    for lang, filename, content in file_types:
        scenarios.append((
            f"Open VSCode and create a new {lang} file '{filename}'",
            [
                {"tool": "process.start_program", "args": {"program": "code.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 3000}}]}},
                # Create new file
                {"tool": "desktop.send_keys", "args": {"keys": "Ctrl+N"}},
                # Type content
                {"tool": "uia.type_text", "args": {"window_title": "Visual Studio Code", "text": content}},
                # Save (Ctrl+S)
                {"tool": "desktop.send_keys", "args": {"keys": "Ctrl+S"}},
                # Wait for save dialog
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}},
                # Type filename
                {"tool": "uia.type_text", "args": {"window_title": "Save", "text": filename}},
                # Confirm save
                {"tool": "desktop.send_keys", "args": {"keys": "Enter"}}
            ]
        ))
    
    # Pattern 2: Notepad - Quick Note with Timestamp
    note_topics = ["meeting notes", "ideas", "todo list", "quick thoughts", "observations"]
    
    for topic in note_topics:
        scenarios.append((
            f"Open Notepad and write a {topic} with today's date",
            [
                {"tool": "process.start_program", "args": {"program": "notepad.exe", "background": True}},
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}},
                # Type heading with date
                {"tool": "uia.type_text", "args": {"window_title": "Notepad", "text": f"{topic.upper()} - {get_date_str()}\n\n"}},
                # Type some content
                {"tool": "uia.type_text", "args": {"window_title": "Notepad", "text": "- Item 1\n- Item 2\n- Item 3\n"}},
                # Save
                {"tool": "desktop.send_keys", "args": {"keys": "Ctrl+S"}},
                # Wait and confirm filename
                {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}}
            ]
        ))
    
    return scenarios


def generate_system_admin_workflows() -> List[tuple]:
    """Generate deep workflows for system administration and maintenance
    
    Patterns:
    - Check system resources → Take action if needed
    - Backup files → Verify → Archive
    - Update software → Check version
    - Manage processes → Kill zombie processes
    """
    scenarios = []
    
    # Pattern 1: System Health Check
    scenarios.append((
        "Check system resources (CPU, memory, disk) and report",
        [
            {"tool": "process.get_system_info", "args": {}},
            {"tool": "process.run_command", "args": {"command": "Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 10", "cwd": "."}},
            {"tool": "process.run_command", "args": {"command": "Get-Volume | Select-Object DriveLetter,SizeRemaining,Size", "cwd": "."}}
        ]
    ))
    
    # Pattern 2: Backup and Archive
    backup_items = ["Documents", "Pictures", "Desktop", "Downloads"]
    
    for item in backup_items:
        scenarios.append((
            f"Backup {item} folder to archive with timestamp",
            [
                {"tool": "filesystem.archive_file", "args": {"filename": f"backups/{item.lower()}_{get_timestamp()}.zip"}},
                {"tool": "process.run_command", "args": {"command": f"Get-Item backups/{item.lower()}_{get_timestamp()}.zip | Select-Object FullName,Length", "cwd": "."}}
            ]
        ))
    
    # Pattern 3: Disk Cleanup
    scenarios.append((
        "Clean up old temporary files and reclaim disk space",
        [
            {"tool": "process.run_command", "args": {"command": "Remove-Item -Path $env:TEMP\\* -Force -Recurse -ErrorAction SilentlyContinue", "cwd": "."}},
            {"tool": "process.run_command", "args": {"command": "Get-Volume | Select-Object DriveLetter,SizeRemaining", "cwd": "."}}
        ]
    ))
    
    # Pattern 4: Monitor and Kill Processes
    scenarios.append((
        "Find and terminate zombie/hanging processes",
        [
            {"tool": "process.list_processes", "args": {}},
            {"tool": "process.run_command", "args": {"command": "Get-Process | Where-Object {$_.CPU -gt 50} | Select-Object Name,CPU", "cwd": "."}}
        ]
    ))
    
    return scenarios


def generate_visual_automation_scenarios() -> List[tuple]:
    """Generate scenarios that require Computer Vision (CV) instead of text/IDs.
    Useful for games, custom UIs, or finding icons when text-based automation fails.
    
    This teaches the model to:
    - Click icons/images based on visual appearance
    - Wait for visual changes (loading spinners, etc.)
    - Use template matching for UI automation
    """
    scenarios = []
    
    # Pattern 1: Find and click icons/images
    icons = [
        "gear_icon", "play_button", "microphone_icon", "download_arrow", 
        "wifi_symbol", "settings_gear", "close_button", "minimize_button",
        "search_icon", "home_icon", "profile_picture", "notification_bell"
    ]
    
    for icon in icons:
        icon_name = icon.replace('_', ' ')
        scenarios.append((
            f"Click the {icon_name} on the screen",
            [
                # 1. Take a screenshot to 'see' the current state
                {"tool": "cv.screenshot", "args": {"filename": "temp_vision.png"}},
                # 2. Find the image template with confidence threshold
                {"tool": "cv.find_image", "args": {"template_path": f"templates/{icon}.png", "confidence": 0.8}},
                # 3. Click the found location
                {"tool": "cv.click_image", "args": {"template_path": f"templates/{icon}.png"}}
            ]
        ))
    
    # Pattern 2: Wait for visual changes (loading indicators)
    loading_scenarios = [
        ("Wait for the loading screen to finish", "loading_spinner.png", True),
        ("Wait until the play button appears", "play_button.png", False),
        ("Wait for the green checkmark to show", "checkmark_green.png", False),
        ("Wait for the error icon to disappear", "error_icon.png", True),
        ("Wait for the upload progress to complete", "uploading_icon.png", True),
    ]
    
    for command, template, wait_disappear in loading_scenarios:
        scenarios.append((
            command,
            [{
                "tool": "cv.wait_for_image", 
                "args": {
                    "template_path": f"templates/{template}", 
                    "timeout": 30, 
                    "wait_for_disappear": wait_disappear
                }
            }]
        ))
    
    # Pattern 3: Find and read text from specific screen regions (OCR with bounding box)
    ocr_scenarios = [
        ("Read the text from the notification popup", "notification_area"),
        ("Get the current price from the price tag", "price_display"),
        ("Read the error message from the dialog", "error_dialog"),
        ("Extract the username from the profile section", "profile_username"),
    ]
    
    for command, region in ocr_scenarios:
        scenarios.append((
            command,
            [
                {"tool": "cv.screenshot", "args": {"filename": "temp_screen.png"}},
                {"tool": "ocr.read_region", "args": {"region": region, "language": "eng"}}
            ]
        ))
    
    # Pattern 4: Multi-step visual workflows
    scenarios.append((
        "Find the settings icon and click it, then click the advanced tab",
        [
            {"tool": "cv.screenshot", "args": {"filename": "screen1.png"}},
            {"tool": "cv.click_image", "args": {"template_path": "templates/settings_gear.png"}},
            {"tool": "desktop.run_steps", "args": {"steps": [{"action": "sleep", "args": {"ms": 1000}}]}},
            {"tool": "cv.screenshot", "args": {"filename": "screen2.png"}},
            {"tool": "cv.click_image", "args": {"template_path": "templates/advanced_tab.png"}}
        ]
    ))
    
    # Pattern 5: Visual verification (check if something appears on screen)
    scenarios.append((
        "Check if the login button is visible",
        [
            {"tool": "cv.screenshot", "args": {"filename": "login_check.png"}},
            {"tool": "cv.find_image", "args": {"template_path": "templates/login_button.png", "confidence": 0.7}}
        ]
    ))
    
    # Pattern 6: Game/Custom UI automation
    game_scenarios = [
        ("Click the start game button", "start_game_button.png"),
        ("Click on the inventory icon", "inventory_icon.png"),
        ("Press the attack button", "attack_button.png"),
        ("Click the quit option", "quit_button.png"),
    ]
    
    for command, template in game_scenarios:
        scenarios.append((
            command,
            [
                {"tool": "cv.screenshot", "args": {"filename": "game_screen.png"}},
                {"tool": "cv.click_image", "args": {"template_path": f"templates/{template}", "confidence": 0.75}}
            ]
        ))
    
    return scenarios


def generate_monitoring_scenarios() -> List[tuple]:
    """Generate scenarios for watching files, network, or processes.
    
    This teaches the model to be a watchdog - monitoring events and reacting:
    - File system changes (new files, modifications, deletions)
    - Network connectivity and API health checks
    - Process monitoring and alerts
    - Scheduled tasks and triggers
    """
    scenarios = []
    
    # Pattern 1: File system watching
    watch_folders = [
        ("Downloads", "created", "A new file was downloaded"),
        ("Documents", "modified", "A document was changed"),
        ("Desktop", "created", "A new file appeared on Desktop"),
        ("Projects", "modified", "Project files were updated"),
    ]
    
    for folder, event_type, message in watch_folders:
        scenarios.append((
            f"Let me know when a new file appears in {folder}",
            [
                {"tool": "filewatcher.watch_directory", "args": {"path": folder, "event_type": event_type}},
                {"tool": "slack.send_message", "args": {"channel": "#general", "text": f"I'm watching your {folder} folder now. I'll notify you when: {message}"}}
            ]
        ))
    
    # Pattern 2: Network/API monitoring
    api_checks = [
        ("https://api.example.com/health", "Check if the API is responding"),
        ("https://mywebsite.com", "Check if my website is up"),
        ("https://api.github.com", "Verify GitHub API is accessible"),
        ("https://status.slack.com/api/v2.0.0/current", "Check Slack service status"),
    ]
    
    for url, description in api_checks:
        scenarios.append((
            f"{description}",
            [
                {"tool": "network.http_request", "args": {"url": url, "method": "GET"}},
                # Model learns to interpret HTTP response codes
            ]
        ))
    
    # Pattern 3: Monitor and alert on specific conditions
    scenarios.append((
        "Alert me if CPU usage goes above 80%",
        [
            {"tool": "process.get_system_info", "args": {}},
            {"tool": "slack.send_message", "args": {"channel": "#alerts", "text": "CPU usage is high! Monitoring now..."}}
        ]
    ))
    
    scenarios.append((
        "Watch the logs folder and alert me on errors",
        [
            {"tool": "filewatcher.watch_directory", "args": {"path": "logs", "event_type": "modified"}},
            {"tool": "filesystem.read_file", "args": {"filename": "logs/latest.log", "tail": 10}},
            {"tool": "slack.send_message", "args": {"channel": "#errors", "text": "New log entry detected"}}
        ]
    ))
    
    # Pattern 4: Scheduled/Periodic monitoring
    scenarios.append((
        "Check disk space every hour and warn if low",
        [
            {"tool": "process.run_command", "args": {"command": "Get-Volume | Select-Object DriveLetter,SizeRemaining", "cwd": "."}},
            # Model learns to set up periodic tasks
        ]
    ))
    
    # Pattern 5: Process monitoring
    process_monitors = [
        ("Chrome crashes", "chrome.exe"),
        ("Python stops running", "python.exe"),
        ("VS Code closes", "code.exe"),
        ("Spotify quits unexpectedly", "spotify.exe"),
    ]
    
    for event, process_name in process_monitors:
        scenarios.append((
            f"Alert me if {event}",
            [
                {"tool": "process.list_processes", "args": {}},
                {"tool": "process.monitor_process", "args": {"process_name": process_name, "alert_on_exit": True}}
            ]
        ))
    
    # Pattern 6: Network connectivity monitoring
    scenarios.append((
        "Monitor my internet connection and notify me if it drops",
        [
            {"tool": "network.check_connectivity", "args": {"host": "8.8.8.8"}},
            {"tool": "slack.send_message", "args": {"channel": "#alerts", "text": "Internet connection check started"}}
        ]
    ))
    
    # Pattern 7: Wait for specific file to appear
    scenarios.append((
        "Wait for the report.pdf file to be created, then email it",
        [
            {"tool": "filewatcher.wait_for_file", "args": {"path": "reports/report.pdf", "timeout": 300}},
            {"tool": "email.send", "args": {
                "to": "team@company.com",
                "subject": "Report Ready",
                "body": "The report has been generated.",
                "attachments": ["reports/report.pdf"]
            }}
        ]
    ))
    
    # Pattern 8: Monitor clipboard for specific content
    scenarios.append((
        "Watch my clipboard and save any code snippets to a file",
        [
            {"tool": "clipboard.monitor", "args": {"pattern": "```", "action": "save"}},
            {"tool": "filesystem.append_file", "args": {"filename": "snippets.md", "content": "[clipboard content]"}}
        ]
    ))
    
    return scenarios


def generate_error_scenarios() -> List[tuple]:
    """Generate error/edge case scenarios (15% of dataset)"""
    scenarios = []
    
    # Permission errors
    scenarios.append((
        "Delete system32 folder",
        []  # Should clarify/refuse
    ))
    
    # Missing file
    scenarios.append((
        "Open the nonexistent_file.txt",
        []  # Should ask for clarification
    ))
    
    # Ambiguous request
    scenarios.append((
        "Send it to them",
        []  # Needs clarification
    ))
    
    # Network failure simulation
    scenarios.append((
        "Download file from unreachable server",
        []  # Should handle gracefully
    ))
    
    # Process not found
    scenarios.append((
        "Kill process that doesn't exist",
        []  # Should report not found
    ))
    
    return scenarios


# === NEW: Agent-style examples (intent→plan, tool traces, multi-step, failures, persona+planning) ===
def generate_intent_plan_examples(n: int = 50) -> List[Dict[str, Any]]:
    """Map natural utterances to intents and concrete multi-step plans."""
    samples: List[Dict[str, Any]] = []
    commands = [
        ("bro close the chrome window that's hanging", "close_app", [
            {"action": "focus_window", "args": {"name": "Chrome"}},
            {"action": "send_keys", "args": {"keys": "Alt+F4"}},
            {"action": "verify_window_closed", "args": {"name": "Chrome"}},
            {"action": "fallback_click_close_button", "args": {}}
        ]),
        ("find my downloads and clean up old files", "cleanup_downloads", [
            {"action": "fs.list", "args": {"path": "Downloads"}},
            {"action": "fs.filter_by_age", "args": {"days": 30}},
            {"action": "fs.delete", "args": {"files": ["*.zip", "*.tmp"]}},
            {"action": "fs.verify_deleted", "args": {}}
        ]),
        ("search python async best practices and summarize", "research_and_summarize", [
            {"action": "browser.goto", "args": {"url": "https://google.com"}},
            {"action": "browser.search", "args": {"query": "python async best practices"}},
            {"action": "browser.open_result", "args": {"index": 1}},
            {"action": "browser.screenshot", "args": {"path": f"research/async_{get_date_str()}.png"}},
            {"action": "extract.summary", "args": {"source": "page"}}
        ]),
    ]
    
    for _ in range(n):
        text, intent, plan = random.choice(commands)
        # ✅ FIX: Add messages field
        samples.append({
            "messages": [
                {"role": "system", "content": "You are Kayas. Map user requests to structured action plans."},
                {"role": "user", "content": text},
                {"role": "assistant", "content": json.dumps({
                    "intent": intent,
                    "plan": plan
                }, indent=2)}
            ],
            "category": "intent_plan",
            "scenario": "multi_step_plan"
        })
    
    return samples


def generate_tool_trace_examples(n: int = 50) -> List[Dict[str, Any]]:
    """Action→observation→next_action logs with retries and final_success."""
    traces: List[Dict[str, Any]] = []
    
    for _ in range(n):
        ocr_words = random.sample(["Close", "Exit", "Cancel", "OK", "Apply"], k=2)
        match_score = round(random.random(), 2)
        result = "found" if match_score > 0.6 else "not_found"
        fallback = "press_alt_f4" if result == "not_found" else None
        
        # ✅ FIX: Add messages field
        traces.append({
            "messages": [
                {"role": "system", "content": "You are Kayas. Track action results and retry on failures."},
                {"role": "user", "content": "close the window using OCR"},
                {"role": "assistant", "content": json.dumps({
                    "log": [
                        {
                            "step": "click_image",
                            "result": result,
                            "observation": {"ocr": ocr_words, "image_match_score": match_score},
                            "retry": result == "not_found",
                            "fallback": fallback
                        },
                        {
                            "step": "verify_window_closed",
                            "result": "success",
                            "observation": {"windows_open": ["VS Code"]}
                        }
                    ],
                    "final_success": True
                }, indent=2)}
            ],
            "category": "tool_trace",
            "scenario": "ui_click_with_ocr"
        })
    
    return traces


def generate_multistep_task_examples(n: int = 60) -> List[Dict[str, Any]]:
    """Real tasks: google→open→screenshot→extract; clean downloads→verify; scroll→click."""
    tasks: List[Dict[str, Any]] = []
    patterns = [
        {
            "user": "search something on google → open a result → screenshot → extract info",
            "steps": [
                {"tool": "browser.run_steps", "args": {"steps": [{"action": "goto", "args": {"url": "https://google.com"}}, {"action": "fill", "args": {"selector": "input[name=q]", "value": "python error handling best practices"}}, {"action": "enter", "args": {}}]}},
                {"tool": "browser.run_steps", "args": {"steps": [{"action": "click", "args": {"selector": "#search div.g:first-child a"}}]}},
                {"tool": "browser.run_steps", "args": {"steps": [{"action": "screenshot", "args": {"filename": f"research/google_{get_timestamp()}.png"}}]}},
                {"tool": "ocr.read_screen", "args": {}}
            ]
        },
        {
            "user": "clean downloads folder → verify deleted files → confirm success",
            "steps": [
                {"tool": "filesystem.list", "args": {"path": "Downloads"}},
                {"tool": "filesystem.delete_file", "args": {"pattern": "*.zip"}},
                {"tool": "filesystem.list", "args": {"path": "Downloads"}},
                {"tool": "process.run_command", "args": {"command": "echo Cleaned"}}
            ]
        },
        {
            "user": "find a window by text → scroll until element appears → click it",
            "steps": [
                {"tool": "uia.find_window", "args": {"title_contains": "Settings"}},
                {"tool": "uia.get_control_tree", "args": {"window_title": "Settings"}},
                {"tool": "ocr.find_text", "args": {"text": "Advanced"}},
                {"tool": "ocr.click_text", "args": {"text": "Advanced"}}
            ]
        }
    ]
    
    for _ in range(n):
        p = random.choice(patterns)
        # ✅ FIX: Add messages field
        tasks.append({
            "messages": [
                {"role": "system", "content": "You are Kayas, an AI assistant that helps users accomplish multi-step tasks."},
                {"role": "user", "content": p["user"]},
                {"role": "assistant", "content": json.dumps({
                    "response": "Working on it…",
                    "actions": p["steps"]
                }, indent=2)}
            ],
            "category": "multi_step_task",
            "scenario": "real_world"
        })
    
    return tasks


def generate_failure_recovery_examples(n: int = 40) -> List[Dict[str, Any]]:
    """Demonstrate missing elements and recovery attempts."""
    examples: List[Dict[str, Any]] = []
    cases = [
        {
            "step": "button missing",
            "attempts": [
                {"action": "ocr.find_text", "args": {"text": "Submit"}, "result": "not_found"},
                {"action": "uia.scroll", "args": {"window_title": "Form"}, "result": "ok"},
                {"action": "ocr.find_text", "args": {"text": "Submit"}, "result": "found"},
                {"action": "ocr.click_text", "args": {"text": "Submit"}, "result": "success"}
            ]
        },
        {
            "step": "page didn’t load",
            "attempts": [
                {"action": "browser.run_steps", "args": {"steps": [{"action": "goto", "args": {"url": "https://example.com"}}]}},
                {"action": "browser.run_steps", "args": {"steps": [{"action": "reload", "args": {}}]}},
                {"action": "browser.run_steps", "args": {"steps": [{"action": "wait", "args": {"ms": 1500}}]}},
                {"action": "browser.run_steps", "args": {"steps": [{"action": "goto", "args": {"url": "https://example.com/dashboard"}}]}}
            ]
        },
        {
            "step": "element moved",
            "attempts": [
                {"action": "ocr.find_text", "args": {"text": "Settings"}, "result": "not_found"},
                {"action": "uia.get_control_tree", "args": {"window_title": "App"}, "result": "ok"},
                {"action": "ocr.find_text", "args": {"text": "Preferences"}, "result": "found"},
                {"action": "ocr.click_text", "args": {"text": "Preferences"}, "result": "success"}
            ]
        }
    ]
    
    for _ in range(n):
        case = random.choice(cases)
        # ✅ FIX: Add messages field
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Kayas. When UI elements are missing, try alternative approaches."},
                {"role": "user", "content": f"handle case: {case['step']}"},
                {"role": "assistant", "content": json.dumps({
                    "trace": case["attempts"],
                    "final_success": True
                }, indent=2)}
            ],
            "category": "failure_recovery",
            "scenario": case["step"]
        })
    
    return examples


def generate_persona_planning_examples(n: int = 50) -> List[Dict[str, Any]]:
    """Friendly response plus concrete actions in one example."""
    examples: List[Dict[str, Any]] = []
    
    for _ in range(n):
        # ✅ FIX: Add messages field
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Kayas, a friendly assistant with personality."},
                {"role": "user", "content": "yo bro clean up my downloads"},
                {"role": "assistant", "content": json.dumps({
                    "response": "sure bro, give me a sec — going through your downloads now",
                    "actions": [
                        {"tool": "fs.list", "args": {"path": "Downloads"}},
                        {"tool": "fs.filter_by_age", "args": {"days": 30}},
                        {"tool": "fs.delete", "args": {"files": ["1.png", "old.zip"]}}
                    ]
                }, indent=2)}
            ],
            "category": "persona_planning",
            "scenario": "downloads_cleanup"
        })
    
    return examples


# Aggregate all scenario generators
def get_all_scenarios() -> List[tuple]:
    """Generate comprehensive scenario pool (20k+)"""
    all_scenarios = []
    
    # Generate multiple batches with randomization to reach 20k examples
    for iteration in range(60):  # Generate 60x to reach ~20k unique scenarios
        all_scenarios.extend(generate_filesystem_scenarios())
        all_scenarios.extend(generate_browser_scenarios())
        all_scenarios.extend(generate_process_scenarios())
        all_scenarios.extend(generate_email_scenarios())
        all_scenarios.extend(generate_workflow_scenarios())
        all_scenarios.extend(generate_planning_scenarios())
        all_scenarios.extend(generate_ui_scenarios())
        all_scenarios.extend(generate_clipboard_scenarios())
        all_scenarios.extend(generate_spotify_scenarios())
        all_scenarios.extend(generate_slack_scenarios())
        all_scenarios.extend(generate_calendar_scenarios())
        # NEW: Deep UI Workflows
        all_scenarios.extend(generate_messaging_workflows())
        all_scenarios.extend(generate_spotify_workflows())
        all_scenarios.extend(generate_browser_deep_workflows())
        all_scenarios.extend(generate_text_editor_workflows())
        all_scenarios.extend(generate_system_admin_workflows())
        # NEW: Visual Automation & Monitoring
        all_scenarios.extend(generate_visual_automation_scenarios())
        all_scenarios.extend(generate_monitoring_scenarios())
    
    # Return all scenarios without deduplication to maximize dataset size
    # Each scenario is already varied enough through the loop iterations
    return all_scenarios


def _merge_agent_examples() -> List[Dict[str, Any]]:
    """Collect all new agent-style examples."""
    merged: List[Dict[str, Any]] = []
    merged.extend(generate_intent_plan_examples(80))
    merged.extend(generate_tool_trace_examples(80))
    merged.extend(generate_multistep_task_examples(100))
    merged.extend(generate_failure_recovery_examples(60))
    merged.extend(generate_persona_planning_examples(80))
    return merged


# === MULTI-TURN CONVERSATION TEMPLATES ===

def create_multi_turn_conversation() -> Dict:
    """Generate 3-5 turn conversations with context, clarifications, follow-ups"""
    conversation_types = [
        # Type 1: Clarification flow
        {
            "messages": [
                {"role": "system", "content": "You are Kayas, a friendly assistant. When the user's request is ambiguous, ask a specific clarifying question before taking action."},
                {"role": "user", "content": "Send the report to John"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Which report would you like me to send? And do you mean John Smith (john.smith@company.com) or John Davis (john.davis@company.com)?",
                    "actions": []
                }, indent=2)},
                {"role": "user", "content": "The Q3 report, send it to John Smith"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Got it! Sending the Q3 report to John Smith now.",
                    "actions": [{
                        "tool": "email.send",
                        "args": {
                            "to": "john.smith@company.com",
                            "subject": "Q3 Report",
                            "body": "Hi John,\n\nPlease find the Q3 report attached.\n\nBest,\nKayas",
                            "attachments": ["reports/Q3_report.pdf"]
                        }
                    }]
                }, indent=2)}
            ],
            "category": "multi_turn",
            "scenario": "clarification_flow"
        },
        
        # Type 2: Context switching
        {
            "messages": [
                {"role": "system", "content": "You are Kayas, a helpful assistant that tracks conversation context."},
                {"role": "user", "content": "Find my budget spreadsheet"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Searching for your budget spreadsheet...",
                    "actions": [{"tool": "local.search", "args": {"query": "budget spreadsheet"}}]
                }, indent=2)},
                {"role": "user", "content": "Actually, never mind. Can you play some music instead?"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Sure thing! What type of music would you like?",
                    "actions": []
                }, indent=2)},
                {"role": "user", "content": "Something chill"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Playing chill music for you! 🎵",
                    "actions": [{"tool": "spotify.play_query", "args": {"query": "chill"}}]
                }, indent=2)}
            ],
            "category": "multi_turn",
            "scenario": "context_switch"
        },
        
        # Type 3: Progressive refinement
        {
            "messages": [
                {"role": "system", "content": "You are Kayas, helping users refine their requests."},
                {"role": "user", "content": "I need to organize my files"},
                {"role": "assistant", "content": json.dumps({
                    "response": "I can help with that! Which files would you like to organize? Recent downloads, project files, or something else?",
                    "actions": []
                }, indent=2)},
                {"role": "user", "content": "My project files from last month"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Should I create an archive or move them to a specific folder?",
                    "actions": []
                }, indent=2)},
                {"role": "user", "content": "Create a zip archive"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Creating archive of last month's project files!",
                    "actions": [{
                        "tool": "filesystem.archive_file",
                        "args": {"filename": f"archive/projects_{(datetime.now() - timedelta(days=30)).strftime('%Y_%m')}.zip"}
                    }]
                }, indent=2)}
            ],
            "category": "multi_turn",
            "scenario": "progressive_refinement"
        },
        
        # Type 4: Error recovery
        {
            "messages": [
                {"role": "system", "content": "You are Kayas. If a tool fails, explain briefly and propose a safe recovery plan."},
                {"role": "user", "content": "Open Chrome and go to GitHub"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Opening Chrome and navigating to GitHub...",
                    "actions": [
                        {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}},
                        {"tool": "browser.run_steps", "args": {"steps": [{"action": "goto", "args": {"url": "https://github.com"}}]}}
                    ]
                }, indent=2)},
                {"role": "user", "content": "Chrome crashed"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Oh no! Let me try restarting Chrome. If it crashes again, I can try opening GitHub in Edge instead.",
                    "actions": [
                        {"tool": "process.kill_process", "args": {"process_name": "chrome.exe"}},
                        {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}}
                    ]
                }, indent=2)},
                {"role": "user", "content": "Still not working, try Edge"},
                {"role": "assistant", "content": json.dumps({
                    "response": "No problem! Opening in Edge instead.",
                    "actions": [
                        {"tool": "process.start_program", "args": {"program": "msedge.exe", "background": True}},
                        {"tool": "browser.run_steps", "args": {"steps": [{"action": "goto", "args": {"url": "https://github.com"}}]}}
                    ]
                }, indent=2)}
            ],
            "category": "multi_turn",
            "scenario": "error_recovery"
        },
        
        # Type 5: Follow-up actions
        {
            "messages": [
                {"role": "system", "content": "You are Kayas, tracking task sequences."},
                {"role": "user", "content": "Create a new project folder called api_gateway"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Creating project folder for api_gateway!",
                    "actions": [
                        {"tool": "filesystem.create_file", "args": {"filename": "api_gateway/README.md", "content": "# API Gateway\n\n## Overview\n\n## Setup\n\n"}},
                        {"tool": "filesystem.create_file", "args": {"filename": "api_gateway/requirements.txt", "content": ""}}
                    ]
                }, indent=2)},
                {"role": "user", "content": "Great! Now add a gitignore file"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Adding .gitignore to the api_gateway project.",
                    "actions": [{
                        "tool": "filesystem.create_file",
                        "args": {
                            "filename": "api_gateway/.gitignore",
                            "content": "__pycache__/\n*.pyc\n.env\nvenv/\n.vscode/\n"
                        }
                    }]
                }, indent=2)},
                {"role": "user", "content": "And initialize git"},
                {"role": "assistant", "content": json.dumps({
                    "response": "Initializing git repository in api_gateway!",
                    "actions": [{
                        "tool": "process.run_command",
                        "args": {"command": "git init", "cwd": "./api_gateway"}
                    }]
                }, indent=2)}
            ],
            "category": "multi_turn",
            "scenario": "follow_up_actions"
        },
    ]
    
    return random.choice(conversation_types)


AMBIGUOUS_PROMPTS = [
    "Hey can you find my recent docs?",
    "Make a zip of my last week’s work.",
    "Send it to John.",
    "Open that thing from yesterday.",
    "Email the report.",
    "Schedule it for later.",
    "Share the file with the team.",
    "Archive those logs.",
    "Back it up.",
    "Organize everything from last month.",
    "Clean up my downloads.",
    "Prepare the presentation.",
    "Can you send this to finance?",
    "Book the meeting room.",
    "Post the update."
]

AMBIGUOUS_QUESTIONS = [
    "Which files do you mean? Recent by date, name, or folder?",
    "Which time range should I include for the zip?",
    "Who is John (email address)?",
    "Which item from yesterday should I open?",
    "Which report are you referring to?",
    "What exactly should I schedule (event name, date/time)?",
    "Which file and which team/channel should I share to?",
    "Which logs and what date range?",
    "What should I back up and where should I store it?",
    "Which items from last month should I organize and how?",
    "What should I keep vs delete in Downloads?",
    "Which presentation and what audience?",
    "What is the finance email or channel?",
    "Which day/time and room capacity?",
    "Where should I post and what content?"
]


# Human-style dialog templates (slang, indirect, typos, emojis)
HUMAN_DIALOG_TEMPLATES = [
    "yo can u shoot that report to navya again?",
    "mind sending that thing to yasser, the project report one?",
    "could u like find my docs from last week n zip em?",
    "hey, can you ping slack abt the update and share the file?",
    "lemme see the budget sheet, open it for me",
    "brb but schedule the meeting for tmrw 3pm, thx",
    "pls create a quick todo, nothing fancy",
    "idk which file it was, can you find the latest draft?",
    "that browser died lol, try again later",
    "send the deck to the team (same as last time)",
]


def create_human_dialog_examples() -> List[Dict[str, Any]]:
    """Generate human-style dialog examples with friendly responses and actions."""
    examples: List[Dict[str, Any]] = []
    for text in HUMAN_DIALOG_TEMPLATES:
        # Map a few intents to plausible tools
        if "navya" in text or "yasser" in text or "send the deck" in text:
            tools = [
                {"tool": "email.send", "args": {
                    "to": "navya@company.com" if "navya" in text else ("yasser@company.com" if "yasser" in text else "team@company.com"),
                    "subject": "Project Report" if ("report" in text or "deck" in text) else "Shared File",
                    "body": "Hi, sending the item you requested.",
                    "attachments": ["project_report.docx"] if ("report" in text or "deck" in text) else []
                }}
            ]
        elif "budget" in text:
            tools = [
                {"tool": "local.search", "args": {"query": "budget sheet"}},
                {"tool": "process.start_program", "args": {"program": "excel.exe", "background": True}}
            ]
        elif "zip" in text or "zip em" in text:
            tools = [
                {"tool": "local.search", "args": {"query": "last week docs"}},
                {"tool": "filesystem.archive_file", "args": {"filename": "last_week_docs.zip"}}
            ]
        elif "slack" in text and "share" in text:
            tools = [
                {"tool": "slack.send_message", "args": {"channel": "#updates", "text": "Project update posted."}}
            ]
        elif "schedule" in text:
            tools = [
                {"tool": "calendar.create_event", "args": {
                    "summary": "Meeting",
                    "start_time": "2025-10-25T15:00:00",
                    "end_time": "2025-10-25T16:00:00",
                    "description": "Auto-scheduled by Kayas"
                }}
            ]
        elif "todo" in text:
            tools = [
                {"tool": "filesystem.create_file", "args": {"filename": "todo.txt", "content": "- [ ] Task 1\n"}}
            ]
        elif "browser died" in text or "try again later" in text:
            # Error-recovery flavored human dialog
            response = "Looks like the browser crashed. I'll retry in 5 minutes and let you know if it fails again."
            examples.append({
                "messages": [
                    {"role": "system", "content": "You are Kayas, a friendly assistant. If a tool fails, explain briefly and propose a safe recovery plan."},
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": json.dumps({
                        "response": response,
                        "actions": [
                            {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}}
                        ]
                    }, indent=2)}
                ],
                "category": "human_dialog",
                "scenario": "error_recovery"
            })
            continue
        else:
            # Default: ask clarification
            examples.append(create_clarification_example(text, "Could you share a few more details so I do the right thing?"))
            examples[-1]["category"] = "human_dialog"
            examples[-1]["scenario"] = "ambiguous_human"
            continue

        # Add a personality-flavored human dialog output by default
        examples.append(create_personality_example(
            text,
            tools,
            friendly_response="You got it — on it now!",
            category="human_dialog",
            scenario="slang_indirect"
        ))
    return examples


def create_tool_only_example(command: str, tools: List[Dict], *, category: str = "synthetic", scenario: str = "auto-generated") -> Dict:
    """Create a tool-only example (no personality). Category/scenario can be customized."""
    system_prompt = """You are Kayas, an intelligent AI assistant that helps users accomplish tasks by calling the appropriate tools.

When given a command, respond with a JSON array of tool calls. Each tool call has:
- "tool": the tool name (e.g., "filesystem.create_file")
- "args": a dictionary of arguments

Available tools:
- filesystem.create_file, filesystem.append_file, filesystem.delete_file, filesystem.archive_file
- browser.run_steps (with steps array)
- email.send
- process.start_program, process.run_command, process.get_system_info, process.kill_process, process.list_processes
- clipboard.copy_text, clipboard.paste_text, clipboard.get_history
- uia.click_button, uia.type_text, uia.close_window, uia.list_windows, uia.get_control_tree, uia.find_window, uia.focus_window
- spotify.play_query, spotify.pause_playback, spotify.get_current_playing, spotify.resume_playback
- slack.send_message, slack.search_messages
- calendar.list_events, calendar.create_event, calendar.delete_event
- network.http_request, network.download_file
- local.search
- cv.screenshot
- ocr.read_screen, ocr.find_text, ocr.click_text

Respond ONLY with valid JSON. No explanation, just the tool calls."""
    
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
            {"role": "assistant", "content": json.dumps(tools, indent=2)}
        ],
        "category": category,
        "scenario": scenario
    }


def create_personality_example(command: str, tools: List[Dict], friendly_response: str, *, category: str = "synthetic", scenario: str = "auto-generated-personality") -> Dict:
    """Create a personality-aware example. Category/scenario can be customized."""
    system_prompt = """You are Kayas, a friendly and helpful AI assistant. You have a warm personality and genuinely care about helping users.

When users ask you to do something:
1. First, acknowledge their request warmly
2. Then provide the JSON tool calls
3. Optionally add a brief confirmation

Format:
{
  "response": "Your friendly message here",
  "actions": [{"tool": "...", "args": {...}}]
}

Be natural, friendly, and professional. Use emojis sparingly and appropriately."""
    
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
            {"role": "assistant", "content": json.dumps({
                "response": friendly_response,
                "actions": tools
            }, indent=2)}
        ],
        "category": category,
        "scenario": scenario
    }


def create_clarification_example(command: str, question: str) -> Dict:
    """Create an example where the assistant asks for clarification and performs no actions."""
    system_prompt = """You are Kayas, a friendly, safe assistant. When the user's request is ambiguous, ask a specific clarifying question before taking action. If information is missing (like which file, which recipient, which time range), respond with a short, warm question and do not call any tools until clarified.

Format:
{
  "response": "Your clarifying question",
  "actions": []
}

Respond only with JSON in the above format."""
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
            {"role": "assistant", "content": json.dumps({
                "response": question,
                "actions": []
            }, indent=2)}
        ],
        "category": "clarification",
        "scenario": "ambiguous"
    }


def generate_ui_continuation_scenarios() -> List[Dict]:
    """Generate multi-step UI flows where second command continues the first.
    These teach the model to handle state persistence and follow-up actions."""
    scenarios = []
    
    # Pattern 1: Open app → interact with startup dialog (CRITICAL for account picker)
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Track the last action and use UI automation when apps show dialogs."},
            {"role": "user", "content": "open chrome"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening Chrome...",
                "actions": [{"tool": "process.start_program", "args": {"program": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "background": True}}]
            }, indent=2)},
            {"role": "user", "content": "use the kayas account"},
            {"role": "assistant", "content": json.dumps({
                "response": "Selecting your profile...",
                "actions": [{"tool": "perception.smart_click", "args": {"target": "Kayas", "context": {"window_title": "Chrome"}}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "chrome_profile_selection"
    })
    
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Track state and handle account/profile selections."},
            {"role": "user", "content": "launch microsoft edge"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening Edge...",
                "actions": [{"tool": "process.start_program", "args": {"program": "msedge.exe", "background": True}}]
            }, indent=2)},
            {"role": "user", "content": "select work profile"},
            {"role": "assistant", "content": json.dumps({
                "response": "Switching to work profile...",
                "actions": [{"tool": "perception.smart_click", "args": {"target": "work", "context": {}}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "edge_profile_selection"
    })
    
    # Pattern 2: Open app → use keyboard shortcut
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Use keyboard shortcuts for UI actions when appropriate."},
            {"role": "user", "content": "open notepad"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening Notepad...",
                "actions": [{"tool": "process.start_program", "args": {"program": "notepad.exe", "background": True}}]
            }, indent=2)},
            {"role": "user", "content": "type hello world"},
            {"role": "assistant", "content": json.dumps({
                "response": "Typing...",
                "actions": [{"tool": "perception.smart_type", "args": {"text": "hello world"}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "text_input"
    })
    
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Continue from previous actions."},
            {"role": "user", "content": "open vs code"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening VS Code...",
                "actions": [{"tool": "process.start_program", "args": {"program": "code.exe", "background": True}}]
            }, indent=2)},
            {"role": "user", "content": "create a new file"},
            {"role": "assistant", "content": json.dumps({
                "response": "Creating new file...",
                "actions": [{"tool": "desktop.send_keys", "args": {"keys": "Ctrl+N"}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "vscode_new_file"
    })
    
    # Pattern 3: Open file dialog → select file
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Handle file dialogs via UI automation."},
            {"role": "user", "content": "open a file in notepad"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening file dialog...",
                "actions": [
                    {"tool": "process.start_program", "args": {"program": "notepad.exe", "background": True}},
                    {"tool": "desktop.send_keys", "args": {"keys": "Ctrl+O"}}
                ]
            }, indent=2)},
            {"role": "user", "content": "select notes.txt"},
            {"role": "assistant", "content": json.dumps({
                "response": "Selecting notes.txt...",
                "actions": [
                    {"tool": "perception.smart_type", "args": {"text": "notes.txt"}},
                    {"tool": "desktop.send_keys", "args": {"keys": "Enter"}}
                ]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "file_dialog"
    })
    
    # Pattern 4: Search → click result
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. After web search, allow clicking specific results."},
            {"role": "user", "content": "search python tutorials on google"},
            {"role": "assistant", "content": json.dumps({
                "response": "Searching...",
                "actions": [{"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "goto", "args": {"url": "https://google.com/search?q=python+tutorials"}}
                ]}}]
            }, indent=2)},
            {"role": "user", "content": "open the first result"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening first result...",
                "actions": [{"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "click", "args": {"selector": "#search div.g:first-child a"}}
                ]}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "search_click_result"
    })
    
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Handle sequential web actions."},
            {"role": "user", "content": "go to youtube"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening YouTube...",
                "actions": [{"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "goto", "args": {"url": "https://youtube.com"}}
                ]}}]
            }, indent=2)},
            {"role": "user", "content": "search for ai tutorials"},
            {"role": "assistant", "content": json.dumps({
                "response": "Searching YouTube...",
                "actions": [{"tool": "browser.run_steps", "args": {"steps": [
                    {"action": "type", "args": {"selector": "input[name='search_query']", "text": "ai tutorials"}},
                    {"action": "click", "args": {"selector": "#search-icon-legacy"}}
                ]}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "youtube_search"
    })
    
    # Pattern 5: Screenshot → describe/OCR
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Use OCR/vision to describe screen content."},
            {"role": "user", "content": "take a screenshot"},
            {"role": "assistant", "content": json.dumps({
                "response": "Screenshot saved!",
                "actions": [{"tool": "desktop.screenshot", "args": {"filename": f"screenshots/capture_{get_timestamp()}.png"}}]
            }, indent=2)},
            {"role": "user", "content": "what's on screen"},
            {"role": "assistant", "content": json.dumps({
                "response": "Reading screen...",
                "actions": [{"tool": "perception.smart_read", "args": {"context": {}}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "screenshot_describe"
    })
    
    # Pattern 6: Open app → click button
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Handle UI button interactions."},
            {"role": "user", "content": "open calculator"},
            {"role": "assistant", "content": json.dumps({
                "response": "Opening Calculator...",
                "actions": [{"tool": "process.start_program", "args": {"program": "calc.exe", "background": True}}]
            }, indent=2)},
            {"role": "user", "content": "click the 5 button"},
            {"role": "assistant", "content": json.dumps({
                "response": "Clicking 5...",
                "actions": [{"tool": "perception.smart_click", "args": {"target": "5", "context": {"control_type": "button"}}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "calculator_button"
    })
    
    # Pattern 7: Email → reply
    scenarios.append({
        "messages": [
            {"role": "system", "content": "You are Kayas. Handle email workflows."},
            {"role": "user", "content": "check my email"},
            {"role": "assistant", "content": json.dumps({
                "response": "Checking email...",
                "actions": [{"tool": "email.list_recent", "args": {"limit": 10}}]
            }, indent=2)},
            {"role": "user", "content": "reply to the first one"},
            {"role": "assistant", "content": json.dumps({
                "response": "Composing reply...",
                "actions": [{"tool": "email.send", "args": {"to": "sender@example.com", "subject": "Re: Previous subject", "body": ""}}]
            }, indent=2)}
        ],
        "category": "ui_continuation",
        "scenario": "email_reply"
    })
    
    return scenarios


def expand_dataset(base_examples: List[Dict], target_count: int = 1000) -> List[Dict]:
    """Expand dataset to target count with high-quality, diverse examples"""
    expanded = list(base_examples)
    
    print(f"Starting with {len(expanded)} base examples...")
    
    # Inject agent-style examples first to cover intent→plan, tool traces, multi-step tasks, failures, persona+planning
    agent_examples = _merge_agent_examples()
    for ex in agent_examples:
        if len(expanded) >= target_count:
            break
        expanded.append(ex)

    # Get all dynamic scenarios (200+ unique)
    all_scenarios = get_all_scenarios()
    print(f"Generated {len(all_scenarios)} unique scenarios")
    
    # Add UI continuation scenarios (10% of target) - CRITICAL for follow-up commands
    ui_continuation_target = int(0.10 * target_count)
    ui_continuation_examples = generate_ui_continuation_scenarios()
    ui_continuation_count = 0
    
    while ui_continuation_count < ui_continuation_target and len(expanded) < target_count:
        expanded.append(ui_continuation_examples[ui_continuation_count % len(ui_continuation_examples)])
        ui_continuation_count += 1
    
    print(f"Added {ui_continuation_count} UI continuation examples (state persistence & follow-ups)")
    
    # Add multi-turn conversations (10% of target)
    multi_turn_target = int(0.10 * target_count)
    multi_turn_count = 0
    while multi_turn_count < multi_turn_target and len(expanded) < target_count:
        expanded.append(create_multi_turn_conversation())
        multi_turn_count += 1
    print(f"Added {multi_turn_count} multi-turn conversations")
    
    # Generate from scenarios with semantic variations
    for scenario_text, tools in all_scenarios:
        if len(expanded) >= target_count:
            break
            
        for template in COMMAND_TEMPLATES[:5]:  # Semantic variations, not just politeness
            if len(expanded) >= target_count:
                break
                
            # Format command
            if "{command}" in template:
                command_text = scenario_text.lower()
                command = template.format(command=command_text)
            else:
                command = scenario_text  # Use original if template doesn't fit
            
            # 50/50 split: tool-only vs personality
            if random.random() < 0.5:
                expanded.append(create_tool_only_example(command, tools, category="synthetic", scenario="dynamic"))
            else:
                friendly_responses = [
                    f"On it! {scenario_text}",
                    f"Sure! {scenario_text} now.",
                    f"Got it, handling it.",
                    f"No problem!",
                ]
                expanded.append(create_personality_example(
                    command,
                    tools,
                    random.choice(friendly_responses),
                    category="personality",
                    scenario="friendly"
                ))

    # Add clarification examples (ambiguous requests)
    clarification_target = int(0.08 * target_count)
    clarification_count = 0
    for prompt, question in zip(AMBIGUOUS_PROMPTS, AMBIGUOUS_QUESTIONS):
        if clarification_count >= clarification_target or len(expanded) >= target_count:
            break
        expanded.append(create_clarification_example(prompt, question))
        clarification_count += 1
    print(f"Added {clarification_count} clarification examples")
    
    # Add error scenarios (15% of target)
    error_target = int(0.15 * target_count)
    error_count = 0
    error_scenarios = generate_error_scenarios()
    while error_count < error_target and len(expanded) < target_count:
        # Create error/clarification examples
        error_text, _ = random.choice(error_scenarios) if error_scenarios else ("Invalid request", [])
        error_response = random.choice([
            "I can't do that for safety reasons. Can you clarify what you need?",
            "That file doesn't exist. Which file did you mean?",
            "I need more information to complete this request.",
            "That operation failed. Would you like me to try a different approach?",
        ])
        expanded.append(create_clarification_example(error_text, error_response))
        error_count += 1
    print(f"Added {error_count} error/edge case examples")
    
    # Add human-style dialog (tunable ratio)
    desired_human = max(1, int(globals().get('_DESIRED_HUMAN_RATIO', 0.15) * target_count))
    def count_cat(items, cat):
        return sum(1 for it in items if it.get("category") == cat)
    current_human = count_cat(expanded, "human_dialog")
    if current_human < desired_human and len(expanded) < target_count:
        human_examples = create_human_dialog_examples()
        idx = 0
        while current_human < desired_human and len(expanded) < target_count:
            expanded.append(human_examples[idx % len(human_examples)])
            idx += 1
            current_human += 1
    print(f"Added {current_human} human-style dialog examples")

    # Fill remaining with diverse sampling
    while len(expanded) < target_count:
        source = random.choice(all_scenarios) if all_scenarios else random.choice(base_examples if base_examples else expanded[:100])
        if isinstance(source, tuple):
            scenario_text, tools = source
            template = random.choice(COMMAND_TEMPLATES)
            command = template.format(command=scenario_text.lower()) if "{command}" in template else scenario_text
            expanded.append(create_tool_only_example(command, tools, category="synthetic", scenario="filler"))
        else:
            expanded.append(source)
    
    # Shuffle for better distribution
    random.shuffle(expanded)
    
    return expanded[:target_count]



def main():
    parser = argparse.ArgumentParser(description="Expand dataset to target size")
    parser.add_argument("--target", type=int, default=1500, help="Target number of examples (e.g., 1500, 5000)")
    parser.add_argument("--output", type=str, default=None, help="Optional output filename (.jsonl). Defaults to mega_brain_dataset_<target>.jsonl")
    parser.add_argument("--human_ratio", type=float, default=0.15, help="Proportion of human-style dialog (0.10–0.20 recommended)")
    args = parser.parse_args()

    data_dir = Path(__file__).parent / "training_data"

    print("🌟 MEGA DATASET EXPANSION")
    print("=" * 80)

    # Load existing
    combined_path = data_dir / "combined_mega_dataset.jsonl"
    if combined_path.exists():
        print(f"📂 Loading {combined_path}...")
        base_data = load_jsonl(combined_path)
    else:
        print("⚠️ combined_mega_dataset.jsonl not found, creating from scratch...")
        base_data = []

    print(f"   Loaded {len(base_data)} base examples")

    # Expand
    print(f"\n🚀 Expanding to {args.target} examples...")
    # Monkey-patch desired human ratio into function scope by closure variable
    global _DESIRED_HUMAN_RATIO
    _DESIRED_HUMAN_RATIO = max(0.0, min(0.5, args.human_ratio))
    mega_data = expand_dataset(base_data, target_count=args.target)

    # Save
    output_name = args.output if args.output else f"mega_brain_dataset_{args.target}.jsonl"
    output_path = data_dir / output_name
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in mega_data:
            f.write(json.dumps(item) + '\n')

    print(f"\n✅ Generated {len(mega_data)} examples!")
    print(f"📁 Saved to: {output_path}")

    # Statistics
    categories = {}
    for item in mega_data:
        cat = item.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n📊 Breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"   {cat}: {count}")

    print(f"\n💡 Update finetune_brain.py:")
    print(f'   "train_data_path": Path(__file__).parent / "training_data" / "{output_name}"')


if __name__ == "__main__":
    main()
