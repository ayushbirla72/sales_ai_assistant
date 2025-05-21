from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CalendarEvent(BaseModel):
    event_id: str
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = []
    created_at: datetime
    updated_at: datetime
    user_id: str

class CalendarEventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = []

class CalendarEventResponse(CalendarEvent):
    pass 