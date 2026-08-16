"""Main client for the Apple Ads Platform API v1.

This module provides the AppleAdsClient class, the primary interface
for the Apple Ads Platform API v1 (``https://api.ads.apple.com/v1``),
which replaces the Campaign Management API v5 (sunset 2027-01-26).

Authentication is unchanged from v5, so the same credentials work for
both clients. The v1 API scopes requests to an *ad account* via the
``X-AP-Context: adAccountId=...`` header instead of v5's ``orgId``.
"""

from pathlib import Path
from types import TracebackType
from typing import Self

import httpx
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from asa_api_client.auth import Authenticator
from asa_api_client.exceptions import ConfigurationError
from asa_api_client.logging import get_logger

logger = get_logger(__name__)

# API base URL
DEFAULT_V1_BASE_URL = "https://api.ads.apple.com/v1"


class _V1EnvSettings(BaseSettings):
    """Environment settings for the v1 client.

    Reads the same ``ASA_*`` variables as the v5 client, plus
    ``ASA_AD_ACCOUNT_ID``. ``ASA_ORG_ID`` is optional here: v1 requests
    are scoped by ad account, not organization.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASA_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    client_id: str
    team_id: str
    key_id: str
    org_id: int = 0
    ad_account_id: str | None = None
    private_key: SecretStr | None = None
    private_key_path: Path | None = None


class AppleAdsClient:
    """Client for the Apple Ads Platform API v1.

    Provides access to all v1 API resources through a structured,
    resource-based interface. Supports both synchronous and
    asynchronous operations (async methods use the ``_async`` suffix).

    The ``ad_account_id`` may be omitted at construction to bootstrap:
    account-management endpoints (``client.me()``, ``client.acls``)
    work without it, and it can be assigned afterwards. Account-scoped
    resources raise ``ConfigurationError`` until it is set.

    Attributes:
        ad_account_id: The Apple Ads ad account ID for request scoping.

    Example:
        Basic usage::

            from asa_api_client import AppleAdsClient

            client = AppleAdsClient(
                client_id="SEARCHADS.abc123",
                team_id="TEAM123",
                key_id="KEY123",
                ad_account_id="123456",
                private_key_path="path/to/private-key.pem",
            )

            campaigns = client.campaigns.query()
            for campaign in campaigns:
                print(f"{campaign.name}: {campaign.status}")

        From environment variables (``ASA_*`` plus ``ASA_AD_ACCOUNT_ID``)::

            client = AppleAdsClient.from_env()

        Bootstrap without a known ad account::

            client = AppleAdsClient.from_env()
            acls = client.acls.list()
            client.ad_account_id = str(acls[0].ad_account_id)
    """

    def __init__(
        self,
        *,
        client_id: str,
        team_id: str,
        key_id: str,
        ad_account_id: str | int | None = None,
        org_id: int | None = None,
        private_key: str | None = None,
        private_key_path: Path | str | None = None,
        base_url: str = DEFAULT_V1_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Apple Ads Platform API v1 client.

        You must provide either `private_key` or `private_key_path`.

        Args:
            client_id: Your Apple Ads API client ID.
            team_id: Your Apple Developer team ID.
            key_id: The key ID for your private key.
            ad_account_id: The ad account ID for request scoping. May be
                omitted for bootstrap (account discovery) and set later.
            org_id: Optional v5 organization ID; not used by v1 requests
                but recorded on the shared authenticator.
            private_key: The private key as a PEM-encoded string.
            private_key_path: Path to the private key PEM file.
            base_url: The API base URL. Defaults to the v1 API.
            timeout: Request timeout in seconds.

        Raises:
            ConfigurationError: If credentials are invalid or missing.
        """
        self.ad_account_id = str(ad_account_id) if ad_account_id is not None else None
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

        self._authenticator = Authenticator(
            client_id=client_id,
            team_id=team_id,
            key_id=key_id,
            org_id=org_id or 0,
            private_key=private_key,
            private_key_path=private_key_path,
        )

        # HTTP clients (created lazily)
        self._http_client: httpx.Client | None = None
        self._async_http_client: httpx.AsyncClient | None = None

        logger.info(
            "AppleAdsClient initialized for ad_account_id=%s, base_url=%s",
            self.ad_account_id,
            base_url,
        )

    @classmethod
    def from_env(
        cls,
        *,
        env_file: str | Path | None = ".env",
        base_url: str = DEFAULT_V1_BASE_URL,
        timeout: float = 30.0,
    ) -> Self:
        """Create a client from environment variables and .env file.

        Required settings (via env vars or .env file):
        - ASA_CLIENT_ID
        - ASA_TEAM_ID
        - ASA_KEY_ID
        - ASA_PRIVATE_KEY or ASA_PRIVATE_KEY_PATH

        Optional settings:
        - ASA_AD_ACCOUNT_ID (omit to bootstrap via account discovery)
        - ASA_ORG_ID (v5 compatibility; unused by v1 requests)

        Args:
            env_file: Path to .env file to load. Set to None to skip
                loading from file. Defaults to ".env".
            base_url: The API base URL.
            timeout: Request timeout in seconds.

        Returns:
            A configured AppleAdsClient instance.

        Raises:
            ConfigurationError: If required settings are missing or invalid.
        """
        from pydantic import ValidationError as PydanticValidationError

        try:
            settings = _V1EnvSettings(_env_file=env_file)
        except PydanticValidationError as e:
            errors = e.errors()
            if errors:
                first_error = errors[0]
                loc = first_error.get("loc") or ()
                msg = first_error.get("msg", "validation error")
                if loc:
                    raise ConfigurationError(
                        f"Configuration error for ASA_{str(loc[0]).upper()}: {msg}"
                    ) from e
                raise ConfigurationError(f"Configuration error: {msg}") from e
            raise ConfigurationError(f"Configuration error: {e}") from e

        return cls(
            client_id=settings.client_id,
            team_id=settings.team_id,
            key_id=settings.key_id,
            ad_account_id=settings.ad_account_id,
            org_id=settings.org_id or None,
            private_key=(settings.private_key.get_secret_value() if settings.private_key else None),
            private_key_path=settings.private_key_path,
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
        return f"AppleAdsClient(ad_account_id={self.ad_account_id})"
