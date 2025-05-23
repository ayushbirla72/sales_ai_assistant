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
from src.services.google_auth_service import verify_google_token

load_dotenv()

client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
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

class GoogleAuthRequest(BaseModel):
    id_token: str
    google_access_token: str
    google_refresh_token: str


class ConnectGoogleRequest(BaseModel):
    id_token: str

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
    user = await save_user_details({
        "name": data.name, 
        "email": data.email, 
        "password": hashed_pw,
    })

    payload = {
        "user_id": str(user["_id"]),
        "email": data.email,
        "access_token": data.google_access_token,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    secret = os.getenv("JWT_SECRET", "default_secret")
    token = jwt.encode(payload, secret, algorithm="HS256")
    print(f"tokennnn.... {token}")

    return {"message": "Signup successful.", "userId": str(user), "access_token": token}

@router.post("/login")
async def login(data: LoginRequest):
    """Login with email and password"""
    try:
        print(f"Login attempt for email: {data.email}")
        user = await get_user_details({"email": data.email})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")
        
        if not user.get("password"):
            raise HTTPException(
                status_code=400, 
                detail="This account was created with Google. Please use Google login."
            )
        
        if not verify_password(data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid password.")
        
        # Generate JWT token
        payload = {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        secret = os.getenv("JWT_SECRET", "default_secret")
        token = jwt.encode(payload, secret, algorithm="HS256")

        return {
            "message": "Login successful.",
            "userId": str(user["_id"]),
            "access_token": token,
            "user": {
                "name": user.get("name"),
                "email": user["email"],
                "picture": user.get("picture"),
                "is_google_connected": user.get("is_google_connected", False)
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.post("/google/auth")
async def google_auth(data: GoogleAuthRequest):
    """
    Handle both Google signup and login.
    If user exists, log them in. If not, create a new account.
    """
    try:
        # Verify Google token
        print("Verifying Google token...")
        user_info = verify_google_token(data.id_token)
        print(f"User info from Google: {user_info}")
        
        # Check if user exists
        user = await get_user_details({"email": user_info["email"]})
        print(f"Existing user: {user}")

        if user:
            # User exists - Update Google info and login
            print("User exists, updating Google info...")
            await users_collection.update_one(
                {"email": user_info["email"]},
                {
                    "$set": {
                        "google_id": user_info["google_id"],
                        "picture": user_info["picture"],
                        "google_id_token": data.id_token,
                        "is_google_connected": True,
                        "updatedAt": datetime.utcnow(),
                        "google_access_token": data.google_access_token,
                        "google_refresh_token": data.google_refresh_token,
                    }
                }
            )
            message = "Google login successful."
        else:
            # User doesn't exist - Create new account
            print("Creating new user...")
            user = await save_user_details({
                "name": user_info["name"],
                "email": user_info["email"],
                "password": None,  # No password for Google auth
                "google_id": user_info["google_id"],
                "picture": user_info["picture"],
                "google_id_token": data.id_token,
                "is_google_connected": True,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "google_access_token": data.google_access_token,
                "google_refresh_token": data.google_refresh_token,
            })
            message = "Google signup successful."

        # Generate JWT token
        payload = {
            "user_id": str(user["_id"]),
            "email": user_info["email"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        print(f"JWT payload: {payload}")
        
        secret = os.getenv("JWT_SECRET", "default_secret")
        token = jwt.encode(payload, secret, algorithm="HS256")
        print(f"Generated JWT token: {token}")

        return {
            "message": "Login/Signup successful",
            "userId": str(user["_id"]),
            "access_token": token,
            "user": {
                "name": user_info["name"],
                "email": user_info["email"],
                "picture": user_info["picture"],
                "is_google_connected": True
            }
        }
    except ValueError as e:
        print(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect-google")
async def connect_google_account(
    data: ConnectGoogleRequest,
    token_data: dict = Depends(verify_token)
):
    """Connect Google account to an existing user account."""
    try:
        # Verify Google token
        user_info = verify_google_token(data.id_token)
        
        # Get user from database
        user = await get_user_details({"email": token_data["email"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        # Update user's Google info
        await users_collection.update_one(
            {"email": token_data["email"]},
            {
                "$set": {
                    "google_id": user_info["google_id"],
                    "picture": user_info["picture"],
                    "google_id_token": data.id_token,
                    "is_google_connected": True,
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        return {
            "message": "Google account connected successfully.",
            "is_google_connected": True
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
