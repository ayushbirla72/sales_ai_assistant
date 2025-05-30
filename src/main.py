from fastapi import FastAPI
from src.routes.meeting import router as meeting_router
from src.routes.auth import router as auth_router
from src.routes.suggestion import router as suggestion_router
# from src.routes.chatBot import router as chatbot
from src.routes.calendar import router as calendar_router

app = FastAPI(title="Audio Uploader with Transcription & Diarization")

app.include_router(meeting_router, prefix="/api/meeting")
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(suggestion_router, prefix="/api/sg")
# app.include_router(chatbot, prefix="/api/chat")
app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])
