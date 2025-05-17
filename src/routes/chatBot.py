from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.prediction_models_service import run_instruction

router = APIRouter()

class ChatBotRequest(BaseModel):
    message: str

class ChatBotResponse(BaseModel):
    reply: str

@router.post("/chat-bot", response_model=ChatBotResponse)
async def chat_bot(request: ChatBotRequest):
    try:
        instruction = "You are a helpful and friendly assistant. Respond naturally to the user's message."

        reply = run_instruction(instruction, request.message)

        return ChatBotResponse(reply=reply)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
