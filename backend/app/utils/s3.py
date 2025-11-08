import boto3
from botocore.exceptions import ClientError
from app.config import get_settings

settings = get_settings()

def get_s3_client():
    """Get S3 client configured for LocalStack."""
    return boto3.client(
        's3',
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.s3_region
    )

def create_bucket_if_not_exists():
    """Create the S3 bucket if it doesn't exist."""
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        try:
            s3.create_bucket(Bucket=settings.s3_bucket)
            print(f"Created bucket: {settings.s3_bucket}")
        except Exception as e:
            print(f"Error creating bucket: {e}")

def upload_file(file_obj, key: str) -> str:
    """Upload a file to S3 and return the key."""
    s3 = get_s3_client()
    try:
        s3.upload_fileobj(file_obj, settings.s3_bucket, key)
        return key
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise

def download_file(key: str):
    """Download a file from S3."""
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=settings.s3_bucket, Key=key)
        return response['Body']
    except Exception as e:
        print(f"Error downloading file: {e}")
        raise

def download_file_bytes(key: str) -> bytes:
    """Download a file from S3 and return as bytes."""
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=settings.s3_bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        print(f"Error downloading file bytes: {e}")
        raise

def delete_file(key: str):
    """Delete a file from S3."""
    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=settings.s3_bucket, Key=key)
    except Exception as e:
        print(f"Error deleting file: {e}")
        raise