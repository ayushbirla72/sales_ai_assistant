from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class GoogleCalendarService:
    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self):
        """Handles authentication with Google Calendar API."""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('calendar', 'v3', credentials=self.creds)

    def get_calendar_events(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Fetches calendar events for the next 7 days."""
        if not self.service:
            self.authenticate()

        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        one_week_later = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=one_week_later,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_event = {
                'event_id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start_time': start,
                'end_time': end,
                'location': event.get('location', ''),
                'attendees': [attendee['email'] for attendee in event.get('attendees', [])],
                'created_at': event.get('created'),
                'updated_at': event.get('updated')
            }
            formatted_events.append(formatted_event)

        return formatted_events

calendar_service = GoogleCalendarService() 