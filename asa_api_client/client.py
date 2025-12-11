"""Main client for the Apple Search Ads API.

This module provides the AppleSearchAdsClient class, which is the
primary interface for interacting with the Apple Search Ads API.
"""

from pathlib import Path
from types import TracebackType
from typing import Self

import httpx

from asa_api_client.auth import Authenticator
from asa_api_client.logging import get_logger
from asa_api_client.resources.campaigns import CampaignResource
from asa_api_client.resources.reports import ReportResource

logger = get_logger(__name__)

# API base URL
DEFAULT_BASE_URL = "https://api.searchads.apple.com/api/v5"


class AppleSearchAdsClient:
    """Client for interacting with the Apple Search Ads API.

    This is the main entry point for the library. It provides access
    to all API resources through a structured, resource-based interface.

    The client supports both synchronous and asynchronous operations.
    Async methods are available with the `_async` suffix.

    Attributes:
        org_id: The Apple Search Ads organization ID.
        campaigns: Resource for managing campaigns.
        reports: Resource for generating reports.

    Example:
        Basic usage::

            from asa_api_client import AppleSearchAdsClient

            client = AppleSearchAdsClient(
                client_id="SEARCHADS.abc123",
                team_id="TEAM123",
                key_id="KEY123",
                org_id=123456,
                private_key_path="path/to/private-key.pem",
            )

            # List campaigns
            campaigns = client.campaigns.list()
            for campaign in campaigns:
                print(f"{campaign.name}: {campaign.status}")

            # Create a campaign
            from asa_api_client.models import CampaignCreate, Money, CampaignSupplySource

            new_campaign = client.campaigns.create(
                CampaignCreate(
                    name="My Campaign",
                    budget_amount=Money.usd(10000),
                    adam_id=123456789,
                    countries_or_regions=["US"],
                    supply_sources=[CampaignSupplySource.APPSTORE_SEARCH_RESULTS],
                )
            )

        Async usage::

            async with AppleSearchAdsClient(...) as client:
                campaigns = await client.campaigns.list_async()

        Context manager::

            with AppleSearchAdsClient(...) as client:
                campaigns = client.campaigns.list()

        From environment variables::

            # Set these environment variables:
            # ASA_CLIENT_ID, ASA_TEAM_ID, ASA_KEY_ID, ASA_ORG_ID
            # ASA_PRIVATE_KEY or ASA_PRIVATE_KEY_PATH

            client = AppleSearchAdsClient.from_env()
    """

    def __init__(
        self,
        *,
        client_id: str,
        team_id: str,
        key_id: str,
        org_id: int,
        private_key: str | None = None,
        private_key_path: Path | str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Apple Search Ads client.

        You must provide either `private_key` or `private_key_path`.

        Args:
            client_id: Your Apple Search Ads API client ID.
            team_id: Your Apple Developer team ID.
            key_id: The key ID for your private key.
            org_id: Your Apple Search Ads organization ID.
            private_key: The private key as a PEM-encoded string.
            private_key_path: Path to the private key PEM file.
            base_url: The API base URL. Defaults to the v5 API.
            timeout: Request timeout in seconds.

        Raises:
            ConfigurationError: If credentials are invalid or missing.
        """
        self.org_id = org_id
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

        self._authenticator = Authenticator(
            client_id=client_id,
            team_id=team_id,
            key_id=key_id,
            org_id=org_id,
            private_key=private_key,
            private_key_path=private_key_path,
        )

        # HTTP clients (created lazily)
        self._http_client: httpx.Client | None = None
        self._async_http_client: httpx.AsyncClient | None = None

        # Initialize resources
        self._campaigns = CampaignResource(self)
        self._reports = ReportResource(self)

        logger.info(
            "AppleSearchAdsClient initialized for org_id=%d, base_url=%s",
            org_id,
            base_url,
        )

    @classmethod
    def from_env(
        cls,
        *,
        env_file: str | Path | None = ".env",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> Self:
        """Create a client from environment variables and .env file.

        Loads configuration from environment variables and optionally
        from a `.env` file. Environment variables take precedence.

        Required settings (via env vars or .env file):
        - ASA_CLIENT_ID
        - ASA_TEAM_ID
        - ASA_KEY_ID
        - ASA_ORG_ID
        - ASA_PRIVATE_KEY or ASA_PRIVATE_KEY_PATH

        Args:
            env_file: Path to .env file to load. Set to None to skip
                loading from file. Defaults to ".env".
            base_url: The API base URL.
            timeout: Request timeout in seconds.

        Returns:
            A configured AppleSearchAdsClient instance.

        Raises:
            ConfigurationError: If required settings are missing or invalid.

        Example:
            Load from .env file::

                client = AppleSearchAdsClient.from_env()

            Load from a specific env file::

                client = AppleSearchAdsClient.from_env(env_file=".env.production")

            Only use environment variables::

                client = AppleSearchAdsClient.from_env(env_file=None)
        """
        auth = Authenticator.from_env(env_file=env_file)

        return cls(
            client_id=auth.client_id,
            team_id=auth.team_id,
            key_id=auth.key_id,
            org_id=auth.org_id,
            private_key=auth._private_key,
            base_url=base_url,
            timeout=timeout,
        )

    def _get_http_client(self) -> httpx.Client:
        """Get or create the synchronous HTTP client.

        Returns:
            The httpx.Client instance.
        """
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._http_client

    def _get_async_http_client(self) -> httpx.AsyncClient:
        """Get or create the asynchronous HTTP client.

        Returns:
            The httpx.AsyncClient instance.
        """
        if self._async_http_client is None:
            self._async_http_client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._async_http_client

    @property
    def campaigns(self) -> CampaignResource:
        """Get the campaigns resource.

        Returns:
            CampaignResource for managing campaigns.

        Example:
            List all campaigns::

                campaigns = client.campaigns.list()

            Access ad groups in a campaign::

                ad_groups = client.campaigns(123).ad_groups.list()
        """
        return self._campaigns

    @property
    def reports(self) -> ReportResource:
        """Get the reports resource.

        Returns:
            ReportResource for generating reports.

        Example:
            Get campaign report::

                from datetime import date

                report = client.reports.campaigns(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                )
        """
        return self._reports

    def close(self) -> None:
        """Close the HTTP clients and release resources.

        This should be called when you're done using the client.
        Alternatively, use the client as a context manager.
        """
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

        if self._async_http_client is not None:
            # For sync close of async client, we just set to None
            # The actual close should be done with aclose()
            self._async_http_client = None

        logger.debug("Client closed")

    async def aclose(self) -> None:
        """Close the HTTP clients asynchronously.

        This should be called when using the client in async mode.
        """
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

        if self._async_http_client is not None:
            await self._async_http_client.aclose()
            self._async_http_client = None

        logger.debug("Client closed (async)")

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            The client instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and close resources."""
        self.close()

    async def __aenter__(self) -> Self:
        """Enter the async context manager.

        Returns:
            The client instance.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close resources."""
        await self.aclose()

    def __repr__(self) -> str:
        """Return a string representation of the client."""
        return f"AppleSearchAdsClient(org_id={self.org_id})"
