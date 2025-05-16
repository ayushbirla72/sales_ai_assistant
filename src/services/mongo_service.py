from motor.motor_asyncio import AsyncIOMotorClient
from src.config import MONGO_URL, MONGO_DB_NAME
from datetime import datetime

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]

chunks_col = db["chunks"]
final_col = db["final"]
sales_col = db["sales_samples"]

async def save_chunk_metadata(session_id: str, s3_url: str, userId:str):
    await chunks_col.update_one(
        {"sessionId": session_id, "userId":userId},
        {"$push": {"chunks": s3_url}},
        upsert=True
    )

async def get_chunk_list(session_id: str):
    doc = await chunks_col.find_one({"sessionId": session_id})
    print(f"chunksss {doc}")
    return doc["chunks"] if doc else []

async def save_final_audio(session_id: str, s3_url: str, transcript: str, speakers: list,userId:str):
    doc = {
        "sessionId": session_id,
        "s3_url": s3_url,
        "transcript": transcript,
        # "speakers": speakers,
        "userId":userId
    }
    result = await final_col.insert_one(doc)
    return result.inserted_id





async def save_salesperson_sample(filename: str, s3_url: str, userId:str):
    doc = {
        "filename": filename,
        "s3_url": s3_url,
        "uploadedAt": datetime.utcnow(),
        "userId":userId
    }
    result = await sales_col.insert_one(doc)
    return result.inserted_id

async def get_salesperson_sample(userId:str):
    doc = {
        "userId":userId
    }
    result = await sales_col.find_one(doc)
    print(f"data.. {result}")
    return result

chunks_col_Transcription = db["transcription_chunks"]

users_collection = db["users"]

async def save_transcription_chunk(sessionId: str, s3_url: str, transcript: str, userId:str):
    doc = {
        "sessionId": sessionId,
        "s3_url": s3_url,
        "transcript": transcript,
        "uploadedAt": datetime.utcnow(),
        "userId":userId
    }
    result = await chunks_col_Transcription.insert_one(doc)
    return result.inserted_id

async def save_user_details(data:object):
    print(f"dataaaaaaa  {data}")
    # password =" 11 "
    print(f"password {data["password"]}")
    doc ={
        "email":data["email"],
        "password":data["password"]
    }
    result = await users_collection.insert_one(doc)
    return result.inserted_id

async def get_user_details(data:object):
    doc ={
        "email":data["email"]
    }
    result = await users_collection.find_one(doc)
    print(f"data.. {result}")
    return result