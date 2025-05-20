from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import MONGO_URL, MONGO_DB_NAME
from datetime import datetime
from pymongo import DESCENDING

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]

chunks_col = db["chunks"]
final_col = db["finalTranscriptions"]
sales_col = db["salesSamples"]
chunks_col_Transcription = db["transcriptionChunks"]
users_collection = db["users"]
meetings_collection = db["meetings"]
prediction_collection = db["predictions"]
suggestion_collection = db["suggestions"]
meeting_summry_collection = db["meetingSummrys"]

# Save chunk metadata
async def save_chunk_metadata(session_id: str, chunk_name: str, userId: str, transcript: str, s3_url: str):
    now = datetime.utcnow()
    doc = {
        "sessionId": session_id,
        "s3_url": s3_url,
        "transcript": transcript,
        "uploadedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "userId": userId,
        "chunk_name": chunk_name,
    }
    await chunks_col.update_one(
        {"sessionId": session_id, "userId": userId},
        {
            "$push": {"chunks": doc},
            "$set": {"updatedAt": now},
            "$setOnInsert": {"createdAt": now}
        },
        upsert=True
    )

# Get chunk list
async def get_chunk_list(session_id: str):
    doc = await chunks_col.find_one({"sessionId": session_id})
    print(f"chunksss {doc}")
    return doc["chunks"] if doc else []

# Save final audio
async def save_final_audio(session_id: str, s3_url: str, results: list, userId: str):
    now = datetime.utcnow()
    doc = {
        "sessionId": session_id,
        "s3_url": s3_url,
        "results": results,
        "userId": userId,
        "createdAt": now,
        "updatedAt": now
    }
    result = await final_col.insert_one(doc)
    return result.inserted_id

# Save salesperson sample
async def save_salesperson_sample(filename: str, s3_url: str, userId: str):
    now = datetime.utcnow()
    doc = {
        "filename": filename,
        "s3_url": s3_url,
        "uploadedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "userId": userId
    }
    result = await sales_col.insert_one(doc)
    return result.inserted_id

# Get salesperson sample
async def get_salesperson_sample(userId: str):
    result = await sales_col.find_one({"userId": userId})
    print(f"data.. {result}")
    return result

# Save transcription chunk
async def save_transcription_chunk(sessionId: str, s3_url: str, transcript: str, userId: str):
    now = datetime.utcnow()
    doc = {
        "sessionId": sessionId,
        "s3_url": s3_url,
        "transcript": transcript,
        "uploadedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "userId": userId
    }
    result = await chunks_col_Transcription.insert_one(doc)
    return result.inserted_id

# Save user details
async def save_user_details(data: object):
    print(f"dataaaaaaa  {data}")
    print(f"password {data['password']}")
    now = datetime.utcnow()
    doc = {
        "email": data["email"],
        "name": data["name"],
        "password": data["password"],
        "createdAt": now,
        "updatedAt": now
    }
    result = await users_collection.insert_one(doc)
    inserted_user = await users_collection.find_one({"_id":result.inserted_id})
    return inserted_user

# Get user details
async def get_user_details(data: object):
    result = await users_collection.find_one({"email": data["email"]})
    print(f"data.. {result}")
    return result


async def create_meeting(data: dict):
    print(f"dataaaaaaa  {data}")
    data["createdAt"] = datetime.utcnow()
    data["updatedAt"] = datetime.utcnow()
    result = await meetings_collection.insert_one(data)
    return result.inserted_id

async def get_all_meetings(userId:str):
    cursor = meetings_collection.find({"userId":userId})
    return await cursor.to_list(length=None)

async def get_meeting_by_id(meeting_id: str):
    doc = await meetings_collection.find_one({"_id": ObjectId(meeting_id)})
    return doc

async def save_prediction_result(userId: str, sessionId: str, question: str, topic: str, result: str):
    now = datetime.utcnow()
    doc = {
        "userId": userId,
        "sessionId": sessionId,
        "question": question,
        "topic": topic,
        "result": result,
        "createdAt": now,
        "updatedAt": now
    }
    res = await prediction_collection.insert_one(doc)
    return res.inserted_id

async def   get_predictions(userId: str, sessionId: str = None):
    now = datetime.utcnow()
    query = {"userId": userId}
    if sessionId:
        query["sessionId"] = sessionId
    cursor = prediction_collection.find(query)
    return await cursor.to_list(length=100)

async def save_suggestion(sessionId: str, userId: str, transcript: str, suggestion: str):
    doc = {
        "sessionId": sessionId,
        "userId": userId,
        "transcript": transcript,
        "suggestion": suggestion,
        "createdAt": datetime.utcnow()
    }
    result = await suggestion_collection.insert_one(doc)
    return result.inserted_id



def serialize_suggestion(suggestion: dict) -> dict:
    suggestion["_id"] = str(suggestion["_id"])  # Convert ObjectId to string
    return suggestion

async def get_suggestions_by_user_and_session(userId: str, sessionId: str):
    query = {"userId": userId, "sessionId": sessionId}
    cursor = suggestion_collection.find(query)
    results = await cursor.to_list(length=None)
    return [serialize_suggestion(s) for s in results]



async def update_final_summary_and_suggestion(sessionId: str, userId: str, summary: str, suggestion:str):
    now = datetime.utcnow()
    doc = {
        "userId": userId,
        "sessionId": sessionId,
        "summary": summary,
        "suggestion":suggestion,
        "createdAt": now,
        "updatedAt": now
    }
    await meeting_summry_collection.insert_one(
    doc
    )


async def get_summary_and_suggestion(sessionId: str, userId: Optional[str] = None):
    query = {"sessionId": sessionId}
    if userId:
        query["userId"] = userId
    return await meeting_summry_collection.find_one(query)

async def update_user_password(email: str, new_hashed_password: str):
    now = datetime.utcnow()
    result = await users_collection.update_one(
        {"email": email},
        {"$set": {"password": new_hashed_password, "updatedAt": now}}
    )
    return result.modified_count