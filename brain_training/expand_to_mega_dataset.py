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


# Aggregate all scenario generators
def get_all_scenarios() -> List[tuple]:
    """Generate comprehensive scenario pool (200+)"""
    all_scenarios = []
    
    # Generate multiple batches with randomization
    for _ in range(3):  # Generate 3x to ensure diversity
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
    
    # Deduplicate by text (keep first occurrence)
    seen = set()
    unique_scenarios = []
    for text, tools in all_scenarios:
        if text not in seen:
            seen.add(text)
            unique_scenarios.append((text, tools))
    
    return unique_scenarios


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


def expand_dataset(base_examples: List[Dict], target_count: int = 1000) -> List[Dict]:
    """Expand dataset to target count with high-quality, diverse examples"""
    expanded = list(base_examples)
    
    print(f"Starting with {len(expanded)} base examples...")
    
    # Get all dynamic scenarios (200+ unique)
    all_scenarios = get_all_scenarios()
    print(f"Generated {len(all_scenarios)} unique scenarios")
    
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
