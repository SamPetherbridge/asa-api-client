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
from asa_api_client.v1.resources.ad_accounts import (
    AclResource,
    AdAccountResource,
    AdvertiserResourceResource,
    OrgResource,
)
from asa_api_client.v1.resources.ad_groups import AdGroupResource
from asa_api_client.v1.resources.ads import AdResource
from asa_api_client.v1.resources.apps import AppResource
from asa_api_client.v1.resources.brands import (
    BrandRejectionReasonResource,
    BrandResource,
    BusinessCategoryResource,
    LocationGroupResource,
    LocationResource,
)
from asa_api_client.v1.resources.budget_orders import BudgetOrderResource
from asa_api_client.v1.resources.bulk import BulkOperationResource
from asa_api_client.v1.resources.campaigns import CampaignResource
from asa_api_client.v1.resources.change_history import ChangeHistoryResource
from asa_api_client.v1.resources.creatives import AssetResource, CreativeResource
from asa_api_client.v1.resources.geo import GeoResource
from asa_api_client.v1.resources.insights import InsightResource
from asa_api_client.v1.resources.keywords import KeywordResource, NegativeKeywordResource
from asa_api_client.v1.resources.product_pages import ProductPageResource
from asa_api_client.v1.resources.recommendations import RecommendationResource
from asa_api_client.v1.resources.reports import BrandReportResource, ReportResource
from asa_api_client.v1.resources.suggestions import SuggestionResource

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

        # Initialize resources
        self._campaigns = CampaignResource(self)
        self._ad_accounts = AdAccountResource(self)
        self._acls = AclResource(self)
        self._orgs = OrgResource(self)
        self._advertiser_resources = AdvertiserResourceResource(self)
        self._ad_groups = AdGroupResource(self)
        self._keywords = KeywordResource(self)
        self._negative_keywords = NegativeKeywordResource(self)
        self._ads = AdResource(self)
        self._creatives = CreativeResource(self)
        self._assets = AssetResource(self)
        self._product_pages = ProductPageResource(self)
        self._budget_orders = BudgetOrderResource(self)
        self._apps = AppResource(self)
        self._geo = GeoResource(self)
        self._brands = BrandResource(self)
        self._business_categories = BusinessCategoryResource(self)
        self._brand_rejection_reasons = BrandRejectionReasonResource(self)
        self._locations = LocationResource(self)
        self._location_groups = LocationGroupResource(self)
        self._reports = ReportResource(self)
        self._brand_reports = BrandReportResource(self)
        self._insights = InsightResource(self)
        self._suggestions = SuggestionResource(self)
        self._recommendations = RecommendationResource(self)
        self._change_history = ChangeHistoryResource(self)
        self._bulk = BulkOperationResource(self)

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

    @property
    def campaigns(self) -> CampaignResource:
        """Campaigns resource (App Store and Apple Maps campaigns).

        Example:
            List enabled campaigns::

                from asa_api_client.v1 import Query

                page = client.campaigns.query(
                    Query().where("status", "EQUALS", "ENABLED")
                )
        """
        return self._campaigns

    @property
    def ad_accounts(self) -> AdAccountResource:
        """Ad accounts resource; also carries ``me()`` for the current user."""
        return self._ad_accounts

    @property
    def acls(self) -> AclResource:
        """User ACLs resource — enumerates accessible ad accounts."""
        return self._acls

    @property
    def orgs(self) -> OrgResource:
        """Organizations resource (v5-compatible org lookups)."""
        return self._orgs

    @property
    def advertiser_resources(self) -> AdvertiserResourceResource:
        """Advertiser resources (delegations) resource."""
        return self._advertiser_resources

    @property
    def ad_groups(self) -> AdGroupResource:
        """Ad groups resource."""
        return self._ad_groups

    @property
    def keywords(self) -> KeywordResource:
        """Targeting keywords resource."""
        return self._keywords

    @property
    def negative_keywords(self) -> NegativeKeywordResource:
        """Negative keywords resource."""
        return self._negative_keywords

    @property
    def ads(self) -> AdResource:
        """Ads resource."""
        return self._ads

    @property
    def creatives(self) -> CreativeResource:
        """Ad creatives resource."""
        return self._creatives

    @property
    def assets(self) -> AssetResource:
        """Creative assets resource (upload, query)."""
        return self._assets

    @property
    def product_pages(self) -> ProductPageResource:
        """Custom product pages resource (read-only)."""
        return self._product_pages

    @property
    def budget_orders(self) -> BudgetOrderResource:
        """Shared budgets (budget orders) resource."""
        return self._budget_orders

    @property
    def apps(self) -> AppResource:
        """App search, details, eligibility, and rejection reasons."""
        return self._apps

    @property
    def geo(self) -> GeoResource:
        """Geo targeting search resource."""
        return self._geo

    @property
    def brands(self) -> BrandResource:
        """Apple Maps ads brands resource."""
        return self._brands

    @property
    def business_categories(self) -> BusinessCategoryResource:
        """Apple Maps ads business categories resource."""
        return self._business_categories

    @property
    def brand_rejection_reasons(self) -> BrandRejectionReasonResource:
        """Apple Maps ads brand rejection reasons resource."""
        return self._brand_rejection_reasons

    @property
    def locations(self) -> LocationResource:
        """Apple Maps ads locations resource."""
        return self._locations

    @property
    def location_groups(self) -> LocationGroupResource:
        """Apple Maps ads location groups resource."""
        return self._location_groups

    @property
    def reports(self) -> ReportResource:
        """App Store campaign reports (all levels).

        Example:
            Campaign-level report::

                report = client.reports.campaigns(request)
        """
        return self._reports

    @property
    def brand_reports(self) -> BrandReportResource:
        """Apple Maps ads (business brands) reports."""
        return self._brand_reports

    @property
    def insights(self) -> InsightResource:
        """Insights: impression share and search term popularity.

        Example:
            Search term popularity::

                rows = client.insights.query_search_term_popularity(request)
        """
        return self._insights

    @property
    def suggestions(self) -> SuggestionResource:
        """Keyword/phrase/category and target-CPA suggestions."""
        return self._suggestions

    @property
    def recommendations(self) -> RecommendationResource:
        """Target-CPA and daily-budget recommendations (query/apply/dismiss)."""
        return self._recommendations

    @property
    def change_history(self) -> ChangeHistoryResource:
        """Change history (audit) resource."""
        return self._change_history

    @property
    def bulk(self) -> BulkOperationResource:
        """Bulk operations for keywords and negative keywords."""
        return self._bulk

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
