"""Apple Ads API client library.

A modern, fully-typed Python client for the Apple Ads Platform API v1
with async support, Pydantic models, and structured logging.

Example:
    Basic usage with ``AppleAdsClient``::

        from asa_api_client import AppleAdsClient, Query

        with AppleAdsClient.from_env() as client:
            for campaign in client.campaigns.iter_all(
                Query().where("status", "EQUALS", "ENABLED")
            ):
                print(campaign.name)
"""

from asa_api_client.exceptions import (
    AppleAdsError,
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
from asa_api_client.v1.query import FilterOperator, Query, SortOrder

__all__ = [
    "AppleAdsClient",
    "AppleAdsError",
    "AppleSearchAdsError",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "FilterOperator",
    "NetworkError",
    "NotFoundError",
    "PartialFailureError",
    "Query",
    "RateLimitError",
    "ServerError",
    "Settings",
    "SortOrder",
    "ValidationError",
    "configure_logging",
]

__version__ = "1.0.1"
