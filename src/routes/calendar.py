from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from src.models.calendar_model import CalendarEvent, CalendarEventCreate, CalendarEventResponse
from src.services.calendar_service import calendar_service
from src.services.mongo_service import (
    get_calendar_events_tasks,
    save_calendar_event,
    get_calendar_events,
    get_calendar_event_by_id,
    update_calendar_event,
    delete_calendar_event,
    get_user_details,
    get_calendar_events_by_status,
    get_calendar_events_by_end_time,
    calendar_events_collection
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
    request: Request,
    token_data: dict = Depends(verify_token)
):
    try:
        body = await request.json()
        events = body.get("events", [])
        # if not events:
        #     raise HTTPException(status_code=400, detail="No events provided in request body")

        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Process and save/update events from the request body
        for event_data in events:
            # Check if event exists by id
            existing_event = await get_calendar_event_by_id(event_data["id"], user_id=token_data["user_id"]) if "id" in event_data else None
            
            if existing_event:
                # Update existing event
                updated = await update_calendar_event(
                    existing_event["_id"],
                    {
                        **event_data,
                        "isMeetingDetailsUploaded": existing_event["isMeetingDetailsUploaded"],
                        "updated": datetime.utcnow().isoformat() + 'Z',
                        "user_id": token_data["user_id"]
                    }
                )
                if not updated:
                    raise HTTPException(status_code=500, detail=f"Failed to update event {event_data['id']}")
            else:
                # Create new event
                event_dict = event_data.copy()
                event_dict.update({
                    "created": datetime.utcnow().isoformat() + 'Z',
                    "updated": datetime.utcnow().isoformat() + 'Z',
                    "user_id": token_data["user_id"],
                    "isMeetingDetailsUploaded": False,
                    "autoJoin": True,
                    "mode": "Online"
                })
                
                await save_calendar_event(event_dict)

        # Get current time in UTC
        current_time = datetime.now(timezone.utc)
        
        # Query to get all events that:
        # 1. Belong to the current user
        # 2. Have end time greater than or equal to current time
        # 3. Have status "confirmed"
        query = {
            "user_id": token_data["user_id"],
            "end.dateTime": {"$gte": current_time.isoformat()},
            "status": "confirmed"
        }
        
        # Get all matching events from calendar_events collection
        cursor = calendar_events_collection.find(query).sort("start.dateTime", 1)
        all_events = await cursor.to_list(length=None)
        
        # Add MongoDB _id to each event in the response
        for event in all_events:
            event["eventId"] = str(event["_id"])
        
        return all_events

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/today-started-meetings", response_model=List[CalendarEventResponse])
async def get_today_started_meetings(token_data: dict = Depends(verify_token)):
    """
    Get all meetings that have started today (status = 'start').
    
    Returns:
        List[CalendarEventResponse]: List of started meetings
    """
    try:
        # Get today's date in UTC
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get events with status 'start'
        events = await get_calendar_events_by_status(
            user_id=token_data["user_id"],
            status="start",
            start_date=today
        )
        print(f"events........ {events}")
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/completed-meetings", response_model=List[CalendarEventResponse])
async def get_completed_meetings(token_data: dict = Depends(verify_token)):
    """
    Get all completed meetings where the end time is greater than the current time.
    
    Returns:
        List[CalendarEventResponse]: List of completed meetings
    """
    try:
        # Get current time in UTC
        current_time = datetime.now(timezone.utc)
        
        # Get events with end time greater than current time
        events = await get_calendar_events_by_end_time(
            user_id=token_data["user_id"],
            current_time=current_time
        )
        print(f"events {events}")
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    

@router.post("/meeting-tasks")
async def get_meeting_task(
    request: Request,
    token_data: dict = Depends(verify_token)
):
    try:
        body = await request.json()
        meetingId = body.get("meetingId")
        eventId = body.get("eventId")

        if not meetingId and not eventId:
            raise HTTPException(status_code=400, detail="Either meetingId or eventId is required")

        tasks = await get_calendar_events_tasks(
            user_id=token_data["user_id"],
            meetingId=meetingId,
            eventId=eventId
        )

        if not tasks:
            raise HTTPException(status_code=404, detail="No tasks found for the given meeting/event")
        
        for task in tasks:
            task["_id"] = str(task["_id"])

        return tasks

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
