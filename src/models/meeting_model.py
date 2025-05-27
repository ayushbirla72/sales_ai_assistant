from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

class MeetingCreate(BaseModel):
   
    title: str
    description: Optional[str] = None
    topics: List[str]
    participants: int
    product_details: Optional[str] = None
    scheduled_time: Optional[str] = None

class MeetingResponse(MeetingCreate):
    id: str

class GetMeetingsById():
     userId:str
    

# Helper to convert MongoDB document to response
def meeting_doc_to_response(doc):
    return MeetingResponse(
        id=str(doc["_id"]),
        userId=doc["userId"],
        title=doc["title"],
        description=doc.get("description"),
        topics=doc.get("topics", []),
        persons=doc.get("persons", []),
        product_details=doc.get("product_details"),
        scheduled_time=doc.get("scheduled_time")
    )

class MeetingChatMessage(BaseModel):
    meeting_id: str
    message: str
    sender: str
    timestamp: datetime
    user_id: str

class AudioChunk(BaseModel):
    meeting_id: str
    chunk_data: str  # base64 encoded audio data
    timestamp: datetime
    chunk_index: int
    user_id: str

class MeetingSession(BaseModel):
    meeting_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str  # "active" or "ended"
    last_chat_sync: Optional[datetime] = None
    last_audio_sync: Optional[datetime] = None
