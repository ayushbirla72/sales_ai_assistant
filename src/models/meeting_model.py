from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

class MeetingCreate(BaseModel):
   
    title: str
    description: Optional[str] = None
    topics: List[str]
    participants: int
    product_details: Optional[str] = None
    scheduled_time: Optional[str] = None
    eventId: Optional[str] = None
    meetingJoinId: Optional[str] = None

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
        scheduled_time=doc.get("scheduled_time"),
        eventId=doc.get("eventId"),
        meetingJoinId=doc.get("meetingJoinId")
    )
