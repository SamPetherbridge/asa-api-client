"""Apple Search Ads API client library.

A modern, fully-typed Python client for the Apple Search Ads API
with async support, Pydantic models, and comprehensive logging.

Example:
    Basic usage with the client::

        from asa_api_client import AppleSearchAdsClient

        client = AppleSearchAdsClient(
            client_id="your-client-id",
            team_id="your-team-id",
            key_id="your-key-id",
            org_id=123456,
            private_key_path="path/to/private-key.pem",
        )

        # List all campaigns
        campaigns = client.campaigns.list()

        # Async usage
        campaigns = await client.campaigns.list_async()
"""

from asa_api_client.client import AppleSearchAdsClient
from asa_api_client.exceptions import (
    AppleSearchAdsError,
    AuthenticationError,
    ConfigurationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from asa_api_client.logging import configure_logging
from asa_api_client.settings import Settings

__all__ = [
    "AppleSearchAdsClient",
    "AppleSearchAdsError",
    "AuthenticationError",
    "ConfigurationError",
    "NotFoundError",
    "RateLimitError",
    "Settings",
    "ValidationError",
    "configure_logging",
]

__version__ = "0.1.0"
