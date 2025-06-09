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
        formatted_transcript = request.message

        description = "This is a product team sync regarding the upcoming client pitch and product development progress."
        product_details = "Product: AI-based Smart Inventory System."

        base_context = f"Meeting Description: {description}\nProduct Details: {product_details}\nTranscript:\n{formatted_transcript}"

        instructions = {
            "Meeting Details": "Extract the meeting date (if available), time, participants, organizer, and duration.",
            "Agenda": "List the agenda items discussed or implied during the meeting.",
            "Key Discussion Points": "List the key discussion points from the meeting.",
            "Action Items / To-Dos": "List all action items with responsible persons and due dates (if mentioned).",
            "Decisions & Agreements": "List important decisions and agreements made during the meeting.",
            "Follow-up Items": "List follow-up questions or tasks that need to be addressed in the next meeting.",
            "Meeting Summary": "Summarize the entire meeting in 2-3 sentences.",
            "Sentiment / Feedback": "Analyze the tone and sentiment of each speaker and the overall meeting."
        }

        results = {}
        for section, instruction in instructions.items():
            results[section] = run_instruction(instruction, base_context)

        return ChatBotResponse(results=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
