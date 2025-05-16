from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from typing import List
from bson import ObjectId
from src.services.mongo_service import save_suggestion, get_suggestions_by_user_and_session

router = APIRouter()

@router.post("/suggestions")
async def create_suggestion(
    sessionId: str = Body(...),
    userId: str = Body(...),
    transcript: str = Body(...),
    suggestion: str = Body(...)
):
    inserted_id = await save_suggestion(sessionId, userId, transcript, suggestion)
    return {"message": "Suggestion saved", "id": str(inserted_id)}


@router.get("/suggestions", response_model=List[dict])
async def get_suggestions( sessionId: str = Form(...),
    userId: str = Form(...)):
    suggestions = await get_suggestions_by_user_and_session(userId, sessionId)
    return suggestions
