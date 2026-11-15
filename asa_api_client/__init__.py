"""Apple Ads API client library.

A modern, fully-typed Python client for the Apple Ads Platform API v1
(and legacy Campaign Management API v5) with async support, Pydantic
models, and comprehensive logging.

Example:
    Basic usage with the Platform API v1 client::

        from asa_api_client import AppleAdsClient

        client = AppleAdsClient(
            client_id="your-client-id",
            team_id="your-team-id",
            key_id="your-key-id",
            ad_account_id="123456",
            private_key_path="path/to/private-key.pem",
        )

        # Iterate all campaigns
        for campaign in client.campaigns.iter_all():
            print(campaign.name)

        # Async usage
        page = await client.campaigns.query_async()
"""

from asa_api_client.client import AppleSearchAdsClient
from asa_api_client.exceptions import (
    AppleSearchAdsError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    NetworkError,
    NotFoundError,
    PartialFailureError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from asa_api_client.logging import configure_logging
from asa_api_client.settings import Settings
from asa_api_client.v1.client import AppleAdsClient

__all__ = [
    "AppleAdsClient",
    "AppleSearchAdsClient",
    "AppleSearchAdsError",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "NetworkError",
    "NotFoundError",
    "PartialFailureError",
    "RateLimitError",
    "ServerError",
    "Settings",
    "ValidationError",
    "configure_logging",
]

__version__ = "0.6.0"
