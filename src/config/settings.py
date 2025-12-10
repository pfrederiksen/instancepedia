"""Application settings"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None

    class Config:
        env_prefix = "INSTANCEPEDIA_"
        case_sensitive = False

