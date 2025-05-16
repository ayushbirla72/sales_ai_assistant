from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from src.services.mongo_service import get_user_details, save_user_details
from src.utils import hash_password, verify_password
import os
from dotenv import load_dotenv

load_dotenv()

client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["sales_ai_assistant"]
users_collection = db["users"]

router = APIRouter()

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
async def signup(data: SignupRequest):
    existing_user = await get_user_details({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    print(f"loggggggg... {data}")

    hashed_pw = hash_password(data.password)

    print(f"hass pasword {hashed_pw}")
    await save_user_details({"email": data.email, "password": hashed_pw})
    return {"message": "Signup successful."}

@router.post("/login")
async def login(data: LoginRequest):
    print(f"emilllll  {data}")
    user = await get_user_details({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    print(f"data  {user["_id"]}")
    
    return {"message": "Login successful.", "userId":f"{user["_id"]}"}
