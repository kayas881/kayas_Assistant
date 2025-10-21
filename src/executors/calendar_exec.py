from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from ..agent.config import google_calendar_config
from pathlib import Path


@dataclass
class CalendarConfig:
    credentials_file: str
    token_file: str
    scopes: List[str]


class GoogleCalendarExecutor:
    def __init__(self, cfg: CalendarConfig):
        self.cfg = cfg
        self.service = None
        if GOOGLE_AVAILABLE:
            self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        creds = None
        token_path = Path(self.cfg.token_file)
        
        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.cfg.scopes)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.cfg.credentials_file or not Path(self.cfg.credentials_file).exists():
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(self.cfg.credentials_file, self.cfg.scopes)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)

    def list_events(self, calendar_id: str = 'primary', max_results: int = 10, days_ahead: int = 7) -> Dict:
        """List upcoming events"""
        if not GOOGLE_AVAILABLE or not self.service:
            return {"error": "Google Calendar API not available or not authenticated"}
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            future = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                timeMax=future,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                })
            
            return {
                "action": "calendar.list_events",
                "events": formatted_events,
                "count": len(formatted_events)
            }
        except Exception as e:
            return {"error": f"Failed to list events: {str(e)}"}

    def create_event(self, summary: str, start_time: str, end_time: str, 
                    description: str = "", location: str = "", calendar_id: str = 'primary') -> Dict:
        """Create a new calendar event"""
        if not GOOGLE_AVAILABLE or not self.service:
            return {"error": "Google Calendar API not available or not authenticated"}
        
        try:
            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
            }
            
            created_event = self.service.events().insert(
                calendarId=calendar_id, 
                body=event
            ).execute()
            
            return {
                "action": "calendar.create_event",
                "event_id": created_event['id'],
                "link": created_event.get('htmlLink', ''),
                "summary": summary,
                "start": start_time
            }
        except Exception as e:
            return {"error": f"Failed to create event: {str(e)}"}

    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> Dict:
        """Delete a calendar event"""
        if not GOOGLE_AVAILABLE or not self.service:
            return {"error": "Google Calendar API not available or not authenticated"}
        
        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return {
                "action": "calendar.delete_event",
                "event_id": event_id,
                "deleted": True
            }
        except Exception as e:
            return {"error": f"Failed to delete event: {str(e)}"}

    def find_free_time(self, duration_minutes: int = 60, days_ahead: int = 7, 
                      start_hour: int = 9, end_hour: int = 17) -> Dict:
        """Find free time slots in calendar"""
        if not GOOGLE_AVAILABLE or not self.service:
            return {"error": "Google Calendar API not available or not authenticated"}
        
        try:
            # Get busy times
            now = datetime.utcnow()
            future = now + timedelta(days=days_ahead)
            
            body = {
                "timeMin": now.isoformat() + 'Z',
                "timeMax": future.isoformat() + 'Z',
                "items": [{"id": "primary"}]
            }
            
            freebusy = self.service.freebusy().query(body=body).execute()
            busy_times = freebusy['calendars']['primary'].get('busy', [])
            
            # Find free slots
            free_slots = []
            current_day = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            
            while current_day < future and len(free_slots) < 5:
                if current_day.weekday() < 5:  # Weekdays only
                    day_end = current_day.replace(hour=end_hour)
                    slot_start = current_day
                    
                    while slot_start + timedelta(minutes=duration_minutes) <= day_end:
                        slot_end = slot_start + timedelta(minutes=duration_minutes)
                        
                        # Check if slot conflicts with busy times
                        is_free = True
                        for busy in busy_times:
                            busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                            busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                            
                            if (slot_start < busy_end and slot_end > busy_start):
                                is_free = False
                                break
                        
                        if is_free:
                            free_slots.append({
                                "start": slot_start.isoformat() + 'Z',
                                "end": slot_end.isoformat() + 'Z',
                                "duration_minutes": duration_minutes
                            })
                        
                        slot_start += timedelta(minutes=30)  # 30-minute increments
                
                current_day += timedelta(days=1)
                current_day = current_day.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            
            return {
                "action": "calendar.find_free_time",
                "free_slots": free_slots[:5],  # Return top 5 slots
                "duration_minutes": duration_minutes
            }
        except Exception as e:
            return {"error": f"Failed to find free time: {str(e)}"}