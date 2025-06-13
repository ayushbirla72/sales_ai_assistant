from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import MONGO_URL, MONGO_DB_NAME
from datetime import datetime, timedelta
from pymongo import DESCENDING

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]

chunks_col = db["chunks"]
final_col = db["finalTranscriptions"]
sales_col = db["salesSamples"]
chunks_col_Transcription = db["transcriptionChunks"]
users_collection = db["users"]
meetings_collection = db["meetings"]
prediction_collection = db["predictions"]
suggestion_collection = db["suggestions"]
meeting_summry_collection = db["meetingSummrys"]
calendar_events_collection = db["calendarEvents"]
calendar_events_tasks_collection = db["calendarEventsTasks"]

# Save chunk metadata
async def save_chunk_metadata(meetingId: str, chunk_name: str, userId: str, transcript: str, s3_url: str , eventId: str, container_id: str):
    now = datetime.utcnow()
    doc = {
        "s3_url": s3_url,
        "transcript": transcript,
        "uploadedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "userId": userId,
        "chunk_name": chunk_name,
        "eventId": eventId,
        "container_id": container_id,
        "meetingId": meetingId
    }
    await chunks_col.update_one(
        {"meetingId": meetingId},
        {
            "$push": {"chunks": doc},
            "$set": {"updatedAt": now},
            "$setOnInsert": {"createdAt": now}
        },
        upsert=True
    )

# Get chunk list
async def get_chunk_list(meetingId: str):
    doc = await chunks_col.find_one({"meetingId": meetingId})
    # print(f"chunksss {doc}")
    return doc["chunks"] if doc else []

# Save final audio
async def save_final_audio(meetingId: str, s3_url: str, results: list, userId: str):
    now = datetime.utcnow()
    doc = {
        "meetingId": meetingId,
        "s3_url": s3_url,
        "results": results,
        "userId": userId,
        "createdAt": now,
        "updatedAt": now
    }
    result = await final_col.insert_one(doc)
    return result.inserted_id

async def get_final_audio(meetingId: str):
    doc = await final_col.find_one({"meetingId": meetingId})
    return doc

# Save salesperson sample
async def save_salesperson_sample(filename: str, s3_url: str, userId: str):
    now = datetime.utcnow()
    doc = {
        "filename": filename,
        "s3_url": s3_url,
        "uploadedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "userId": userId
    }
    result = await sales_col.insert_one(doc)
    return result.inserted_id

# Get salesperson sample
async def get_salesperson_sample(userId: str):
    result = await sales_col.find_one({"userId": userId})
    print(f"data.. {result}")
    return result

# Save transcription chunk
async def save_transcription_chunk(meetingId: str, s3_url: str, transcript: str, userId: str):
    now = datetime.utcnow()
    doc = {
        "meetingId": meetingId,
        "s3_url": s3_url,
        "transcript": transcript,
        "uploadedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "userId": userId
    }
    result = await chunks_col_Transcription.insert_one(doc)
    return result.inserted_id

# Save user details
async def save_user_details(data: dict) -> dict:
    """
    Save user details to the database.
    
    Args:
        data (dict): User data containing:
            - email (str): User's email
            - name (str): User's name
            - password (str, optional): Hashed password
            - google_id (str, optional): Google user ID
            - picture (str, optional): Profile picture URL
            - google_id_token (str, optional): Google ID token
            - is_google_connected (bool, optional): Whether user is connected with Google
            - company_name (str, optional): User's company name
            - mobile_number (str, optional): User's mobile number
            - position (str, optional): User's position in company
            - google_access_token (str, optional): Google OAuth2 access token
            - google_refresh_token (str, optional): Google OAuth2 refresh token
    
    Returns:
        dict: The saved user document with password removed
    """
    now = datetime.utcnow()
    
    # Base document with required fields and defaults
    doc = {
        "email": data["email"],
        "name": data["name"],
        "createdAt": now,
        "updatedAt": now,
        # Default values for optional fields
        "password": None,
        "google_id": None,
        "picture": None,
        "google_id_token": None,
        "is_google_connected": False,
        "company_name": None,
        "mobile_number": None,
        "position": None,
        "google_access_token": None,
        "google_refresh_token": None
    }
    
    # Override defaults with provided values
    for field in [
        "password", "google_id", "picture", "google_id_token",
        "is_google_connected", "company_name", "mobile_number", "position",
        "google_access_token", "google_refresh_token"
    ]:
        if field in data:
            doc[field] = data[field]
    
    # Insert the document
    result = await users_collection.insert_one(doc)
    
    # Get the inserted document and remove password before returning
    inserted_user = await users_collection.find_one({"_id": result.inserted_id})
    if inserted_user and "password" in inserted_user:
        inserted_user["password"] = None
    
    return inserted_user

# Get user details
async def get_user_details(data: dict) -> Optional[dict]:
    """
    Get user details from the database.
    
    Args:
        data (dict): Query data containing:
            - email (str): User's email to search for
    
    Returns:
        Optional[dict]: User document with password removed, or None if not found
    """
    try:
        # Find user by email
        user = await users_collection.find_one({"email": data["email"]})
        
        if not user:
            return None
            
        # Remove password from response
        if "password" in user:
            user["password"] = None
            
        # Ensure all fields exist with defaults if missing
        default_fields = {
            "google_id": None,
            "picture": None,
            "google_id_token": None,
            "is_google_connected": False,
            "company_name": None,
            "mobile_number": None,
            "position": None,
            "google_access_token": None,
            "google_refresh_token": None
        }
        
        # Add any missing fields with defaults
        for field, default_value in default_fields.items():
            if field not in user:
                user[field] = default_value
                
        return user
        
    except Exception as e:
        print(f"Error getting user details: {str(e)}")
        return None

async def create_meeting(data: dict):
    print(f"dataaaaaaa  {data}")
    data["createdAt"] = datetime.utcnow()
    data["updatedAt"] = datetime.utcnow()
    result = await meetings_collection.insert_one(data)
    return result.inserted_id

async def get_all_meetings(userId:str):
    cursor = meetings_collection.find({"userId":userId})
    return await cursor.to_list(length=None)

async def get_meeting_by_id(meeting_id: str):
    doc = await meetings_collection.find_one({"_id": ObjectId(meeting_id)})
    return doc

async def save_prediction_result(userId: str, meetingId: str, question: str, topic: str, result: str):
    now = datetime.utcnow()
    doc = {
        "userId": userId,
        "meetingId": meetingId,
        "question": question,
        "topic": topic,
        "result": result,
        "createdAt": now,
        "updatedAt": now
    }
    res = await prediction_collection.insert_one(doc)
    return res.inserted_id

async def   get_predictions(userId: str, meetingId: str = None):
    now = datetime.utcnow()
    query = {"userId": userId}
    if meetingId:
        query["meetingId"] = meetingId
    cursor = prediction_collection.find(query)
    return await cursor.to_list(length=100)

async def save_suggestion(meetingId: str, userId: str, transcript: str, suggestion: str):
    doc = {
        "meetingId": meetingId,
        "userId": userId,
        "transcript": transcript,
        "suggestion": suggestion,
        "createdAt": datetime.utcnow()
    }
    result = await suggestion_collection.insert_one(doc)
    return result.inserted_id



def serialize_suggestion(suggestion: dict) -> dict:
    suggestion["_id"] = str(suggestion["_id"])  # Convert ObjectId to string
    return suggestion

async def get_suggestions_by_user_and_session(userId: str, meetingId: str):
    query = {"userId": userId, "meetingId": meetingId}
    cursor = suggestion_collection.find(query).sort("updatedAt", -1)  # Sort descending
    results = await cursor.to_list(length=None)
    return [serialize_suggestion(s) for s in results]



async def update_final_summary_and_suggestion(meetingId: str, userId: str, summary: str, suggestion:list):
    now = datetime.utcnow()
    doc = {
        "userId": userId,
        "meetingId": meetingId,
        "summary": summary,
        "suggestion":suggestion,
        "createdAt": now,
        "updatedAt": now
    }
    await meeting_summry_collection.insert_one(
    doc
    )


async def get_summary_and_suggestion(meetingId: str, userId: Optional[str] = None):
    query = {"meetingId": meetingId}
    if userId:
        query["userId"] = userId
    return await meeting_summry_collection.find_one(query)

async def update_user_password(email: str, new_hashed_password: str):
    now = datetime.utcnow()
    result = await users_collection.update_one(
        {"email": email},
        {"$set": {"password": new_hashed_password, "updatedAt": now}}
    )
    return result.modified_count

async def save_calendar_event(event_data: dict):
    """Save a calendar event to the database."""
    now = datetime.utcnow()
    doc = {
        **event_data,
        "createdAt": now,
        "updatedAt": now
    }
    result = await calendar_events_collection.insert_one(doc)
    return result.inserted_id

async def get_calendar_events(user_id: str, start_date: datetime = None, end_date: datetime = None):
    """Get calendar events for a user within a date range."""
    query = {"user_id": user_id}
    
    if start_date and end_date:
        query["start_time"] = {
            "$gte": start_date,
            "$lte": end_date
        }
    
    cursor = calendar_events_collection.find(query).sort("start_time", 1)
    return await cursor.to_list(length=None)

async def get_calendar_event_by_id(eventId: str, user_id: str):
    """Get a specific calendar event by eventId and user_id."""
    try:
        doc = await calendar_events_collection.find_one({
            "id": eventId,
            "user_id": user_id
        })
        return doc
    except:
        return None

async def get_calendar_event_by_id_only(eventId: str):
    """Get a specific calendar event by eventId and user_id."""
    try:
        doc = await calendar_events_collection.find_one({
            "_id": ObjectId(eventId)
        })
        return doc
    except:
        return None


async def update_calendar_event(eventId: str, update_data: dict):
    """Update a calendar event."""
    try:
        result = await calendar_events_collection.update_one(
            {"_id": ObjectId(eventId)},
            {"$set": {**update_data, "updatedAt": datetime.utcnow()}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating calendar event: {str(e)}")
        return False

async def update_meeting_details_uploaded(eventId: str, meetingId: str) -> bool:
    """
    Update the isMeetingDetailsUploaded field to True and add meetingId for a calendar event.
    
    Args:
        eventId (str): The ID of the calendar event
        meetingId (str): The ID of the meeting to associate with the calendar event
    
    Returns:
        bool: True if the update was successful, False otherwise
    """
    try:
        result = await calendar_events_collection.update_one(
            {"_id": ObjectId(eventId)},
            {
                "$set": {
                    "isMeetingDetailsUploaded": True,
                    "meetingId": meetingId,
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating meeting details uploaded status: {str(e)}")
        return False

async def delete_calendar_event(eventId: str):
    """Delete a calendar event."""
    try:
        result = await calendar_events_collection.delete_one({"_id": ObjectId(eventId)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting calendar event: {str(e)}")
        return False

async def update_user_profile(email: str, update_data: dict) -> bool:
    """
    Update user profile information.
    
    Args:
        email (str): User's email
        update_data (dict): Data to update containing:
            - name (str): User's name
            - company_name (str): User's company name
            - mobile_number (str): User's mobile number
            - position (str): User's position in company
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        now = datetime.utcnow()
        result = await users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    **update_data,
                    "updatedAt": now
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating user profile: {str(e)}")
        return False

async def update_user_google_info(email: str, google_data: dict) -> bool:
    """
    Update user's Google authentication information.
    
    Args:
        email (str): User's email
        google_data (dict): Google authentication data containing:
            - google_id (str): Google user ID
            - picture (str): Profile picture URL
            - google_id_token (str): Google ID token
            - google_access_token (str): Google OAuth2 access token
            - google_refresh_token (str): Google OAuth2 refresh token
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        now = datetime.utcnow()
        result = await users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    **google_data,
                    "is_google_connected": True,
                    "updatedAt": now
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating Google info: {str(e)}")
        return False

async def get_calendar_events_by_status(user_id: str, status: str, start_date: datetime = None):
    """
    Get calendar events by status and optional start date.
    
    Args:
        user_id (str): User ID
        status (str): Event status to filter by
        start_date (datetime, optional): Start date to filter events from
        
    Returns:
        List[dict]: List of calendar events
    """
    query = {
        "user_id": user_id,
        "status": status
    }
    
    if start_date:
        # Convert start_date to ISO format string for comparison
        start_date_str = start_date.isoformat()
        query["start.dateTime"] = {"$gte": start_date_str}
    
    cursor = calendar_events_collection.find(query).sort("start.dateTime", DESCENDING)
    return await cursor.to_list(length=None)

async def get_calendar_events_by_end_time(user_id: str, current_time: datetime):
    """
    Get calendar events where end time is greater than current time.
    
    Args:
        user_id (str): User ID
        current_time (datetime): Current time to compare against
        
    Returns:
        List[dict]: List of calendar events
    """
    # Convert current_time to ISO format string for comparison
    current_time_str = current_time.isoformat()
    
    query = {
        "user_id": user_id,
        "end.dateTime": {"$lte": current_time_str}
    }
    
    cursor = calendar_events_collection.find(query).sort("end.dateTime", DESCENDING)
    return await cursor.to_list(length=None)




async def get_real_time_transcript(meetingId: str, userId: str, eventId: str) -> Optional[list]:
    try:
        doc = await chunks_col.find_one({"meetingId": meetingId})
        if not doc or "chunks" not in doc:
            return []

        # Sort the chunks by 'createdAt' ascending
        sorted_chunks = sorted(doc["chunks"], key=lambda chunk: chunk.get("createdAt"))

        return sorted_chunks

    except Exception as e:
        print(f"Error retrieving real-time transcript: {str(e)}")
        return None


async def calendar_events_tasks_collection_save(meetingId, eventId, userId, event_data_list: list):
    """Save multiple calendar event tasks to the database."""
    now = datetime.utcnow()
    documents = []

    for event_data in event_data_list:
        doc = {
            **event_data,
            "user_id": userId,
            "meetingId": meetingId,
            "eventId": eventId,
            "isCreated": False,
            "createdAt": now,
            "updatedAt": now
        }
        documents.append(doc)

    if documents:
        result = await calendar_events_tasks_collection.insert_many(documents)
        return result.inserted_ids


async def get_calendar_events_tasks(user_id: str, meetingId: str, eventId: str):
    """
    Get calendar event tasks for a specific user, meeting, and event.
    
    :param user_id: ID of the user.
    :param meetingId: ID of the meeting.
    :param eventId: ID of the calendar event.
    :return: List of tasks sorted by date.
    """
    query = {
        # "user_id": user_id,
        # "meetingId": meetingId,
        # "eventId": eventId
    }

    cursor = calendar_events_tasks_collection.find(query).sort("date", 1)
    return await cursor.to_list(length=None)


async def get_calendar_event_task_by_id(eventId: str, user_id: str):
    """Get a specific calendar event task by eventId and user_id."""
    try:
        doc = await calendar_events_tasks_collection.find_one({
            "eventId": eventId,
            "user_id": user_id
        })
        return doc
    except:
        return None
async def update_calendar_event_task(eventId: str, update_data: dict):
    """Update a calendar event task."""
    try:
        result = await calendar_events_tasks_collection.update_one(
            {"_id": ObjectId(eventId)},
            {"$set": {**update_data, "updatedAt": datetime.utcnow()}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating calendar event task: {str(e)}")
        return False
async def delete_calendar_event_task(eventId: str):
    """Delete a calendar event task."""
    try:
        result = await calendar_events_tasks_collection.delete_one({"_id": ObjectId(eventId)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting calendar event task: {str(e)}")
        return False
async def get_calendar_event_task_by_id_only(eventId: str):
    """Get a specific calendar event task by eventId."""
    try:
        doc = await calendar_events_tasks_collection.find_one({
            "_id": ObjectId(eventId)
        })
        return doc
    except:
        return None