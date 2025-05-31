from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, HttpUrl, validator
from typing import Optional
from src.services.external_meeting_service import (
    join_external_meeting,
    get_meeting_status,
    end_meeting
)
from src.routes.auth import verify_token
from src.services.mongo_service import get_user_details, get_meeting_by_id
from src.config import ADMIN_GMAIL_EMAIL, ADMIN_GMAIL_PASSWORD

router = APIRouter()

async def verify_admin(token_data: dict = Depends(verify_token)):
    """
    Verify if the user is an admin.
    
    Args:
        token_data (dict): Token data from authentication
        
    Returns:
        dict: Token data if user is admin
        
    Raises:
        HTTPException: If user is not an admin
    """
    user = await get_user_details({"email": token_data["email"]})
    if not user or not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action"
        )
    return token_data

class JoinMeetingRequest(BaseModel):
    gmeet_link: HttpUrl
    duration_in_minutes: Optional[int] = 10
    userId: Optional[str] = None
    meetingId: Optional[str] = None
    max_wait_time_in_minutes: Optional[int] = 2

    @validator('duration_in_minutes')
    def validate_duration(cls, v):
        if v < 1 or v > 120:  # Limit meeting duration between 1 and 120 minutes
            raise ValueError('Duration must be between 1 and 120 minutes')
        return v

    @validator('max_wait_time_in_minutes')
    def validate_wait_time(cls, v):
        if v < 1 or v > 30:  # Limit wait time between 1 and 30 minutes
            raise ValueError('Wait time must be between 1 and 30 minutes')
        return v

    @validator('meetingId')
    def validate_meeting_id(cls, v, values):
        if v:
            # Check if meeting exists in database
            meeting = get_meeting_by_id(v)
            if not meeting:
                raise ValueError('Invalid meeting ID')
        return v

class MeetingStatusRequest(BaseModel):
    meeting_id: str

    @validator('meeting_id')
    def validate_meeting_id(cls, v):
        if not v:
            raise ValueError('Meeting ID is required')
        return v

class EndMeetingRequest(BaseModel):
    meeting_id: str

    @validator('meeting_id')
    def validate_meeting_id(cls, v):
        if not v:
            raise ValueError('Meeting ID is required')
        return v

@router.post("/join")
async def join_meeting(
    data: JoinMeetingRequest,
    token_data: dict = Depends(verify_admin)
):
    """
    Join an external Google Meet session.
    Only administrators can perform this action.
    
    Args:
        data (JoinMeetingRequest): Meeting join request data
        token_data (dict): Token data from authentication
        
    Returns:
        dict: Meeting join response
        
    Raises:
        HTTPException: If meeting join fails
    """
    try:
        # Verify user exists
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # If meetingId is provided, verify it exists
        if data.meetingId:
            meeting = await get_meeting_by_id(data.meetingId)
            if not meeting:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Meeting not found"
                )

        result = await join_external_meeting(
            gmeet_link=str(data.gmeet_link),
            gmail_user_email=ADMIN_GMAIL_EMAIL,
            gmail_user_password=ADMIN_GMAIL_PASSWORD,
            duration_in_minutes=data.duration_in_minutes,
            userId=data.userId or token_data["user_id"],
            meetingId=data.meetingId,
            max_wait_time_in_minutes=data.max_wait_time_in_minutes
        )
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to join meeting: {str(e)}"
        )

@router.get("/status/{meeting_id}")
async def check_meeting_status(
    meeting_id: str,
    token_data: dict = Depends(verify_admin)
):
    """
    Get the status of an ongoing meeting.
    Only administrators can perform this action.
    
    Args:
        meeting_id (str): ID of the meeting to check
        token_data (dict): Token data from authentication
        
    Returns:
        dict: Meeting status information
        
    Raises:
        HTTPException: If status check fails
    """
    try:
        # Verify meeting exists
        meeting = await get_meeting_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        result = await get_meeting_status(meeting_id)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get meeting status: {str(e)}"
        )

@router.post("/end/{meeting_id}")
async def terminate_meeting(
    meeting_id: str,
    token_data: dict = Depends(verify_admin)
):
    """
    End an ongoing meeting.
    Only administrators can perform this action.
    
    Args:
        meeting_id (str): ID of the meeting to end
        token_data (dict): Token data from authentication
        
    Returns:
        dict: Meeting end response
        
    Raises:
        HTTPException: If meeting termination fails
    """
    try:
        # Verify meeting exists
        meeting = await get_meeting_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        result = await end_meeting(meeting_id)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end meeting: {str(e)}"
        ) 