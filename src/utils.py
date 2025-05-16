import bcrypt
from urllib.parse import urlparse, unquote


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# def extract_filename_from_s3_url(s3_url: str) -> str:
#     return s3_url.split("/")[-2]

def extract_filename_from_s3_url(s3_url: str) -> str:
    parsed_url = urlparse(s3_url)
    return unquote(parsed_url.path.lstrip("/"))
