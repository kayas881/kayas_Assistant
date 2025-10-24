# Conversation Improvements

## Fixed Issues

### 1. Multi-word App Names
**Problem**: When you said "open microsoft teams", the agent only looked at "microsoft" and ignored "teams".

**Solution**: Enhanced the app name parser to:
- Check for multi-word apps first (e.g., "microsoft teams", "visual studio code", "google chrome")
- Use glob patterns to find Windows Store apps
- Added support for: Teams, VS Code, Office apps (Word, Excel, Outlook), PowerShell

**Supported Apps**:
- Microsoft Teams
- Visual Studio Code / VS Code
- Google Chrome
- Microsoft Edge
- Word, Excel, Outlook
- Spotify
- Notepad, Calculator
- PowerShell, Command Prompt

### 2. Context Memory for Follow-ups
**Problem**: When you said "I meant teams" after "open microsoft", the agent couldn't understand the reference.

**Solution**: Added context resolution that:
- Remembers the last few messages in the conversation
- Resolves follow-ups like "I meant X", "no, X", "actually X"
- Handles single-word corrections (e.g., just saying "teams" after "open microsoft")

**Examples**:
```
You: open microsoft
Kayas: Got it! I took care of that for you.
You: i meant teams
→ Resolves to: "open teams"

You: open microsoft
Kayas: Got it! I took care of that for you.
You: teams
→ Resolves to: "open microsoft teams"
```

## How It Works

### Context Resolution Flow
1. User says something ambiguous (e.g., "teams")
2. Agent looks at recent conversation history
3. Detects patterns:
   - "I meant X" → interprets as correction
   - Single word after "open X" → adds to app name
4. Resolves to full command (e.g., "open microsoft teams")

### App Name Matching
1. Extracts everything after "open"
2. Checks multi-word names first (most specific)
3. Falls back to single-word names
4. Uses Windows paths + glob for Store apps
5. Falls back to shell `start` command if no path found

## Technical Details

### Files Changed
- `src/voice/direct_agent.py`:
  - Enhanced `run()` to accept `conversation_context` parameter
  - Added `_resolve_context()` method for follow-up resolution
  - Improved app name parser with multi-word support and glob patterns
  
- `src/voice/conversation.py`:
  - Updated to pass conversation context to agent

### Testing
Validated with:
- Multi-word apps: "open microsoft teams" ✓
- Context resolution: "i meant teams" → "open teams" ✓
- Continuation: "teams" after "open microsoft" → "open microsoft teams" ✓
