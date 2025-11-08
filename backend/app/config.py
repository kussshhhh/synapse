from functools import lru_cache
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/synapse"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "synapse"
    db_user: str = "postgres"
    db_password: str = "password"
    
    # S3/LocalStack
    s3_endpoint: str = "http://localhost:4566"
    s3_bucket: str = "synapse-storage"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    
    # Environment
    environment: str = "development"

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values) -> str:
        if isinstance(v, str):
            return v
        # If database_url is not provided, construct it from components
        if hasattr(values, 'data'):
            data = values.data
            return (
                f"postgresql://{data.get('db_user', 'postgres')}:"
                f"{data.get('db_password', 'password')}@"
                f"{data.get('db_host', 'localhost')}:"
                f"{data.get('db_port', 5432)}/"
                f"{data.get('db_name', 'synapse')}"
            )
        return "postgresql://postgres:password@localhost:5432/synapse"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()