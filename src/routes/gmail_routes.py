from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict
from pydantic import BaseModel
from src.routes.auth import verify_token

router = APIRouter()

# Define the request model for incoming Gmail data
class GmailEmail(BaseModel):
    id: str
    threadId: str
    subject: str
    from_: str  # `from` is a reserved keyword, so we use `from_`
    to: str
    snippet: str
    date: str

class GmailListRequest(BaseModel):
    emails: List[GmailEmail]

@router.post("/list")
async def gmail_list(
    request: Request,
    token_data: dict = Depends(verify_token)
):
    payload = await request.json()
    print(f"User ID: {token_data['user_id']}")
    print("Received Gmail data:")
    for email in payload.get("emails", []):
        print(email)

    return {"message": f"Received emails successfully"}
