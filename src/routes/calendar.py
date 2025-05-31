from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
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
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.get("is_google_connected"):
            raise HTTPException(
                status_code=400, 
                detail="Google account not connected. Please connect your Google account first."
            )
        
        access_token = user.get("google_access_token")
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Google access token not found. Please reconnect your Google account."
            )

        events = calendar_service.get_calendar_events(access_token)
        
        saved_events = []
        for event in events:
            event["user_id"] = token_data["user_id"]
            eventId = await save_calendar_event(event)
            event["_id"] = eventId
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

@router.get("/events/{eventId}", response_model=CalendarEventResponse)
async def get_event(eventId: str, token_data: dict = Depends(verify_token)):
    """Get a specific calendar event."""
    try:
        event = await get_calendar_event_by_id(eventId, token_data["user_id"])
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{eventId}", response_model=CalendarEventResponse)
async def update_event(
    eventId: str,
    event_data: CalendarEventCreate,
    token_data: dict = Depends(verify_token)
):
    """Update a calendar event."""
    try:
        event = await get_calendar_event_by_id(eventId, token_data["user_id"])
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        updated = await update_calendar_event(eventId, event_data.dict())
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update event")
        
        updated_event = await get_calendar_event_by_id(eventId, token_data["user_id"])
        return updated_event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/{eventId}")
async def delete_event(eventId: str, token_data: dict = Depends(verify_token)):
    """Delete a calendar event."""
    try:
        event = await get_calendar_event_by_id(eventId, token_data["user_id"])
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        deleted = await delete_calendar_event(eventId)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete event")
        
        return {"message": "Event deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-events", response_model=List[CalendarEventResponse])
async def sync_events_from_body(
    events: List[Dict[str, Any]] = Body(..., description="List of calendar events to sync"),
    token_data: dict = Depends(verify_token)
):
    """Sync calendar events from request body to the database.
    If an event with the same id exists, it will be updated instead of created.
    
    Request body example:
    {
        "events": [
            {
                "summary": "Team Meeting",
                "description": "Weekly sync",
                "start": {
                    "dateTime": "2024-03-20T10:00:00Z",
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": "2024-03-20T11:00:00Z",
                    "timeZone": "UTC"
                },
                "location": "Conference Room A",
                "attendees": [
                    {
                        "email": "user1@example.com",
                        "responseStatus": "needsAction"
                    }
                ],
                "conferenceData": {
                    "conferenceId": "abc-123",
                    "conferenceSolution": {
                        "name": "Google Meet"
                    },
                    "entryPoints": [
                        {
                            "entryPointType": "video",
                            "uri": "https://meet.google.com/abc-123"
                        }
                    ]
                }
            }
        ]
    }
    """
    try:
        if not events:
            raise HTTPException(status_code=400, detail="No events provided in request body")

        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        synced_events = []
        for event_data in events:
            # Check if event exists by id
            existing_event = await get_calendar_event_by_id(event_data["id"], user_id=token_data["user_id"]) if "id" in event_data else None
            
            if existing_event:
                # Update existing event
                updated = await update_calendar_event(
                    existing_event["_id"],
                    {
                        **event_data,
                        "updated": datetime.utcnow().isoformat() + 'Z',
                        "user_id": token_data["user_id"]
                    }
                )
                if not updated:
                    raise HTTPException(status_code=500, detail=f"Failed to update event {event_data['id']}")
                
                updated_event = await get_calendar_event_by_id(event_data["id"], user_id=token_data["user_id"])
                synced_events.append(updated_event)
            else:
                # Create new event
                event_dict = event_data.copy()
                event_dict.update({
                    "created": datetime.utcnow().isoformat() + 'Z',
                    "updated": datetime.utcnow().isoformat() + 'Z',
                    "user_id": token_data["user_id"]
                })
                
                eventId = await save_calendar_event(event_dict)
                event_dict["_id"] = eventId
                synced_events.append(event_dict)
        
        return synced_events
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 