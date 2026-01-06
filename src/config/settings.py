"""Application settings"""

from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    model_config = ConfigDict(
        env_prefix="INSTANCEPEDIA_",
        case_sensitive=False
    )

    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None

