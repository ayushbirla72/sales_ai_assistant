from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

class MeetingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    topics: List[str]
    persons: List[str]
    product_details: Optional[str] = None

class MeetingResponse(MeetingCreate):
    id: str

# Helper to convert MongoDB document to response
def meeting_doc_to_response(doc):
    return MeetingResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc.get("description"),
        topics=doc.get("topics", []),
        persons=doc.get("persons", []),
        product_details=doc.get("product_details")
    )
