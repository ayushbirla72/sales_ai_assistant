from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
import uuid, tempfile, os
import asyncio

from src.services.prediction_models_service import run_instruction
from src.services.speaker_identification import load_reference_embedding, process_segments, run_diarization
from src.services.s3_service import upload_file_to_s3, download_file_from_s3
from src.services.mongo_service import get_salesperson_sample, save_chunk_metadata, get_chunk_list, save_final_audio, save_suggestion
from src.services.audio_merge_service import merge_audio_chunks
from src.services.whisper_service import transcribe_audio
from src.services.diarization_service import diarize_audio
from src.services.mongo_service import save_salesperson_sample

from src.services.transcription_service import transcribe_audio_bytes
from src.services.mongo_service import save_transcription_chunk
from src.utils import extract_filename_from_s3_url


from src.models.meeting_model import GetMeetingsById, MeetingCreate, MeetingResponse, meeting_doc_to_response
from src.services.mongo_service import create_meeting, get_all_meetings, get_meeting_by_id

router = APIRouter()



@router.post("/upload-salesperson-audio")
async def upload_salesperson_audio(
    file: UploadFile = File(...),
    userId:str = Form(...)
):
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


@router.post("/upload-chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    sessionId: str = Form(...),
    userId: str = Form(...)
):
    if not sessionId or not file.filename:
        raise HTTPException(status_code=400, detail="Missing sessionId or file")

    # Upload chunk to S3
    chunk_name = f"audio_recording/{sessionId}_{uuid.uuid4()}_{file.filename}"
    content = await file.read()
    s3_url = upload_file_to_s3(chunk_name, content)

    # Transcribe the uploaded audio chunk
    transcript = transcribe_audio_bytes(content)

    # Save the chunk metadata
    await save_chunk_metadata(sessionId, chunk_name, userId, transcript, s3_url)

    # ✅ Fire-and-forget the heavy suggestion task
    asyncio.create_task(handle_post_processing(sessionId, userId))

    # ✅ Send response immediately
    return {
        "message": "Chunk uploaded",
        "chunk": chunk_name,
        "s3_url": s3_url,
        "transcript": transcript,
    }


# 🔁 This runs in background
async def handle_post_processing(sessionId: str, userId: str):
    try:
        # Get all previous transcripts
        chunk_list = await get_chunk_list(sessionId)
        full_transcript = "\n".join(chunk["transcript"] for chunk in chunk_list if "transcript" in chunk)

        # Get meeting info
        meeting = await get_meeting_by_id(sessionId)
        description = meeting.get("description", "")
        product_details = meeting.get("product_details", "")

        # Run LLM
        instruction = f"Suggest improvements for this meeting segment. Meeting Description: {description}. Product Details: {product_details}."
        suggestions = run_instruction(instruction, f"Transcript:\n{full_transcript}")

        # Save suggestions
        await save_suggestion(sessionId, userId, transcript=full_transcript, suggestion=suggestions)

    except Exception as e:
        # Optionally log the error
        print(f"Error in background processing: {e}")



@router.post("/upload-audio-chunk")
async def upload_audio_chunk(
    file: UploadFile = File(...),
    sessionId: str = Form(...),
    userId:str = Form(...)
):
    print("hello")
    print(f"file {file}")
    if not file or not sessionId or not userId:
        raise HTTPException(400, detail="Missing file or sessionId or userId")

    # Read file content
    print(f"file {file}")
    audio_bytes = await file.read()

    # Generate unique filename
    unique_name = f"audio_recording/{sessionId}_{uuid.uuid4()}.wav"

    # Upload chunk to S3
    s3_url = upload_file_to_s3(unique_name, audio_bytes)

    # Transcribe the chunk
    transcript = transcribe_audio_bytes(audio_bytes)

    # Optional: Store transcription metadata in MongoDB
    doc_id = await save_transcription_chunk(sessionId, s3_url, transcript,userId)

    return {
        "sessionId": sessionId,
        "transcript": transcript,
        "chunkUrl": s3_url,
        "id": str(doc_id)
    }

@router.post("/finalize-session")
async def finalize_session(sessionId: str = Form(...), userId: str = Form(...)):
    if not sessionId:
        raise HTTPException(status_code=400, detail="Missing sessionId")

    chunk_keys = await get_chunk_list(sessionId)
    if not chunk_keys:
        raise HTTPException(status_code=404, detail="No chunks found")

    temp_dir = tempfile.mkdtemp()
    local_files = []
    final_path = None
    sample_path = None

    try:
        # Download chunk files from S3 and save locally
        for item in chunk_keys:
            key = item["chunk_name"]
            local_filename = os.path.basename(key)
            local_path = os.path.join(temp_dir, local_filename)

            file_data = download_file_from_s3(key)
            with open(local_path, "wb") as f:
                f.write(file_data)

            local_files.append(local_path)

        # Merge chunks
        final_path = os.path.join(temp_dir, f"{sessionId}_merged.wav")
        merge_audio_chunks(local_files, final_path)

         # If upload_file_to_s3 is async, await it
        with open(final_path, "rb") as f:
            s3_url = upload_file_to_s3(f"final_recording/{sessionId}_merged.wav", f.read())

        # Fetch salesperson sample from DB
        sample_url = await get_salesperson_sample(userId)
        s3_sample_key = extract_filename_from_s3_url(sample_url["s3_url"])  # gets `audio_salesperson_samples/...`

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
         # If upload_file_to_s3 is async, await it
        with open(final_path, "rb") as f:
         s3_url = upload_file_to_s3(f"final_recording/{sessionId}_merged.wav", f.read())

         transcript = ""
         speakers = []

         doc_id = await save_final_audio(sessionId, s3_url, results, userId)

         return {
            "id": str(doc_id),
            "transcript": "",
            "results":results
         }

    finally:
        for file in local_files:
            if os.path.exists(file):
                os.remove(file)
        if final_path and os.path.exists(final_path):
            os.remove(final_path)
        if sample_path and os.path.exists(sample_path):
            os.remove(sample_path)


@router.post("/meetings", response_model=MeetingResponse)
async def create_meeting_api(meeting: MeetingCreate):
    meeting_id = await create_meeting(meeting.dict())
    return MeetingResponse(id=str(meeting_id), **meeting.dict())

@router.get("/meetings", response_model=List[MeetingResponse])
async def get_all_meetings_api(userId:str):
    docs = await get_all_meetings(userId)
    return [meeting_doc_to_response(doc) for doc in docs]

@router.get("/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_by_id_api(meeting_id: str):
    doc = await get_meeting_by_id(meeting_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting_doc_to_response(doc)