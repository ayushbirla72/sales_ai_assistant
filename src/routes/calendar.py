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
        event = await get_calendar_event_by_id(event_id, token_data["user_id"])
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
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
        event = await get_calendar_event_by_id(event_id, token_data["user_id"])
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        updated = await update_calendar_event(event_id, event_data.dict())
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update event")
        
        updated_event = await get_calendar_event_by_id(event_id, token_data["user_id"])
        return updated_event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/{event_id}")
async def delete_event(event_id: str, token_data: dict = Depends(verify_token)):
    """Delete a calendar event."""
    try:
        event = await get_calendar_event_by_id(event_id, token_data["user_id"])
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        deleted = await delete_calendar_event(event_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete event")
        
        return {"message": "Event deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-events", response_model=List[CalendarEventResponse])
async def sync_events_from_body(
    events: List[CalendarEventCreate],
    token_data: dict = Depends(verify_token)
):
    """Sync calendar events from request body to the database.
    If an event with the same event_id exists, it will be updated instead of created.
    """
    try:
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        synced_events = []
        for event_data in events:
            # Check if event exists by event_id
            existing_event = await get_calendar_event_by_id(event_data.event_id,user_id=token_data["user_id"]) if hasattr(event_data, 'event_id') else None
            
            if existing_event:
                # Update existing event
                if existing_event["user_id"] != token_data["user_id"]:
                    raise HTTPException(status_code=403, detail=f"Not authorized to update event {event_data.event_id}")
                
                updated = await update_calendar_event(
                    existing_event["_id"],
                    {
                        **event_data.dict(),
                        "updated_at": datetime.utcnow(),
                        "user_id": token_data["user_id"]
                    }
                )
                if not updated:
                    raise HTTPException(status_code=500, detail=f"Failed to update event {event_data.event_id}")
                
                updated_event = await get_calendar_event_by_id(existing_event["_id"])
                synced_events.append(updated_event)
            else:
                # Create new event
                event_dict = event_data.dict()
                event_dict.update({
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "user_id": token_data["user_id"]
                })
                
                event_id = await save_calendar_event(event_dict)
                event_dict["_id"] = event_id
                synced_events.append(event_dict)
        
        return synced_events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 