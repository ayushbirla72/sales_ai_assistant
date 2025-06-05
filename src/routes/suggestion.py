from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Query, Depends
from typing import List
from bson import ObjectId
from src.services.mongo_service import get_final_audio, get_summary_and_suggestion, save_suggestion, get_suggestions_by_user_and_session
from src.routes.auth import verify_token

router = APIRouter()

@router.post("/suggestions")
async def create_suggestion(
    meetingId: str = Body(...),
    userId: str = Body(...),
    transcript: str = Body(...),
    suggestion: str = Body(...),
    token_data: dict = Depends(verify_token)
):
    inserted_id = await save_suggestion(meetingId, userId, transcript, suggestion)
    return {"message": "Suggestion saved", "id": str(inserted_id)}


@router.get("/suggestions", response_model=List[dict])
async def get_suggestions(
    meetingId: str = Body(...),
    userId: str = Body(...),
    token_data: dict = Depends(verify_token)
):
    suggestions = await get_suggestions_by_user_and_session(userId, meetingId)
    return suggestions


@router.get("/meeting-summary/{meetingId}", response_model=dict)
async def get_meeting_summary(
    meetingId: str,
    token_data: dict = Depends(verify_token)
):
    userId = token_data["user_id"]
    document = await get_summary_and_suggestion(meetingId, userId)
    if not document:
        raise HTTPException(status_code=404, detail="Summary not found")

    result = await get_final_audio(meetingId)
    return {
        "meetingId": document["meetingId"],
        "userId": document["userId"],
        "summary": document["summary"],
        "suggestion": document["suggestion"],
        "createdAt": document["createdAt"],
        "updatedAt": document["updatedAt"],
        "transcript": result["results"]
    }