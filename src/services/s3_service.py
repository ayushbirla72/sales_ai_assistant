import boto3
from src.config import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET_NAME, AWS_REGION

s3 = boto3.client("s3", region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY)

def upload_file_to_s3(key: str, content: bytes):
    s3.put_object(Bucket=AWS_BUCKET_NAME, Key=f"{key}", Body=content)
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"

def download_file_from_s3(key: str) -> bytes:
    response = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=f"{key}")
    return response["Body"].read()
