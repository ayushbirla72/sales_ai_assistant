# from motor.motor_asyncio import AsyncIOMotorClient
# from src.config import MONGO_URL, MONGO_DB_NAME
# from datetime import datetime

# client = AsyncIOMotorClient(MONGO_URL)
# db = client[MONGO_DB_NAME]

# chunks_col = db["chunks"]
# final_col = db["final"]
# sales_col = db["sales_samples"]

# async def save_chunk_metadata(session_id: str, chunk_name: str, userId:str, transcript:str, s3_url:str ):
#     doc = {
#         "sessionId": session_id,
#         "s3_url": s3_url,
#         "transcript": transcript,
#         "uploadedAt": datetime.utcnow(),
#         "userId":userId,
#         "chunk_name": chunk_name,
#     }
#     await chunks_col.update_one(
#         {"sessionId": session_id, "userId":userId},
#         {"$push": {"chunks": doc}},
#         upsert=True
#     )

# async def get_chunk_list(session_id: str):
#     doc = await chunks_col.find_one({"sessionId": session_id})
#     print(f"chunksss {doc}")
#     return doc["chunks"] if doc else []

# async def save_final_audio(session_id: str, s3_url: str, transcript: str, speakers: list,userId:str):
#     doc = {
#         "sessionId": session_id,
#         "s3_url": s3_url,
#         "transcript": transcript,
#         # "speakers": speakers,
#         "userId":userId
#     }
#     result = await final_col.insert_one(doc)
#     return result.inserted_id





# async def save_salesperson_sample(filename: str, s3_url: str, userId:str):
#     doc = {
#         "filename": filename,
#         "s3_url": s3_url,
#         "uploadedAt": datetime.utcnow(),
#         "userId":userId
#     }
#     result = await sales_col.insert_one(doc)
#     return result.inserted_id

# async def get_salesperson_sample(userId:str):
#     doc = {
#         "userId":userId
#     }
#     result = await sales_col.find_one(doc)
#     print(f"data.. {result}")
#     return result

# chunks_col_Transcription = db["transcription_chunks"]

# users_collection = db["users"]

# async def save_transcription_chunk(sessionId: str, s3_url: str, transcript: str, userId:str):
#     doc = {
#         "sessionId": sessionId,
#         "s3_url": s3_url,
#         "transcript": transcript,
#         "uploadedAt": datetime.utcnow(),
#         "userId":userId
#     }
#     result = await chunks_col_Transcription.insert_one(doc)
#     return result.inserted_id

# async def save_user_details(data:object):
#     print(f"dataaaaaaa  {data}")
#     # password =" 11 "
#     print(f"password {data["password"]}")
#     doc ={
#         "email":data["email"],
#         "password":data["password"]
#     }
#     result = await users_collection.insert_one(doc)
#     return result.inserted_id

# async def get_user_details(data:object):
#     doc ={
#         "email":data["email"]
#     }
#     result = await users_collection.find_one(doc)
#     print(f"data.. {result}")
#     return result


from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import MONGO_URL, MONGO_DB_NAME
from datetime import datetime

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]

chunks_col = db["chunks"]
final_col = db["final"]
sales_col = db["sales_samples"]
chunks_col_Transcription = db["transcription_chunks"]
users_collection = db["users"]
meetings_collection = db["meetings"]

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
        "password": data["password"],
        "createdAt": now,
        "updatedAt": now
    }
    result = await users_collection.insert_one(doc)
    return result.inserted_id

# Get user details
async def get_user_details(data: object):
    result = await users_collection.find_one({"email": data["email"]})
    print(f"data.. {result}")
    return result


async def create_meeting(data: dict):
    result = await meetings_collection.insert_one(data)
    return result.inserted_id

async def get_all_meetings(userId:str):
    cursor = meetings_collection.find({"userId":userId})
    return await cursor.to_list(length=None)

async def get_meeting_by_id(meeting_id: str):
    doc = await meetings_collection.find_one({"_id": ObjectId(meeting_id)})
    return doc