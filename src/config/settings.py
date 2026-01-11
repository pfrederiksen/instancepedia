"""Application settings

Settings are loaded in order of precedence (highest to lowest):
1. Environment variables (INSTANCEPEDIA_*)
2. Config file (~/.instancepedia/config.toml)
3. Default values
"""

import os
import sys
from pathlib import Path
from typing import Any, Type

from pydantic import ConfigDict
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

# Import tomllib (Python 3.11+) or tomli (Python 3.9-3.10)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".instancepedia" / "config.toml"


class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that loads from TOML config file."""

    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:
        """Get field value from TOML config."""
        config_data = self._load_config()
        if field_name in config_data:
            return config_data[field_name], field_name, False
        return None, field_name, False

    def _load_config(self) -> dict:
        """Load config from TOML file."""
        if not hasattr(self, '_config_cache'):
            self._config_cache = {}
            config_path = get_config_path()
            if config_path.exists() and tomllib is not None:
                try:
                    with open(config_path, "rb") as f:
                        self._config_cache = tomllib.load(f)
                except Exception:
                    pass  # Silently ignore config file errors
        return self._config_cache

    def __call__(self) -> dict[str, Any]:
        """Return all settings from config file."""
        return self._load_config()


class Settings(BaseSettings):
    """Application settings

    Settings can be configured via:
    - Environment variables: INSTANCEPEDIA_<SETTING_NAME>
    - Config file: ~/.instancepedia/config.toml

    Example config.toml:
        aws_region = "us-west-2"
        aws_profile = "my-profile"
        pricing_concurrency = 15
    """

    model_config = ConfigDict(
        env_prefix="INSTANCEPEDIA_",
        case_sensitive=False
    )

    aws_region: str = "us-east-1"
    aws_profile: str | None = None

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
    max_pool_connections: int = 50  # Max connections in the HTTP connection pool

    # TUI configuration
    vim_keys: bool = False  # Enable vim-style navigation (hjkl)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources order.

        Order (highest to lowest priority):
        1. Init settings (passed to constructor)
        2. Environment variables
        3. TOML config file
        """
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )


def create_default_config() -> str:
    """Generate default config file content."""
    return '''# Instancepedia Configuration
# Place this file at ~/.instancepedia/config.toml

# AWS Configuration
# aws_region = "us-east-1"
# aws_profile = "default"

# Timeout Configuration (in seconds)
# aws_connect_timeout = 10
# aws_read_timeout = 60
# pricing_read_timeout = 90

# Performance Configuration
# pricing_concurrency = 10      # TUI mode concurrent requests
# cli_pricing_concurrency = 5   # CLI mode concurrent requests
# pricing_request_delay_ms = 50 # Delay between requests
# spot_batch_size = 50          # Instance types per spot API call
# ui_update_throttle = 10       # Update UI every N pricing updates
# max_pool_connections = 50     # HTTP connection pool size

# TUI Configuration
# vim_keys = false              # Enable vim-style navigation (hjkl)
'''

