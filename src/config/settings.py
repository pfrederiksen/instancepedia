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

    # Performance configuration
    pricing_concurrency: int = 10  # Max concurrent pricing requests (TUI mode)
    pricing_retry_concurrency: int = 3  # Max concurrent requests for retries
    cli_pricing_concurrency: int = 5  # Max concurrent pricing requests (CLI mode)
    pricing_request_delay_ms: int = 50  # Delay between requests in milliseconds
    spot_batch_size: int = 50  # Number of instance types per spot price API call
    ui_update_throttle: int = 10  # Update UI every N pricing updates

