import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from datetime import datetime
import base64
import wave
import io
import asyncio
from typing import AsyncGenerator, Optional
import numpy as np

class GoogleMeetService:
    def __init__(self, access_token: str):
        self.credentials = Credentials(
            token=access_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=[
                "https://www.googleapis.com/auth/meetings",
                "https://www.googleapis.com/auth/meetings.audio",
                "https://www.googleapis.com/auth/meetings.chat"
            ]
        )
        self.meet_service = build("meet", "v2", credentials=self.credentials)
        self.active_sessions = {}

    async def join_meeting(self, meeting_id: str, display_name: str) -> str:
        """Join a Google Meet meeting and return the join URL."""
        try:
            # Create a participant
            participant = {
                "displayName": display_name,
                "joinAs": "PARTICIPANT"
            }
            
            # Join the meeting
            response = self.meet_service.spaces().participants().create(
                parent=f"spaces/{meeting_id}",
                body=participant
            ).execute()
            
            # Get the join URL
            join_url = response.get("joinUrl")
            if not join_url:
                raise Exception("Failed to get join URL")
            
            return join_url
        except HttpError as error:
            raise Exception(f"Failed to join meeting: {error}")

    async def start_meeting_monitoring(self, meeting_id: str, user_id: str) -> None:
        """Start monitoring a meeting for audio and chat."""
        if meeting_id in self.active_sessions:
            return

        self.active_sessions[meeting_id] = {
            "user_id": user_id,
            "last_chat_sync": None,
            "last_audio_sync": None,
            "is_monitoring": True
        }

        # Start monitoring tasks
        asyncio.create_task(self._monitor_chat(meeting_id))
        asyncio.create_task(self._monitor_audio(meeting_id))

    async def stop_meeting_monitoring(self, meeting_id: str) -> None:
        """Stop monitoring a meeting."""
        if meeting_id in self.active_sessions:
            self.active_sessions[meeting_id]["is_monitoring"] = False
            del self.active_sessions[meeting_id]

    async def _monitor_chat(self, meeting_id: str) -> None:
        """Continuously monitor chat messages."""
        while meeting_id in self.active_sessions and self.active_sessions[meeting_id]["is_monitoring"]:
            try:
                last_sync = self.active_sessions[meeting_id]["last_chat_sync"]
                messages = await self.get_meeting_chat(meeting_id)
                
                # Process new messages
                for message in messages:
                    if not last_sync or message["timestamp"] > last_sync:
                        # Store message in database
                        from src.services.mongo_service import save_meeting_chat
                        await save_meeting_chat({
                            "meeting_id": meeting_id,
                            "message": message["message"],
                            "sender": message["sender"],
                            "timestamp": message["timestamp"],
                            "user_id": self.active_sessions[meeting_id]["user_id"]
                        })
                
                if messages:
                    self.active_sessions[meeting_id]["last_chat_sync"] = messages[-1]["timestamp"]
                
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"Error monitoring chat: {str(e)}")
                await asyncio.sleep(5)

    async def _monitor_audio(self, meeting_id: str) -> None:
        """Continuously monitor audio stream."""
        chunk_index = 0
        while meeting_id in self.active_sessions and self.active_sessions[meeting_id]["is_monitoring"]:
            try:
                audio_data = await self.get_meeting_audio(meeting_id)
                if audio_data:
                    # Store audio chunk in database
                    from src.services.mongo_service import save_audio_chunk
                    await save_audio_chunk({
                        "meeting_id": meeting_id,
                        "chunk_data": audio_data["audio_data"],
                        "timestamp": datetime.utcnow(),
                        "chunk_index": chunk_index,
                        "user_id": self.active_sessions[meeting_id]["user_id"]
                    })
                    chunk_index += 1
                
                await asyncio.sleep(1)  # Get audio every second
            except Exception as e:
                print(f"Error monitoring audio: {str(e)}")
                await asyncio.sleep(1)

    async def get_meeting_audio(self, meeting_id: str) -> Optional[dict]:
        """Get the audio stream from a Google Meet meeting."""
        try:
            # Get the meeting's audio stream
            response = self.meet_service.spaces().get(
                name=f"spaces/{meeting_id}"
            ).execute()
            
            # Get the audio stream URL
            audio_stream = response.get("audioStream")
            if not audio_stream:
                return None
            
            # Convert audio stream to base64 for transmission
            audio_data = base64.b64encode(audio_stream).decode('utf-8')
            
            return {
                "audio_data": audio_data,
                "format": "wav",
                "sample_rate": 16000,
                "channels": 1
            }
        except HttpError as error:
            raise Exception(f"Failed to get meeting audio: {error}")

    async def get_meeting_chat(self, meeting_id: str) -> list:
        """Get the chat messages from a Google Meet meeting."""
        try:
            # Get the meeting's chat messages
            response = self.meet_service.spaces().messages().list(
                parent=f"spaces/{meeting_id}"
            ).execute()
            
            messages = response.get("messages", [])
            formatted_messages = []
            
            for message in messages:
                formatted_messages.append({
                    "message": message.get("text"),
                    "timestamp": message.get("createTime"),
                    "sender": message.get("sender", {}).get("displayName", "Unknown")
                })
            
            return formatted_messages
        except HttpError as error:
            raise Exception(f"Failed to get meeting chat: {error}")

    async def send_chat_message(self, meeting_id: str, message: str, sender: str) -> None:
        """Send a chat message in a Google Meet meeting."""
        try:
            # Create the message
            message_body = {
                "text": message,
                "sender": {
                    "displayName": sender
                }
            }
            
            # Send the message
            self.meet_service.spaces().messages().create(
                parent=f"spaces/{meeting_id}",
                body=message_body
            ).execute()
        except HttpError as error:
            raise Exception(f"Failed to send chat message: {error}")

    def _convert_audio_to_wav(self, audio_data: bytes) -> bytes:
        """Convert raw audio data to WAV format."""
        # Create a WAV file in memory
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_data)
            return wav_buffer.getvalue() 