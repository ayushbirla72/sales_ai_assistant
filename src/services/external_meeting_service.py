import aiohttp
from typing import Optional, Dict
import urllib.parse
from src.config import (
    EXTERNAL_MEETING_JOIN_ENDPOINT,
    EXTERNAL_MEETING_STATUS_ENDPOINT,
    EXTERNAL_MEETING_END_ENDPOINT
)

async def join_external_meeting(
    gmeet_link: str,
    gmail_user_email: str,
    gmail_user_password: str,
    duration_in_minutes: int = 10,
    userId: str = None,
    meetingId: str = None,
    max_wait_time_in_minutes: int = 2,
    eventId: str = None
) -> Dict:
    """
    Call the external meeting API to join a Google Meet session.
    
    Args:
        gmeet_link (str): The Google Meet link to join
        gmail_user_email (str): Gmail account email to use
        gmail_user_password (str): Gmail account password
        duration_in_minutes (int, optional): Duration of the meeting in minutes. Defaults to 10.
        userId (str): User ID to use for the meeting. Defaults to None.
        meetingId (str): Meeting ID to use for the meeting. Defaults to None.
        max_wait_time_in_minutes (int, optional): Maximum wait time in minutes. Defaults to 2.
    
    Returns:
        Dict: Response from the external API containing meeting details
        
    Raises:
        Exception: If the API call fails
    """
    try:
        # Prepare query parameters
        params = {
            "GMEET_LINK": gmeet_link,
            "GMAIL_USER_EMAIL": gmail_user_email,
            "GMAIL_USER_PASSWORD": gmail_user_password,
            "DURATION_IN_MINUTES": str(duration_in_minutes),
            "USER_ID": userId,
            "MEETING_ID": meetingId,
            "MAX_WAIT_TIME_IN_MINUTES": str(max_wait_time_in_minutes),
            "EVENT_ID": eventId
        }
        
        # Construct the full URL with query parameters
        url = f"{EXTERNAL_MEETING_JOIN_ENDPOINT}?{urllib.parse.urlencode(params)}"
        
        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    response_data = await response.json()
                    print(response_data)
                    return response_data
                else:
                    error_text = await response.text()
                    raise Exception(f"API call failed with status {response.status}: {error_text}")
                    
    except Exception as e:
        raise Exception(f"Failed to join external meeting: {str(e)}")

async def get_meeting_status(meeting_id: str) -> Dict:
    """
    Get the status of an ongoing meeting.
    
    Args:
        meeting_id (str): The ID of the meeting to check
        
    Returns:
        Dict: Meeting status information
        
    Raises:
        Exception: If the API call fails
    """
    try:
        url = f"{EXTERNAL_MEETING_STATUS_ENDPOINT}?meeting_id={meeting_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API call failed with status {response.status}: {error_text}")
                    
    except Exception as e:
        raise Exception(f"Failed to get meeting status: {str(e)}")

async def end_meeting(meeting_id: str) -> Dict:
    """
    End an ongoing meeting.
    
    Args:
        meeting_id (str): The ID of the meeting to end
        
    Returns:
        Dict: Response indicating the meeting was ended
        
    Raises:
        Exception: If the API call fails
    """
    try:
        url = f"{EXTERNAL_MEETING_END_ENDPOINT}?meeting_id={meeting_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API call failed with status {response.status}: {error_text}")
                    
    except Exception as e:
        raise Exception(f"Failed to end meeting: {str(e)}") 