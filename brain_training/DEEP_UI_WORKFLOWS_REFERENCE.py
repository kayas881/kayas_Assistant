#!/usr/bin/env python3
"""
Quick Reference: Deep UI Workflows Structure

This shows the exact pattern structure for each deep UI workflow category.
Use this to understand or extend the workflows.
"""

# ============================================================================
# 1. MESSAGING WORKFLOWS PATTERN
# ============================================================================

"""
WHATSAPP:
  Command: "Open WhatsApp and text {contact} '{message}'"
  
  Pattern:
    1. process.start_program("WhatsApp.exe")
    2. Wait for UI (sleep 3000ms)
    3. Focus window
    4. Open search (Ctrl+F)
    5. Type contact name
    6. Wait for results (1000ms)
    7. Press Enter to select
    8. Wait for chat to load (1500ms)
    9. Click message input
    10. Type message
    11. Send (Enter)
  
  Variations:
    - Multiple contacts: Abdus, Mom, John, Team Lead, Sarah, etc.
    - Multiple messages: "hi", "running late", "check email", etc.
    - Total: 8 contacts × 10 messages = 80 scenarios
    
  Learning: Search → Select → Type → Send pattern


DISCORD:
  Command: "Open Discord and message {channel} in {server} '{message}'"
  
  Pattern:
    1. process.start_program("Discord.exe")
    2. Wait (2000ms)
    3. Click server from sidebar
    4. Wait (1000ms)
    5. Click channel
    6. Click message input
    7. Type message
    8. Send (Enter)
  
  Variations:
    - Servers: Development, Community, Gaming, Work
    - Channels: general, announcements, random, help
    - Total: 4 × 4 = 16 base + 5 messages = 80 scenarios


SLACK:
  Command: "Open Slack and message {user} '{message}'"
  
  Pattern:
    1. process.start_program("slack.exe")
    2. Wait (2500ms) - Slack startup is slower
    3. Open quick switcher (Ctrl+K)
    4. Type user name
    5. Wait (800ms)
    6. Press Enter to open DM
    7. Wait for DM to load (1000ms)
    8. Click message input
    9. Type message
    10. Send (Enter)
  
  Variations:
    - Users: Abdus, Mom, John, Team Lead, Sarah, etc.
    - Messages: 5 variations per user
    - Total: ~65 scenarios
  
  Learning: Quick switcher navigation (Ctrl+K) + DM pattern
"""


# ============================================================================
# 2. SPOTIFY WORKFLOWS PATTERN
# ============================================================================

"""
SEARCH & PLAY:
  Command: "Open Spotify and play '{song}' by {artist}"
  
  Pattern:
    1. process.start_program("Spotify.exe")
    2. Wait (3000ms) - Spotify startup
    3. Focus window
    4. Open search (Ctrl+L)
    5. Type "song artist"
    6. Wait (1500ms) for results
    7. Click song from results
    8. Wait (500ms)
    9. Play (spacebar)
  
  Variations:
    - Artists: The Weeknd, Drake, Taylor Swift, etc. (6 artists)
    - Songs: 2 songs per artist
    - Total: 6 × 2 = 12 scenarios
  
  Learning: Search bar navigation + media playback


PLAYLIST:
  Command: "Open Spotify and play the '{playlist}' playlist"
  
  Pattern:
    1. process.start_program("Spotify.exe")
    2. Wait (3000ms)
    3. Focus window
    4. Click "Search"
    5. Type playlist name
    6. Wait (1200ms)
    7. Click matching playlist
    8. Wait (1000ms) for playlist to load
    9. Play (spacebar)
  
  Variations:
    - Playlists: Chill Vibes, Workout Mix, Focus, Party, Lo-fi (5 total)


PLAYBACK CONTROL:
  Commands:
    - "Play Spotify" → spacebar
    - "Pause Spotify" → spacebar
    - "Skip to next song in Spotify" → Ctrl+Right
    - "Go to previous song in Spotify" → Ctrl+Left
  
  Pattern: Focus window + keyboard shortcut
"""


# ============================================================================
# 3. BROWSER DEEP WORKFLOWS PATTERN
# ============================================================================

"""
SEARCH & EXTRACT:
  Command: "Search '{query}' on Google, open first result, and screenshot"
  
  Pattern:
    1. process.start_program("chrome.exe")
    2. Wait (2000ms)
    3. Navigate to Google
    4. Fill search box with query
    5. Press Enter
    6. Wait (2000ms) for results
    7. Click first result
    8. Wait (2500ms) for page load
    9. Scroll down (3 scrolls)
    10. Screenshot page
  
  Variations:
    - Queries: python async, react hooks, kubernetes, ML, docker (5 total)
  
  Learning: Multi-step extraction, screenshot capture, scroll behavior


GITHUB WORKFLOW:
  Command: "Find and star the {repo} GitHub repository"
  
  Pattern:
    1. process.start_program("chrome.exe")
    2. Wait (2000ms)
    3. Navigate to github.com/{repo}
    4. Wait (2000ms)
    5. Click star button
  
  Variations:
    - Repos: tensorflow, react, cpython, vscode (4 total)


SHOPPING WORKFLOW:
  Command: "Search '{product}' on Amazon, filter by '{filter}', view details"
  
  Pattern:
    1. process.start_program("chrome.exe")
    2. Wait (2000ms)
    3. Navigate to amazon.com
    4. Fill search box
    5. Press Enter
    6. Wait (2000ms)
    7. Click first product
    8. Screenshot product page
  
  Variations:
    - Products: keyboard, laptop stand, monitor (3 total)


YOUTUBE WORKFLOW:
  Command: "Search '{topic}' on YouTube and play first video"
  
  Pattern:
    1. process.start_program("chrome.exe")
    2. Wait (2000ms)
    3. Navigate to youtube.com
    4. Fill search box
    5. Press Enter
    6. Wait (2000ms)
    7. Click first video
    8. Wait (3000ms) for video to load
    9. Play (spacebar)
  
  Variations:
    - Topics: python tutorial, ML explained, javascript (3 total)
"""


# ============================================================================
# 4. TEXT EDITOR WORKFLOWS PATTERN
# ============================================================================

"""
VSCODE FILE CREATION:
  Command: "Open VSCode and create new {language} file '{filename}'"
  
  Pattern:
    1. process.start_program("code.exe")
    2. Wait (3000ms)
    3. Create new file (Ctrl+N)
    4. Type code content
    5. Save (Ctrl+S)
    6. Wait (1000ms) for save dialog
    7. Type filename
    8. Confirm (Enter)
  
  Variations:
    - Languages: python, javascript, html, markdown (4 total)
    - Each with appropriate starter code
  
  Learning: IDE shortcuts (Ctrl+N, Ctrl+S) + file saving dialog


NOTEPAD NOTES:
  Command: "Open Notepad and write '{topic}' with today's date"
  
  Pattern:
    1. process.start_program("notepad.exe")
    2. Wait (1000ms)
    3. Type heading: "{TOPIC} - {DATE}"
    4. Type bullet points (3 items)
    5. Save (Ctrl+S)
    6. Wait (1000ms)
  
  Variations:
    - Topics: meeting notes, ideas, todo, thoughts, observations (5 total)
    - All use same template structure
  
  Learning: Text editor basics + timestamp template pattern
"""


# ============================================================================
# 5. SYSTEM ADMIN WORKFLOWS PATTERN
# ============================================================================

"""
SYSTEM MONITORING:
  Command: "Check system resources (CPU, memory, disk) and report"
  
  Pattern:
    1. process.get_system_info()
    2. process.run_command("Get-Process | Sort by CPU")
    3. process.run_command("Get-Volume | Select size info")
  
  Learning: System query patterns


BACKUP WORKFLOW:
  Command: "Backup {folder} to archive with timestamp"
  
  Pattern:
    1. filesystem.archive_file("backups/{folder}_{timestamp}.zip")
    2. process.run_command("Get-Item to verify archive")
  
  Variations:
    - Folders: Documents, Pictures, Desktop, Downloads (4 total)
  
  Learning: File archiving + verification pattern


CLEANUP WORKFLOW:
  Command: "Clean up old temporary files and reclaim disk space"
  
  Pattern:
    1. process.run_command("Remove-Item $env:TEMP")
    2. process.run_command("Get-Volume to report freed space")
  
  Learning: System maintenance patterns
"""


# ============================================================================
# HOW TO ADD MORE WORKFLOWS
# ============================================================================

"""
To add a new category (e.g., Email workflows):

1. Create generator function:
   
   def generate_email_deep_workflows() -> List[tuple]:
       scenarios = []
       
       recipients = ["john@company.com", "sarah@company.com", ...]
       subjects = ["Project Update", "Meeting Notes", ...]
       
       for recipient in recipients:
           for subject in subjects:
               scenarios.append((
                   f"Send email to {recipient} about '{subject}'",
                   [
                       # Step 1: Open email
                       {"tool": "process.start_program", ...},
                       # Step 2: Compose
                       {"tool": "uia.type_text", ...},
                       # Step 3: Send
                       {"tool": "desktop.send_keys", ...}
                   ]
               ))
       
       return scenarios


2. Add to get_all_scenarios():
   
   all_scenarios.extend(generate_email_deep_workflows())


3. Test with demo:
   
   workflows = generate_email_deep_workflows()
   for text, tools in workflows[:3]:
       print_workflow(text, tools)


KEY PRINCIPLES:
  - Include realistic timing (sleep steps)
  - Use appropriate keyboard shortcuts
  - Test on actual applications
  - Vary contacts/content/parameters
  - Keep steps realistic (not too many, not too few)
  - Include wait times for UI responsiveness
"""


# ============================================================================
# STATISTICS
# ============================================================================

"""
WORKFLOWS GENERATED:

Messaging:        185 scenarios
  WhatsApp:        80 (8 contacts × 10 messages)
  Discord:         80 (4 servers × 4 channels × 5 messages)
  Slack:           65 (5+ users × 5+ messages)

Spotify:           26 scenarios
  Search & Play:   12 (6 artists × 2 songs)
  Playlists:        5
  Playback:         4 (play, pause, skip, previous)
  Create:           5

Browser Deep:      15 scenarios
  Google Search:    5 (5 queries)
  GitHub:           4 (4 repos)
  Amazon:           3 (3 products)
  YouTube:          3 (3 topics)

Text Editors:       9 scenarios
  VSCode:           4 (4 languages)
  Notepad:          5 (5 topics)

System Admin:       7 scenarios
  Monitoring:       1
  Backup:           5 (5 folders)
  Cleanup:          1

────────────────────────────────────
TOTAL:            242 deep UI workflows

When expanded with semantic variations,
this generates 500+ training examples.
"""
