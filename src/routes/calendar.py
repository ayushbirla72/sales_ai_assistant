from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional
from datetime import datetime
from src.models.calendar_model import CalendarEvent, CalendarEventCreate, CalendarEventResponse
from src.services.calendar_service import calendar_service
from src.services.mongo_service import (
    save_calendar_event,
    get_calendar_events,
    get_calendar_event_by_id,
    update_calendar_event,
    delete_calendar_event,
    get_user_details
)
from src.routes.auth import verify_token
from pydantic import BaseModel

router = APIRouter()

class GoogleCalendarRequest(BaseModel):
    id_token: str

@router.post("/sync", response_model=List[CalendarEventResponse])
async def sync_calendar_events(token_data: dict = Depends(verify_token)):
    """Sync calendar events from Google Calendar to the database."""
    try:
        # Get user from database
        # print(f"token,,,,, {token_data}")
        user = await get_user_details({"email": token_data["email"]})
        # print(f"....... user {user}")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has Google account connected
        if not user.get("is_google_connected"):
            raise HTTPException(
                status_code=400, 
                detail="Google account not connected. Please connect your Google account first."
            )
        
        # Get Google ID token from user document
        id_token = user.get("google_id_token")
        access_token = user.get("google_access_token")
        refresh_token = user.get("google_refresh_token")
        if not id_token:
            raise HTTPException(
                status_code=400,
                detail="Google ID token not found. Please reconnect your Google account."
            )

        # Get events from Google Calendar using the ID token
        events = calendar_service.get_calendar_events(access_token)
        
        # Save events to database
        saved_events = []
        for event in events:
            event["user_id"] = token_data["user_id"]
            event_id = await save_calendar_event(event)
            event["_id"] = event_id
            saved_events.append(event)
        
        return saved_events
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events", response_model=List[CalendarEventResponse])
async def get_events(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    token_data: dict = Depends(verify_token)
):
    """Get calendar events for the authenticated user."""
    try:
        events = await get_calendar_events(
            user_id=token_data["user_id"],
            start_date=start_date,
            end_date=end_date
        )
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/{event_id}", response_model=CalendarEventResponse)
async def get_event(event_id: str, token_data: dict = Depends(verify_token)):
    """Get a specific calendar event."""
    try:
        event = await get_calendar_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event["user_id"] != token_data["user_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this event")
        return event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: str,
    event_data: CalendarEventCreate,
    token_data: dict = Depends(verify_token)
):
    """Update a calendar event."""
    try:
        event = await get_calendar_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event["user_id"] != token_data["user_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this event")
        
        updated = await update_calendar_event(event_id, event_data.dict())
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update event")
        
        updated_event = await get_calendar_event_by_id(event_id)
        return updated_event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/{event_id}")
async def delete_event(event_id: str, token_data: dict = Depends(verify_token)):
    """Delete a calendar event."""
    try:
        event = await get_calendar_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event["user_id"] != token_data["user_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this event")
        
        deleted = await delete_calendar_event(event_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete event")
        
        return {"message": "Event deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 