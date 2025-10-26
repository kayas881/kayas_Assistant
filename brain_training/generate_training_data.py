"""
Generate training data for the AI Brain (Action Planner).

This script creates synthetic training examples that teach an LLM to:
1. Understand user commands in natural language
2. Output structured JSON tool calls using your existing executors

The model learns to be a "Tool User" - translating intent into action sequences.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class TrainingExample:
    """A single training example: user command → tool sequence"""
    user_command: str
    tools_sequence: List[Dict[str, Any]]
    explanation: str  # Why this sequence makes sense
    category: str  # Type of task (filesystem, browser, email, etc.)


# ==================== FILESYSTEM EXAMPLES ====================
FILESYSTEM_EXAMPLES = [
    TrainingExample(
        user_command="Create a new file called meeting_notes.txt",
        tools_sequence=[
            {"tool": "filesystem.create_file", "args": {"filename": "meeting_notes.txt", "content": ""}}
        ],
        explanation="Direct file creation command",
        category="filesystem"
    ),
    TrainingExample(
        user_command="Write 'Project deadline: Friday' to my notes",
        tools_sequence=[
            {"tool": "filesystem.append_file", "args": {"filename": "notes.txt", "content": "\nProject deadline: Friday\n"}}
        ],
        explanation="Appending content to default notes file",
        category="filesystem"
    ),
    TrainingExample(
        user_command="Delete the old_report.pdf file",
        tools_sequence=[
            {"tool": "filesystem.delete_file", "args": {"filename": "old_report.pdf"}}
        ],
        explanation="File deletion request",
        category="filesystem"
    ),
    TrainingExample(
        user_command="Archive the finished_project.txt file",
        tools_sequence=[
            {"tool": "filesystem.archive_file", "args": {"filename": "finished_project.txt"}}
        ],
        explanation="Move file to archive folder",
        category="filesystem"
    ),
    TrainingExample(
        user_command="Create a shopping list and add milk, eggs, and bread",
        tools_sequence=[
            {"tool": "filesystem.create_file", "args": {"filename": "shopping_list.txt", "content": "- Milk\n- Eggs\n- Bread\n"}}
        ],
        explanation="Create file with initial content",
        category="filesystem"
    ),
]


# ==================== BROWSER EXAMPLES ====================
BROWSER_EXAMPLES = [
    TrainingExample(
        user_command="Open YouTube and search for Python tutorials",
        tools_sequence=[
            {
                "tool": "browser.run_steps",
                "args": {
                    "steps": [
                        {"action": "goto", "args": {"url": "https://www.youtube.com"}},
                        {"action": "fill", "args": {"selector": "input[name='search_query']", "value": "Python tutorials"}},
                        {"action": "click", "args": {"selector": "button#search-icon-legacy"}},
                        {"action": "wait", "args": {"seconds": 2}}
                    ],
                    "headless": False
                }
            }
        ],
        explanation="Navigate to YouTube, search for content",
        category="browser"
    ),
    TrainingExample(
        user_command="Go to GitHub and check my notifications",
        tools_sequence=[
            {
                "tool": "browser.run_steps",
                "args": {
                    "steps": [
                        {"action": "goto", "args": {"url": "https://github.com/notifications"}},
                        {"action": "wait", "args": {"seconds": 2}}
                    ],
                    "headless": False
                }
            }
        ],
        explanation="Direct navigation to GitHub notifications",
        category="browser"
    ),
    TrainingExample(
        user_command="Search Google for the weather today",
        tools_sequence=[
            {
                "tool": "browser.run_steps",
                "args": {
                    "steps": [
                        {"action": "goto", "args": {"url": "https://www.google.com/search?q=weather+today"}},
                        {"action": "wait", "args": {"seconds": 2}}
                    ]
                }
            }
        ],
        explanation="Google search with query in URL",
        category="browser"
    ),
]


# ==================== EMAIL EXAMPLES ====================
EMAIL_EXAMPLES = [
    TrainingExample(
        user_command="Send an email to yasser@company.com saying 'Meeting at 3pm'",
        tools_sequence=[
            {
                "tool": "email.send",
                "args": {
                    "to": "yasser@company.com",
                    "subject": "Meeting at 3pm",
                    "body": "Hi Yasser,\n\nJust a reminder about our meeting scheduled for 3pm today.\n\nBest regards"
                }
            }
        ],
        explanation="Email with subject and body",
        category="email"
    ),
    TrainingExample(
        user_command="Email the team about tomorrow's deadline",
        tools_sequence=[
            {
                "tool": "email.send",
                "args": {
                    "to": "team@company.com",
                    "subject": "Reminder: Tomorrow's Deadline",
                    "body": "Hi Team,\n\nThis is a reminder that we have a deadline tomorrow. Please ensure all tasks are completed.\n\nThanks!"
                }
            }
        ],
        explanation="Team email with formal reminder",
        category="email"
    ),
]


# ==================== PROCESS EXAMPLES ====================
PROCESS_EXAMPLES = [
    TrainingExample(
        user_command="Open Notepad",
        tools_sequence=[
            {"tool": "process.start_program", "args": {"program": "notepad.exe", "background": True}}
        ],
        explanation="Launch Windows Notepad",
        category="process"
    ),
    TrainingExample(
        user_command="Run the command 'dir' to list files",
        tools_sequence=[
            {"tool": "process.run_command", "args": {"command": "dir", "shell": True}}
        ],
        explanation="Execute shell command",
        category="process"
    ),
    TrainingExample(
        user_command="Open Calculator",
        tools_sequence=[
            {"tool": "process.start_program", "args": {"program": "calc.exe", "background": True}}
        ],
        explanation="Launch Windows Calculator",
        category="process"
    ),
    TrainingExample(
        user_command="Check system information",
        tools_sequence=[
            {"tool": "process.get_system_info", "args": {}}
        ],
        explanation="Retrieve CPU, RAM, disk info",
        category="process"
    ),
]


# ==================== CLIPBOARD EXAMPLES ====================
CLIPBOARD_EXAMPLES = [
    TrainingExample(
        user_command="Copy 'Hello World' to clipboard",
        tools_sequence=[
            {"tool": "clipboard.copy_text", "args": {"text": "Hello World"}}
        ],
        explanation="Store text in clipboard",
        category="clipboard"
    ),
    TrainingExample(
        user_command="What's in my clipboard?",
        tools_sequence=[
            {"tool": "clipboard.paste_text", "args": {}}
        ],
        explanation="Retrieve current clipboard text",
        category="clipboard"
    ),
    TrainingExample(
        user_command="Show my clipboard history",
        tools_sequence=[
            {"tool": "clipboard.get_history", "args": {"limit": 10}}
        ],
        explanation="Get last 10 clipboard items",
        category="clipboard"
    ),
]


# ==================== UI AUTOMATION EXAMPLES ====================
UIAUTOMATION_EXAMPLES = [
    TrainingExample(
        user_command="Click the OK button in Notepad",
        tools_sequence=[
            {"tool": "uia.click_button", "args": {"window_title": "Notepad", "button_text": "OK"}}
        ],
        explanation="Find Notepad window and click OK button",
        category="uiautomation"
    ),
    TrainingExample(
        user_command="Type 'Hello' in Notepad",
        tools_sequence=[
            {"tool": "uia.type_text", "args": {"window_title": "Notepad", "text": "Hello"}}
        ],
        explanation="Type text into active Notepad window",
        category="uiautomation"
    ),
    TrainingExample(
        user_command="Close the Chrome window",
        tools_sequence=[
            {"tool": "uia.close_window", "args": {"window_title": "Chrome"}}
        ],
        explanation="Close window by title",
        category="uiautomation"
    ),
    TrainingExample(
        user_command="Show me what windows are open",
        tools_sequence=[
            {"tool": "uia.list_windows", "args": {}}
        ],
        explanation="List all visible windows",
        category="uiautomation"
    ),
    TrainingExample(
        user_command="Get all the controls in Calculator",
        tools_sequence=[
            {"tool": "uia.get_control_tree", "args": {"window_title": "Calculator"}}
        ],
        explanation="Extract accessibility tree for Calculator app",
        category="uiautomation"
    ),
]


# ==================== MULTI-STEP EXAMPLES ====================
MULTISTEP_EXAMPLES = [
    TrainingExample(
        user_command="Find the report file and email it to Yasser",
        tools_sequence=[
            {"tool": "local.search", "args": {"query": "report"}},
            {"tool": "email.send", "args": {"to": "yasser@company.com", "subject": "Report File", "body": "Hi Yasser,\n\nAttached is the report you requested.\n\nBest regards"}}
        ],
        explanation="Search for file, then send email (note: real implementation would need attachment support)",
        category="multistep"
    ),
    TrainingExample(
        user_command="Create a meeting note and copy it to clipboard",
        tools_sequence=[
            {"tool": "filesystem.create_file", "args": {"filename": "meeting_note.txt", "content": "Meeting Summary:\n- Discussed project timeline\n- Action items assigned\n"}},
            {"tool": "clipboard.copy_text", "args": {"text": "Meeting Summary:\n- Discussed project timeline\n- Action items assigned\n"}}
        ],
        explanation="Create file then copy same content to clipboard",
        category="multistep"
    ),
    TrainingExample(
        user_command="Open Chrome, search for Python documentation, and take a screenshot",
        tools_sequence=[
            {"tool": "process.start_program", "args": {"program": "chrome.exe", "background": True}},
            {
                "tool": "browser.run_steps",
                "args": {
                    "steps": [
                        {"action": "goto", "args": {"url": "https://www.google.com/search?q=Python+documentation"}},
                        {"action": "wait", "args": {"seconds": 2}},
                        {"action": "screenshot", "args": {"filename": "python_docs_search.png"}}
                    ]
                }
            }
        ],
        explanation="Launch browser, navigate, capture screenshot",
        category="multistep"
    ),
    TrainingExample(
        user_command="Check what's in my clipboard and save it to a file",
        tools_sequence=[
            {"tool": "clipboard.paste_text", "args": {}},
            {"tool": "filesystem.create_file", "args": {"filename": "clipboard_backup.txt", "content": ""}}
        ],
        explanation="Retrieve clipboard content then save to file (executor would handle content transfer)",
        category="multistep"
    ),
]


# ==================== SPOTIFY EXAMPLES ====================
SPOTIFY_EXAMPLES = [
    TrainingExample(
        user_command="Play some jazz music",
        tools_sequence=[
            {"tool": "spotify.play_query", "args": {"query": "jazz"}}
        ],
        explanation="Search and play jazz music on Spotify",
        category="spotify"
    ),
    TrainingExample(
        user_command="Pause the music",
        tools_sequence=[
            {"tool": "spotify.pause_playback", "args": {}}
        ],
        explanation="Pause current Spotify playback",
        category="spotify"
    ),
    TrainingExample(
        user_command="What song is playing?",
        tools_sequence=[
            {"tool": "spotify.get_current_playing", "args": {}}
        ],
        explanation="Get currently playing track info",
        category="spotify"
    ),
]


# ==================== SLACK EXAMPLES ====================
SLACK_EXAMPLES = [
    TrainingExample(
        user_command="Send a message to the dev team channel saying 'Build is ready'",
        tools_sequence=[
            {"tool": "slack.send_message", "args": {"channel": "dev-team", "text": "Build is ready"}}
        ],
        explanation="Post message to Slack channel",
        category="slack"
    ),
    TrainingExample(
        user_command="Search Slack for messages about 'deployment'",
        tools_sequence=[
            {"tool": "slack.search_messages", "args": {"query": "deployment", "count": 20}}
        ],
        explanation="Search Slack message history",
        category="slack"
    ),
]


# ==================== COMBINE ALL EXAMPLES ====================
ALL_EXAMPLES = (
    FILESYSTEM_EXAMPLES +
    BROWSER_EXAMPLES +
    EMAIL_EXAMPLES +
    PROCESS_EXAMPLES +
    CLIPBOARD_EXAMPLES +
    UIAUTOMATION_EXAMPLES +
    MULTISTEP_EXAMPLES +
    SPOTIFY_EXAMPLES +
    SLACK_EXAMPLES
)


def generate_chat_format_dataset(examples: List[TrainingExample], output_path: Path) -> None:
    """
    Generate training data in chat format for instruction fine-tuning.
    
    Format:
    System: You are an AI assistant that helps users by calling the right tools.
    User: [command]
    Assistant: [JSON tool calls]
    """
    dataset = []
    
    system_prompt = """You are Kayas, an intelligent AI assistant that helps users accomplish tasks by calling the appropriate tools.

When given a command, respond with a JSON array of tool calls. Each tool call has:
- "tool": the tool name (e.g., "filesystem.create_file")
- "args": a dictionary of arguments

Available tools:
- filesystem.create_file, filesystem.append_file, filesystem.delete_file, filesystem.archive_file
- browser.run_steps (with steps array)
- email.send
- process.start_program, process.run_command, process.get_system_info
- clipboard.copy_text, clipboard.paste_text, clipboard.get_history
- uia.click_button, uia.type_text, uia.close_window, uia.list_windows, uia.get_control_tree
- spotify.play_query, spotify.pause_playback, spotify.get_current_playing
- slack.send_message, slack.search_messages
- local.search

Respond ONLY with valid JSON. No explanation, just the tool calls."""
    
    for example in examples:
        # Create a chat conversation
        conversation = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": example.user_command},
                {"role": "assistant", "content": json.dumps(example.tools_sequence, indent=2)}
            ],
            "category": example.category,
            "explanation": example.explanation
        }
        dataset.append(conversation)
    
    # Save to JSONL (one JSON object per line)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item) + '\n')
    
    print(f"✅ Generated {len(dataset)} training examples")
    print(f"📁 Saved to: {output_path}")
    print(f"\nBreakdown by category:")
    category_counts = {}
    for item in dataset:
        cat = item['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")


def augment_examples(base_examples: List[TrainingExample], multiplier: int = 3) -> List[TrainingExample]:
    """
    Augment training data by creating variations.
    
    Strategies:
    1. Rephrase user commands (synonyms, different tenses)
    2. Add politeness variations ("please", "can you")
    3. Add casual variations ("yo", "hey")
    """
    augmented = list(base_examples)  # Start with originals
    
    # Rephrasing variations
    rephrase_patterns = [
        (r'^Create', ['Make', 'Build', 'Generate', 'Set up']),
        (r'^Open', ['Launch', 'Start', 'Run', 'Fire up']),
        (r'^Send', ['Email', 'Message', 'Send out', 'Shoot']),
        (r'^Search', ['Look for', 'Find', 'Look up', 'Query']),
        (r'^Show', ['Display', 'Get', 'List', 'Tell me']),
    ]
    
    politeness_prefixes = ['Please ', 'Could you ', 'Can you ', 'Would you mind to ']
    casual_prefixes = ['Hey, ', 'Yo, ', '', '']  # Empty strings to keep some without prefix
    
    for example in base_examples:
        variations = []
        
        # Generate rephrased versions
        for pattern, replacements in rephrase_patterns:
            import re
            if re.match(pattern, example.user_command):
                for replacement in replacements[:2]:  # Use first 2 alternatives
                    new_command = re.sub(pattern, replacement, example.user_command)
                    variations.append(new_command)
        
        # Add politeness/casual variations
        for prefix in random.sample(politeness_prefixes + casual_prefixes, min(2, len(politeness_prefixes + casual_prefixes))):
            variations.append(prefix + example.user_command.lower())
        
        # Create new examples from variations
        for variation in variations[:multiplier - 1]:  # multiplier-1 since we keep original
            augmented.append(TrainingExample(
                user_command=variation,
                tools_sequence=example.tools_sequence,
                explanation=example.explanation,
                category=example.category
            ))
    
    random.shuffle(augmented)
    return augmented


def main():
    output_dir = Path(__file__).parent / "training_data"
    
    print("🧠 Generating AI Brain Training Data...")
    print("=" * 60)
    
    # Generate base dataset
    base_output = output_dir / "brain_training_base.jsonl"
    generate_chat_format_dataset(ALL_EXAMPLES, base_output)
    
    print("\n🔄 Augmenting dataset with variations...")
    augmented_examples = augment_examples(ALL_EXAMPLES, multiplier=5)
    augmented_output = output_dir / "brain_training_augmented.jsonl"
    generate_chat_format_dataset(augmented_examples, augmented_output)
    
    print("\n" + "=" * 60)
    print("✅ Dataset generation complete!")
    print(f"\n📊 Stats:")
    print(f"  Base examples: {len(ALL_EXAMPLES)}")
    print(f"  Augmented examples: {len(augmented_examples)}")
    print(f"\n💡 Next steps:")
    print(f"  1. Review the generated files in {output_dir}")
    print(f"  2. Run the fine-tuning script: python finetune_brain.py")
    print(f"  3. Train on L4 GPU for ~2-3 hours")


if __name__ == "__main__":
    main()
