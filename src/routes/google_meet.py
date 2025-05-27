from fastapi import APIRouter, HTTPException, Depends, Body, WebSocket
from typing import List, Optional
from datetime import datetime
from src.routes.auth import verify_token
from src.services.google_meet_service import GoogleMeetService
from src.services.mongo_service import (
    get_user_details,
    create_meeting_session,
    update_meeting_session,
    get_meeting_session
)
from pydantic import BaseModel
import asyncio

router = APIRouter()

class JoinMeetingRequest(BaseModel):
    meeting_id: str
    display_name: Optional[str] = None

class MeetingChatMessage(BaseModel):
    message: str
    timestamp: datetime
    sender: str

@router.post("/join")
async def join_meeting(
    request: JoinMeetingRequest,
    token_data: dict = Depends(verify_token)
):
    """Join a Google Meet meeting as a participant and start monitoring."""
    try:
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.get("is_google_connected"):
            raise HTTPException(
                status_code=400,
                detail="Google account not connected. Please connect your Google account first."
            )

        # Create meeting session
        session = await create_meeting_session({
            "meeting_id": request.meeting_id,
            "user_id": token_data["user_id"],
            "start_time": datetime.utcnow(),
            "status": "active"
        })

        # Join meeting and start monitoring
        meet_service = GoogleMeetService(user["google_access_token"])
        join_url = await meet_service.join_meeting(
            meeting_id=request.meeting_id,
            display_name=request.display_name or user.get("name", "Participant")
        )
        
        # Start monitoring
        await meet_service.start_meeting_monitoring(
            meeting_id=request.meeting_id,
            user_id=token_data["user_id"]
        )
        
        return {
            "message": "Successfully joined meeting and started monitoring",
            "join_url": join_url,
            "session_id": session
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/leave/{meeting_id}")
async def leave_meeting(
    meeting_id: str,
    token_data: dict = Depends(verify_token)
):
    """Leave a Google Meet meeting and stop monitoring."""
    try:
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Stop monitoring
        meet_service = GoogleMeetService(user["google_access_token"])
        await meet_service.stop_meeting_monitoring(meeting_id)

        # Update session status
        await update_meeting_session(
            meeting_id=meeting_id,
            user_id=token_data["user_id"],
            update_data={
                "end_time": datetime.utcnow(),
                "status": "ended"
            }
        )
        
        return {
            "message": "Successfully left meeting and stopped monitoring"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{meeting_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    meeting_id: str,
    token_data: dict = Depends(verify_token)
):
    """WebSocket endpoint for real-time meeting updates."""
    try:
        await websocket.accept()
        
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            await websocket.close(code=4004, reason="User not found")
            return

        meet_service = GoogleMeetService(user["google_access_token"])
        
        while True:
            try:
                # Get latest chat messages
                messages = await meet_service.get_meeting_chat(meeting_id)
                if messages:
                    await websocket.send_json({
                        "type": "chat",
                        "data": messages
                    })

                # Get latest audio chunk
                audio_data = await meet_service.get_meeting_audio(meeting_id)
                if audio_data:
                    await websocket.send_json({
                        "type": "audio",
                        "data": audio_data
                    })

                await asyncio.sleep(1)  # Send updates every second
            except Exception as e:
                print(f"WebSocket error: {str(e)}")
                await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket connection error: {str(e)}")
    finally:
        await websocket.close()

@router.get("/chat/{meeting_id}")
async def get_meeting_chat(
    meeting_id: str,
    token_data: dict = Depends(verify_token)
):
    """Get the chat messages from a Google Meet meeting."""
    try:
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.get("is_google_connected"):
            raise HTTPException(
                status_code=400,
                detail="Google account not connected. Please connect your Google account first."
            )

        meet_service = GoogleMeetService(user["google_access_token"])
        chat_messages = await meet_service.get_meeting_chat(meeting_id)
        
        return {
            "message": "Successfully retrieved chat messages",
            "chat_messages": chat_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/{meeting_id}/send")
async def send_chat_message(
    meeting_id: str,
    message: str = Body(...),
    token_data: dict = Depends(verify_token)
):
    """Send a chat message in a Google Meet meeting."""
    try:
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.get("is_google_connected"):
            raise HTTPException(
                status_code=400,
                detail="Google account not connected. Please connect your Google account first."
            )

        meet_service = GoogleMeetService(user["google_access_token"])
        await meet_service.send_chat_message(
            meeting_id=meeting_id,
            message=message,
            sender=user.get("name", "Participant")
        )
        
        return {
            "message": "Successfully sent chat message"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 