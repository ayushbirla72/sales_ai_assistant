from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from src.services.mongo_service import get_user_details, save_user_details, update_user_password
from src.utils import hash_password, verify_password
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client["sales_ai_assistant"]
users_collection = db["users"]

router = APIRouter()

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str

class GetProfileRequest(BaseModel):
    email: EmailStr

class UpdateProfileRequest(BaseModel):
    email: EmailStr
    name: str
    company_name: str
    mobile_number: str
    position: str

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            os.getenv("JWT_SECRET", "default_secret"), 
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        email = payload.get("email")
        user_id = payload.get("user_id")
        if email is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token payload."
            )
        return {"email": email, "user_id": user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Token verification failed: {str(e)}"
        )

@router.post("/signup")
async def signup(data: SignupRequest):
    existing_user = await get_user_details({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    print(f"loggggggg... {data}")

    hashed_pw = hash_password(data.password)

    print(f"hass pasword {hashed_pw}")
    user = await save_user_details({"name": data.name, "email": data.email, "password": hashed_pw})

    payload = {
        "user_id": str(user["_id"]),
        "email": data.email,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    secret = os.getenv("JWT_SECRET", "default_secret")
    token = jwt.encode(payload, secret, algorithm="HS256")
    print(f"tokennnn.... {token}")

    return {"message": "Signup successful.", "userId": str(user), "access_token": token}


@router.post("/login")
async def login(data: LoginRequest):
    print(f"emilllll  {data}")
    user = await get_user_details({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    print(f"data  {user["_id"]}")

    # Generate JWT token
    payload = {
        "user_id": str(user["_id"]),
        "email": user["email"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    secret = os.getenv("JWT_SECRET", "default_secret")
    token = jwt.encode(payload, secret, algorithm="HS256")

    return {"message": "Login successful.", "userId": f"{user["_id"]}", "access_token": token}

@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, email: str = Depends(verify_token)):
    user = await get_user_details({"email": data.email})
    if not user or not verify_password(data.old_password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or old password.")
    new_hashed_pw = hash_password(data.new_password)
    updated = await update_user_password(data.email, new_hashed_pw)
    if updated:
        return {"message": "Password changed successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to update password.")

@router.post("/profile")
async def get_profile(data: GetProfileRequest, email: str = Depends(verify_token)):
    user = await get_user_details({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    # Remove password from the response
    user.pop("password", None)
    return user

@router.post("/update-profile")
async def update_profile(data: UpdateProfileRequest, email: str = Depends(verify_token)):
    user = await get_user_details({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Update user profile
    now = datetime.utcnow()
    result = await users_collection.update_one(
        {"email": data.email},
        {"$set": {
            "name": data.name,
            "company_name": data.company_name,
            "mobile_number": data.mobile_number,
            "position": data.position,
            "updatedAt": now
        }}
    )
    
    if result.modified_count:
        return {"message": "Profile updated successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to update profile.")
