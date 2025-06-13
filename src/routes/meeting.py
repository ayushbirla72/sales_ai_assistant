from typing import List, Optional
from src.common.extract_calendly_events import extract_calendly_events
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Depends,  Request
import uuid, tempfile, os
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel

from src.services.prediction_models_service import run_instruction
from src.services.speaker_identification import load_reference_embedding, process_segments, run_diarization
from src.services.s3_service import upload_file_to_s3, download_file_from_s3
from src.services.mongo_service import (
    calendar_events_tasks_collection_save, get_calendar_event_by_id_only, get_salesperson_sample, save_chunk_metadata, get_chunk_list, save_final_audio, 
    save_suggestion, update_final_summary_and_suggestion, get_calendar_event_by_id,
    update_calendar_event, save_calendar_event
)
from src.services.audio_merge_service import merge_audio_chunks
from src.services.whisper_service import transcribe_audio
from src.services.diarization_service import diarize_audio
from src.services.mongo_service import save_salesperson_sample

from src.services.transcription_service import transcribe_audio_bytes
from src.services.mongo_service import save_transcription_chunk
from src.utils import extract_filename_from_s3_url


from src.models.meeting_model import GetMeetingsById, MeetingCreate, MeetingResponse, meeting_doc_to_response
from src.services.mongo_service import create_meeting, get_all_meetings, get_meeting_by_id
from src.routes.auth import verify_token

router = APIRouter()

class MeetingStatus(str, Enum):
    SCHEDULED = "scheduled"
    START = "start"
    PROGRESS = "progress"
    TRANSCRIPTION = "transcription"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"

class MeetingStatusUpdate(BaseModel):
    status: MeetingStatus
    meeting_id: str
    event_id: str
    user_id: str
    container_id: str
    message: Optional[str] = None
    timestamp: Optional[str] = None

@router.post("/upload-salesperson-audio")
async def upload_salesperson_audio(
    file: UploadFile = File(...),
    # userId:str = Form(...),
    token_data: dict = Depends(verify_token)
):
    userId = token_data["user_id"]
    print(f"dattttttttttttttt............ {userId}")
    if not userId or not file.filename:
        raise HTTPException(400, detail="Missing userId or file")

    content = await file.read()
    s3_key = f"salesperson_samples_audio/{userId}_{file.filename}"
    s3_url = upload_file_to_s3(s3_key, content)

    doc_id = await save_salesperson_sample(
        filename=file.filename,
        s3_url=s3_url,
        userId=userId
    )

    return {
        "message": "Audio sample uploaded",
        "id": str(doc_id),
        "s3_url": s3_url
    }


@router.post("/audio-chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    meetingId: str = Form(...),
    eventId: str = Form(...),
    token_data: dict = Depends(verify_token)
):
    userId = token_data["user_id"]
    # eventId = '665d63636363636363636363'
    container_id = '1234'
    if not meetingId or not file.filename:
        raise HTTPException(status_code=400, detail="Missing meetingId or file")

    # Upload chunk to S3
    chunk_name = f"audio_recording/{meetingId}_{uuid.uuid4()}_{file.filename}"
    content = await file.read()
    # s3_url = upload_file_to_s3(chunk_name, content)
    s3_url = "https://s3.amazonaws.com/"

    # Transcribe the uploaded audio chunk
    # transcript = transcribe_audio_bytes(content)
    transcript = "test"

    # Save the chunk metadata
    await save_chunk_metadata(meetingId, chunk_name, userId, transcript, s3_url, eventId, container_id)

    # ✅ Fire-and-forget the heavy suggestion task
    asyncio.create_task(handle_post_processing(meetingId, userId))

    # ✅ Send response immediately
    return {
        "message": "Chunk uploaded",
        "chunk": chunk_name,
        "s3_url": s3_url,
        "transcript": transcript,
    }

@router.post("/upload-chunk-google-meet")
async def upload_chunk_google_meet(
    audio: UploadFile = File(...),
    metadata: str = Form(...),
):
    try:
        metadata_dict = json.loads(metadata)
        
        # Extract metadata
        meeting_id = metadata_dict.get("meeting_id")
        container_id = metadata_dict.get("container_id")
        chunk_filename = metadata_dict.get("chunk_filename")
        userId = metadata_dict.get("user_id")
        eventId = metadata_dict.get("event_id")

        print(f"meeting_id {meeting_id}")
        print(f"container_id {container_id}")
        print(f"chunk_filename {chunk_filename}")
        print(f"userId {userId}")
        print(f"eventId {eventId}") 
        if not meeting_id or not container_id or not chunk_filename:
            raise HTTPException(status_code=400, detail="Missing required metadata fields")

        # Upload chunk to S3
        chunk_name = f"audio_recording/{meeting_id}/{container_id}/{chunk_filename}"
        content = await audio.read()
        # s3_url = upload_file_to_s3(chunk_name, content)
        s3_url = "https://s3.amazonaws.com/"
        print(f"s3_url {s3_url}")
        # Transcribe the uploaded audio chunk
        # transcript = transcribe_audio_bytes(content)
        transcript = "test"

        print(f"transcript {transcript}")
        # Save the chunk metadata
        await save_chunk_metadata(meeting_id, chunk_name, userId, transcript, s3_url, eventId, container_id)
        print(f"chunk metadata saved")              
        # Fire-and-forget the heavy suggestion task
        asyncio.create_task(handle_post_processing(meeting_id, userId))
        print(f"chunk uploaded successfully {chunk_name}")
        print(f"s3_url {s3_url}")
        print(f"transcript {transcript}")
        return {
            "message": "Chunk uploaded successfully",
            "chunk": chunk_name,
            "s3_url": s3_url,
            "transcript": transcript,
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chunk: {str(e)}")


# 🔁 This runs in background
async def handle_post_processing(meetingId: str, userId: str):
    try:
        # Get all previous transcripts
        chunk_list = await get_chunk_list(meetingId)
        full_transcript = "\n".join(chunk["transcript"] for chunk in chunk_list if "transcript" in chunk)

        # Get meeting info
        meeting = await get_meeting_by_id(meetingId)
        description = meeting.get("description", "")
        product_details = meeting.get("product_details", "")

        # Prompt to detect questions and respond if directed to sales person
        instruction = (
            f"The following is a transcript of a meeting about {product_details}.\n"
            f"Meeting Description: {description}\n"
            f"Transcript:\n{full_transcript}\n\n"
            f"Step 1: Identify any questions asked during the meeting that are directed to a sales person.\n"
            f"Step 2: For each such question, provide a concise and professional answer from the perspective of a knowledgeable sales person.\n"
            f"Format the response as a list of Q&A pairs like:\n"
            f"Q: [the question]\nA: [the sales person's answer]\n"
        )

        # Run LLM model to get answers
        response = await run_instruction(instruction, full_transcript)  # assuming this is an async call
        print(f"Sales Q&A response: {response}")
        
        suggestions = "test"
        print(f"suggestion result is ............. {suggestions}")
        # Save suggestions
        await save_suggestion(meetingId, userId, transcript=full_transcript, suggestion=suggestions)

    except Exception as e:
        # Optionally log the error
        print(f"Error in background processing: {e}")



@router.post("/upload-audio-chunk")
async def upload_audio_chunk(
    file: UploadFile = File(...),
    meetingId: str = Form(...),
   
    token_data: dict = Depends(verify_token)
):
    userId = token_data["user_id"]
    print("hello")
    print(f"file {file}")
    if not file or not meetingId or not userId:
        raise HTTPException(400, detail="Missing file or meetingId or userId")

    # Read file content
    print(f"file {file}")
    audio_bytes = await file.read()

    # Generate unique filename
    unique_name = f"audio_recording/{meetingId}_{uuid.uuid4()}.wav"

    # Upload chunk to S3
    s3_url = upload_file_to_s3(unique_name, audio_bytes)

    # Transcribe the chunk
    transcript = transcribe_audio_bytes(audio_bytes)

    # Optional: Store transcription metadata in MongoDB
    doc_id = await save_transcription_chunk(meetingId, s3_url, transcript,userId)

    return {
        "meetingId": meetingId,
        "transcript": transcript,
        "chunkUrl": s3_url,
        "id": str(doc_id)
    }

@router.post("/finalize-offline-session")
async def finalize_offline_session(
    file: UploadFile = File(...),
    meetingId: str = Form(...),
    eventId: str = Form(...),
    token_data: dict = Depends(verify_token)
):
    userId = token_data["user_id"]
    if not meetingId or not eventId:
        raise HTTPException(status_code=400, detail="Missing meetingId or eventId")

    temp_dir = tempfile.mkdtemp()
    local_files = []
    final_path = None
    sample_path = None

    try:
        # Read and save the final audio file
        audio_bytes = await file.read()

        BASE_DIR = os.path.dirname(__file__)
        local_audio_dir = os.path.join(BASE_DIR, "../../recordings", meetingId)
        os.makedirs(local_audio_dir, exist_ok=True)  # Ensure directory exists
    
        final_path = os.path.join(local_audio_dir, f"{eventId}_final.wav")
        with open(final_path, "wb") as f:
            f.write(audio_bytes)

        # Upload final audio to S3
        s3_key = f"final_recording/{meetingId}/{eventId}/final.wav"
        # s3_url = upload_file_to_s3(s3_key, audio_bytes)
        s3_url = "https://s3.amazonaws.com/"

        # Fetch salesperson sample from DB
        # sample_url = await get_salesperson_sample(userId)
        # s3_sample_key = extract_filename_from_s3_url(sample_url["s3_url"])

        # # Download and save salesperson sample locally
        # sample_path = os.path.join(temp_dir, os.path.basename(s3_sample_key))
        # sample_file_data = download_file_from_s3(s3_sample_key)
        # with open(sample_path, "wb") as sf:
        #     sf.write(sample_file_data)
        # sample_path = "../host2.wav"
        BASE_DIR = os.path.dirname(__file__)
        sample_path = os.path.join(BASE_DIR, "../host2.wav")

        # Load reference embedding from local sample file
        ref_embedding = load_reference_embedding(sample_path)

        # Run diarization and process
        diarization = run_diarization(final_path)
        results = process_segments(diarization, final_path, ref_embedding)

        # Save the final audio metadata
        doc_id = await save_final_audio(meetingId, s3_url, results, userId)

        # Update calendar event status
        calendar_event = await get_calendar_event_by_id_only(eventId)
        if calendar_event:
            await update_calendar_event(calendar_event["_id"], {
                "meetingId": meetingId,
                "status": "transcription",
                "end.dateTime": datetime.utcnow().isoformat() + 'Z',
                "message": "Meeting recording completed",
            })

        # Run post-processing in background
        asyncio.create_task(handle_finalize_post_processing(meetingId, userId, results, eventId))

        return {
            "id": str(doc_id),
            "transcript": "",
            "results": results,
            "s3_url": s3_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing final session: {str(e)}")
    finally:
        # Clean up temporary files
        for file in local_files:
            if os.path.exists(file):
                os.remove(file)
        if final_path and os.path.exists(final_path):
            os.remove(final_path)
        if sample_path and os.path.exists(sample_path):
            os.remove(sample_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


async def handle_finalize_post_processing(meetingId: str, userId: str, transcript: str, eventId: str):
    try:
        # Get meeting metadata
        meeting = await get_meeting_by_id(meetingId)
        description = meeting.get("description", "")
        product_details = meeting.get("product_details", "")

        # --- Step 1: Parse Transcript ---
        try:
            transcript_data = transcript if isinstance(transcript, list) else json.loads(transcript)
        except Exception as parse_err:
            raise ValueError(f"Failed to parse transcript: {parse_err}")

        # --- Step 2: Group transcript by original speaker labels in order ---
        formatted_transcript = ""
        for entry in transcript_data:
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "").strip()
            if text:
                formatted_transcript += f"{speaker}: {text}\n"

        # --- Step 3: Prepare LLM Instructions ---
        summary_instruction = (
            f"Summarize the following meeting in a concise paragraph.\n"
            # f"Meeting Description: {description}\n"
            # f"Product Details: {product_details}"
        )

        base_context = f"Meeting Description: {description}\nProduct Details: {product_details}\nTranscript:\n{formatted_transcript}"

        suggestion_instruction = (
            f"Suggest improvements based on the following meeting.\n"
            # f"Meeting Description: {description}\n"
            # f"Product Details: {product_details}"
        )

        # --- Step 4: Call LLM ---
        summary = run_instruction(summary_instruction, f"Transcript:\n{formatted_transcript}")
        # suggestion = run_instruction(suggestion_instruction, f"Transcript:\n{formatted_transcript}")
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

          if section == "Action Items / To-Dos":
           # Simulate extracted markdown table text (you can replace this with actual content from base_context)
           table_text = run_instruction(instruction, base_context)
           action_items = extract_calendly_events(table_text)
           await calendar_events_tasks_collection_save(meetingId, eventId, userId, action_items)
           results[section] = table_text
          else:
            results[section] = run_instruction(instruction, base_context)


        # print(f"📄 Summary:\n{summary}\n\n💡 Suggestions:\n{suggestion}")

        # --- Step 5: Save to DB ---
        await update_final_summary_and_suggestion(meetingId, userId, summary, results)

        await update_calendar_event(eventId, {
            "status": "completed",
        })

    except Exception as e:
        print(f"❌ Error in finalize post-processing: {e}")


@router.post("/meetings", response_model=MeetingResponse)
async def create_meeting_api(
    meeting: MeetingCreate,
    token_data: dict = Depends(verify_token)
):
    userId = token_data["user_id"]
    meeting_data = meeting.dict()
    meeting_data["userId"] = userId
    
    # If eventId is not provided, create a new calendar event
    if not meeting_data.get("eventId"):
        from src.services.mongo_service import save_calendar_event
        from datetime import datetime, timedelta
        
        # Create a new calendar event
        event_data = {
            "created": datetime.utcnow().isoformat() + 'Z',
            "creator": {
                "email": token_data["email"],
                "self": True
            },
            "end": {
                "dateTime": (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z',
                "timeZone": "UTC"
            },
            "eventType": "default",
            "kind": "calendar#event",
            "organizer": {
                "email": token_data["email"],
                "self": True
            },
            "attendees": [
                {
                    "email": token_data["email"],
                    "self": True
                }
            ],
            "reminders": {
                "useDefault": True
            },
            "start": {
                "dateTime": datetime.utcnow().isoformat() + 'Z',
                "timeZone": "UTC"
            },
            "status": "confirmed",
            "summary": meeting_data["title"],
            "updated": datetime.utcnow().isoformat() + 'Z',
            "user_id": userId,
            "isMeetingDetailsUploaded": True,
            "autoJoin": True,
            "mode": "Offline"
        }
        
        # Save the new calendar event
        event_id = await save_calendar_event(event_data)
        meeting_data["eventId"] = str(event_id)
    
    # Create the meeting
    meeting_id = await create_meeting(meeting_data)
    
    # Update the calendar event with meeting details
    if meeting_data.get("eventId"):
        from src.services.mongo_service import update_meeting_details_uploaded
        await update_meeting_details_uploaded(meeting_data["eventId"], str(meeting_id))
    
    return MeetingResponse(id=str(meeting_id), **meeting_data)

@router.get("/meetings", response_model=List[MeetingResponse])
async def get_all_meetings_api(
    userId:str,
    token_data: dict = Depends(verify_token)
):
    docs = await get_all_meetings(userId)
    return [meeting_doc_to_response(doc) for doc in docs]

@router.get("/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_by_id_api(
    meeting_id: str,
    token_data: dict = Depends(verify_token)
):
    doc = await get_meeting_by_id(meeting_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting_doc_to_response(doc)

@router.put("/meetings/auto-join/{eventId}")
async def update_auto_join(
    eventId: str,
    auto_join: bool = Body(..., embed=True),
    token_data: dict = Depends(verify_token)
):
    """
    Update the auto-join status for a calendar event.
    
    Args:
        eventId (str): The ID of the calendar event
        auto_join (bool): Whether to auto-join the meeting
        token_data (dict): Token data containing user information
    
    Returns:
        dict: Updated calendar event
    """
    try:
        # Get the calendar event
        event = await get_calendar_event_by_id(eventId, token_data["user_id"])
        if not event:
            raise HTTPException(status_code=404, detail="Calendar event not found")
        
        # Update the auto-join status
        updated = await update_calendar_event(
            event["_id"],
            {
                "autoJoin": auto_join,
                "updated": datetime.utcnow().isoformat() + 'Z'
            }
        )
        
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update auto-join status")
        
        # Get the updated event
        updated_event = await get_calendar_event_by_id(eventId, token_data["user_id"])
        return updated_event
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/some-endpoint")
async def some_endpoint(token_data: dict = Depends(verify_token)):
    email = token_data["email"]
    user_id = token_data["user_id"]
    # ... rest of your code

@router.post("/finalize-online-session")
async def finalize_online_session(
    file: UploadFile = File(...),
    meetingId: str = Form(...),
    eventId: str = Form(...),
    containerId: str = Form(...),
    userId: str = Form(...),
):
    """
    Finalize a meeting session with an audio file.
    All processing is done in the background.
    
    Args:
        file (UploadFile): The audio file to process
        meetingId (str): ID of the meeting
        eventId (str): ID of the event
        containerId (str): ID of the container
        userId (str): ID of the user
        
    Returns:
        dict: Success message
    """
    if not all([file, meetingId, eventId, containerId, userId]):
        raise HTTPException(status_code=400, detail="Missing required parameters")

    # Start background processing
    asyncio.create_task(process_finalize_session(
        file=file,
        meetingId=meetingId,
        eventId=eventId,
        containerId=containerId,
        userId=userId
    ))
    
    return {
        "message": "Session finalization started successfully",
        "meetingId": meetingId
    }

async def process_finalize_session(
    file: UploadFile,
    meetingId: str,
    eventId: str,
    containerId: str,
    userId: str
):
    """
    Background process for finalizing session.
    """
    temp_dir = tempfile.mkdtemp()
    final_path = None
    sample_path = None
    
    try:
        # Read the audio file
        audio_bytes = await file.read()
        
        # Save the audio file to temp directory
        final_path = os.path.join(temp_dir, f"{meetingId}_{file.filename}")
        with open(final_path, "wb") as f:
            f.write(audio_bytes)
        
        # Upload the audio file to S3
        s3_key = f"final_recording/{meetingId}/{containerId}/{file.filename}"
        s3_url = upload_file_to_s3(s3_key, audio_bytes)

        # Fetch salesperson sample from DB
        sample_url = await get_salesperson_sample(userId)
        s3_sample_key = extract_filename_from_s3_url(sample_url["s3_url"]) 
        
        # Download and save salesperson sample locally
        sample_path = os.path.join(temp_dir, os.path.basename(s3_sample_key))

        sample_file_data = download_file_from_s3(s3_sample_key)
        with open(sample_path, "wb") as sf:
            sf.write(sample_file_data)

        # Load reference embedding from local sample file
        ref_embedding = load_reference_embedding(sample_path)

        # Run diarization and process
        diarization = run_diarization(final_path)
        results = process_segments(diarization, final_path, ref_embedding)

        # Save the final audio metadata
        await save_final_audio(meetingId, s3_url, results, userId)
        
        # Run post-processing in background
        asyncio.create_task(handle_finalize_post_processing(meetingId, userId, results, eventId))
        
        # Update calendar event if needed
        calendar_event = await get_calendar_event_by_id_only(eventId)
        if calendar_event:
            await update_calendar_event(calendar_event["_id"], {
                "meetingId": meetingId,
                "status": "completed",
            })
            
    except Exception as e:
        print(f"Error in background processing: {str(e)}")
    finally:
        # Clean up temporary files
        if final_path and os.path.exists(final_path):
            os.remove(final_path)
        if sample_path and os.path.exists(sample_path):
            os.remove(sample_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@router.post("/update-meeting-status")
async def update_meeting_status(
    data: MeetingStatusUpdate
):
    """
    Update the status of a meeting.
    
    Args:
        data (MeetingStatusUpdate): Meeting status update data containing:
            - status (MeetingStatus): New status of the meeting
            - meeting_id (str): ID of the meeting
            - event_id (str): ID of the calendar event
            - user_id (str): ID of the user
            - container_id (str): ID of the container
            - message (str, optional): Additional message
            - timestamp (str, optional): Timestamp of the update
            
    Returns:
        dict: Success message
    """
    try:
        # Get the calendar event
        calendar_event = await get_calendar_event_by_id_only(data.event_id)
        if not calendar_event:
            raise HTTPException(status_code=404, detail="Calendar event not found")

        # Update the calendar event with new status
        update_data = {
            "status": data.status,
        }
        
        if data.message:
            update_data["message"] = data.message

        await update_calendar_event(calendar_event["_id"], update_data)

        return {
            "message": "Meeting status updated successfully",
            "event_id": data.event_id,
            "meeting_id": data.meeting_id,
            "status": data.status,
            "container_id": data.container_id
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating meeting status: {str(e)}"
        )
    












@router.post("/test")
async def test_endpoint(
    request: Request,
    token_data: dict = Depends(verify_token),
):
    body: Dict = await request.json()
    
    meetingId = body.get("meetingId")
    eventId = body.get("eventId")
    table_text = body.get("table_text", "")
    userId = token_data.get("user_id")

    if not meetingId or not eventId:
        raise HTTPException(status_code=400, detail="Missing meetingId or eventId")

    action_items = extract_calendly_events(table_text)

    await calendar_events_tasks_collection_save(meetingId, eventId, userId, action_items)

    return {
        "message": "Action items extracted and saved successfully",
        "action_items": action_items
    }

