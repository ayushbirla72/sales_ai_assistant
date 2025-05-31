from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly'
]

class GoogleCalendarService:
    def __init__(self):
        self.service = None

    def authenticate_with_access_token(self, access_token: str):
        """Authenticate with Google Calendar using a valid OAuth access token (not an ID token)."""
        try:
            print("Authenticating with access token...")

            credentials = Credentials(
                token=access_token,
                scopes=SCOPES
            )

            self.service = build('calendar', 'v3', credentials=credentials)
            print("Google Calendar service initialized.")
        except Exception as e:
            raise ValueError(f"Failed to authenticate: {str(e)}")

    def get_calendar_events(self, access_token: str, max_results: int = 10) -> List[Dict[str, Any]]:
        try:
            self.authenticate_with_access_token(access_token)

            now = datetime.utcnow().isoformat() + 'Z'
            one_week_later = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

            print(f"Fetching events from {now} to {one_week_later}...")

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=one_week_later,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            print(f"Fetched {len(events)} event(s).")

            # Return events in their original format
            return events
        except Exception as e:
            print(f"Error fetching calendar events: {str(e)}")
            return []


calendar_service = GoogleCalendarService() 