from fastapi import FastAPI
# from src.routes.audio import router as audio_router
from src.routes.auth import router as auth_router
from src.routes.suggestion import router as suggestion_router
# from src.routes.chatBot import router as chatbot
from src.routes.calendar import router as calendar_router
from src.routes.google_meet import router as google_meet_router

app = FastAPI(title="Audio Uploader with Transcription & Diarization")

# app.include_router(audio_router, prefix="/api/user")
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(suggestion_router, prefix="/api/sg")
# app.include_router(chatbot, prefix="/api/chat")
app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(google_meet_router, prefix="/api/meet", tags=["Google Meet"])
