from google.oauth2 import id_token
from google.auth.transport import requests
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def verify_google_token(token: str) -> dict:
    """
    Verify the Google ID token and return the user information.
    
    Args:
        token (str): The Google ID token to verify
        
    Returns:
        dict: User information including email, name, and picture
    """
    print("call in side the verification....")
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        print(f"idinfo... {idinfo}")
        
        # Check if the token is valid
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid issuer.')
            
        # Return user information
        return {
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'google_id': idinfo['sub']
        }
    except Exception as e:
        print(f"invalid token: {str(e)}")
        raise ValueError(f'Invalid token: {str(e)}') 