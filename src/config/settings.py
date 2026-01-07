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

    # Timeout configuration (in seconds)
    aws_connect_timeout: int = 10  # Connection timeout for AWS APIs
    aws_read_timeout: int = 60  # Read timeout for AWS API calls
    pricing_read_timeout: int = 90  # Read timeout for pricing API (can be slower)

