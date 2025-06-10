from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.prediction_models_service import run_instruction

router = APIRouter()

class ChatBotRequest(BaseModel):
    message: str  # User input

class ChatBotResponse(BaseModel):
    results: dict  # Return all meeting sections

@router.post("/chat-bot", response_model=ChatBotResponse)
async def chat_bot(request: ChatBotRequest):
    try:
        # Example formatted transcript - replace with actual if needed
        message = request.message

        results = run_instruction( message)

        return ChatBotResponse(results=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
