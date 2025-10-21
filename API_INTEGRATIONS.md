# API Integrations

The agent now supports external API integrations for Google Calendar, Slack, and Spotify. These integrations allow the agent to interact with external services and automate tasks across different platforms.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the required packages:
- `google-api-python-client` - Google Calendar API
- `slack-sdk` - Slack API 
- `spotipy` - Spotify API

### 2. Configure API Credentials

Each API integration requires credentials to be configured. The agent supports both environment variables and profile-based configuration.

#### Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
4. Create credentials (OAuth 2.0 Client ID for desktop application)
5. Download the credentials JSON file

Set environment variables:
```bash
export GOOGLE_CALENDAR_CREDENTIALS_FILE="/path/to/credentials.json"
export GOOGLE_CALENDAR_TOKEN_FILE="/path/to/token.json"
export GOOGLE_CALENDAR_SCOPES="https://www.googleapis.com/auth/calendar"
```

Or use profile config in `.agent/config.yaml`:
```yaml
google_calendar:
  credentials_file: "/path/to/credentials.json"
  token_file: "/path/to/token.json"
  scopes: ["https://www.googleapis.com/auth/calendar"]
```

#### Slack

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app for your workspace
3. Under "OAuth & Permissions", add required scopes:
   - `chat:write` - Send messages
   - `channels:read` - List channels  
   - `users:read` - Get user info
   - `search:read` - Search messages
4. Install app to workspace and copy the Bot User OAuth Token

Set environment variables:
```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_USER_TOKEN="xoxp-your-user-token"  # Optional
```

Or use profile config:
```yaml
slack:
  bot_token: "xoxb-your-bot-token"
  user_token: "xoxp-your-user-token"  # Optional
```

#### Spotify

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Note the Client ID and Client Secret
4. Add redirect URI (e.g., `http://localhost:8080`)

Set environment variables:
```bash
export SPOTIFY_CLIENT_ID="your-client-id"
export SPOTIFY_CLIENT_SECRET="your-client-secret"
export SPOTIFY_REDIRECT_URI="http://localhost:8080"
export SPOTIFY_SCOPE="user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-public"
```

Or use profile config:
```yaml
spotify:
  client_id: "your-client-id"
  client_secret: "your-client-secret"
  redirect_uri: "http://localhost:8080"
  scope: "user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-public"
```

## Available Tools

### Google Calendar

- **calendar.list_events** - List upcoming events
  - `calendar_id` (optional): Calendar to query (default: "primary")
  - `max_results` (optional): Maximum events to return (default: 10)
  - `days_ahead` (optional): Number of days to look ahead (default: 7)

- **calendar.create_event** - Create a new event
  - `summary` (required): Event title
  - `start_time` (required): Start time in ISO format
  - `end_time` (required): End time in ISO format
  - `description` (optional): Event description
  - `location` (optional): Event location
  - `calendar_id` (optional): Target calendar (default: "primary")

- **calendar.delete_event** - Delete an event
  - `event_id` (required): Event ID to delete
  - `calendar_id` (optional): Calendar containing event (default: "primary")

- **calendar.find_free_time** - Find available time slots
  - `duration_minutes` (optional): Required meeting duration (default: 60)
  - `days_ahead` (optional): Number of days to search (default: 7)
  - `start_hour` (optional): Start of work day (default: 9)
  - `end_hour` (optional): End of work day (default: 17)

### Slack

- **slack.send_message** - Send a message to a channel
  - `channel` (required): Channel name or ID
  - `text` (required): Message text
  - `thread_ts` (optional): Thread timestamp for replies

- **slack.list_channels** - List workspace channels
  - `types` (optional): Channel types to include (default: "public_channel,private_channel")
  - `limit` (optional): Maximum channels to return (default: 100)

- **slack.get_user_info** - Get user information
  - `user_id` (required): User ID to query

- **slack.search_messages** - Search for messages
  - `query` (required): Search query
  - `count` (optional): Maximum results (default: 20)

- **slack.set_status** - Set user status
  - `text` (required): Status text
  - `emoji` (optional): Status emoji
  - `expiration` (optional): Status expiration timestamp

### Spotify

- **spotify.search_music** - Search for music
  - `query` (required): Search query
  - `search_type` (optional): Type to search ("track", "album", "artist") (default: "track")
  - `limit` (optional): Maximum results (default: 10)

- **spotify.play_track** - Play a track
  - `track_uri` (required): Spotify track URI
  - `device_id` (optional): Target device ID

- **spotify.get_current_playing** - Get currently playing track
  - No parameters

- **spotify.pause_playback** - Pause current playback
  - `device_id` (optional): Target device ID

- **spotify.resume_playback** - Resume playback
  - `device_id` (optional): Target device ID

- **spotify.get_user_playlists** - Get user's playlists
  - `limit` (optional): Maximum playlists (default: 20)

- **spotify.create_playlist** - Create a new playlist
  - `name` (required): Playlist name
  - `description` (optional): Playlist description
  - `public` (optional): Make playlist public (default: true)

- **spotify.add_tracks_to_playlist** - Add tracks to playlist
  - `playlist_id` (required): Target playlist ID
  - `track_uris` (required): List of track URIs to add

## Usage Examples

### Using the Agent CLI

```bash
# Calendar
python -m src.agent.main "List my calendar events for the next 3 days"
python -m src.agent.main "Create a meeting called 'Project Review' tomorrow at 2pm for 1 hour"
python -m src.agent.main "Find free time slots for a 30-minute meeting this week"

# Slack
python -m src.agent.main "Send a message to #general saying 'Hello team!'"
python -m src.agent.main "List all channels in the workspace"
python -m src.agent.main "Search for messages about 'project deadline'"

# Spotify
python -m src.agent.main "Search for songs by The Beatles"
python -m src.agent.main "Play the song 'Yesterday' by The Beatles"
python -m src.agent.main "Create a playlist called 'Coding Music'"
```

### Using the API Server

```bash
# Start the server
python -m src.server.main

# Calendar endpoints
curl -X POST "http://localhost:8000/tools/calendar/list_events" \
  -H "Content-Type: application/json" \
  -d '{"calendar_id": "primary", "max_results": 5}'

curl -X POST "http://localhost:8000/tools/calendar/create_event" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Team Meeting",
    "start_time": "2024-01-15T14:00:00Z",
    "end_time": "2024-01-15T15:00:00Z",
    "description": "Weekly team sync"
  }'

# Slack endpoints
curl -X POST "http://localhost:8000/tools/slack/send_message" \
  -H "Content-Type: application/json" \
  -d '{"channel": "#general", "text": "Hello from the agent!"}'

curl -X POST "http://localhost:8000/tools/slack/list_channels" \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'

# Spotify endpoints
curl -X POST "http://localhost:8000/tools/spotify/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "rock music", "search_type": "track", "limit": 10}'

curl -X GET "http://localhost:8000/tools/spotify/current"
```

## Error Handling

All API integrations include graceful error handling:

1. **Missing Dependencies**: If the required Python packages are not installed, the executor will return an error message indicating the API is not available.

2. **Authentication Failures**: If credentials are invalid or missing, appropriate error messages are returned.

3. **API Errors**: Network issues, rate limiting, and other API-specific errors are caught and returned with descriptive error messages.

4. **Graceful Degradation**: The agent will continue to function with available tools even if some API integrations fail to initialize.

## Security Notes

- Never commit API credentials to version control
- Use environment variables or secure configuration files for credentials  
- Regularly rotate API tokens and secrets
- Follow the principle of least privilege when setting up API permissions
- Monitor API usage for unusual activity

## Troubleshooting

### Google Calendar
- Ensure the Calendar API is enabled in Google Cloud Console
- Check that OAuth 2.0 consent screen is configured
- Verify the credentials file path is correct
- For first-time setup, the OAuth flow will open a browser window

### Slack
- Verify bot token has required scopes
- Check that the app is installed in the target workspace
- Ensure channel names include the # prefix where required

### Spotify
- Confirm redirect URI matches exactly between app and config
- Check that required scopes are included
- For first-time setup, the OAuth flow will open a browser window
- Ensure you have an active Spotify Premium account for playback control

For additional help, check the error messages returned by each executor - they provide specific guidance on resolving common issues.