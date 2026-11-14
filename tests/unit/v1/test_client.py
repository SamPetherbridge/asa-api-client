"""Tests for the AppleAdsClient."""

import asyncio
from typing import ClassVar

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.auth import TOKEN_URL
from asa_api_client.exceptions import ConfigurationError
from asa_api_client.v1.client import DEFAULT_V1_BASE_URL, AppleAdsClient


def make_client(ec_private_key_pem: str, **kwargs: object) -> AppleAdsClient:
    """Build a client with dummy credentials and overrides."""
    params: dict[str, object] = {
        "client_id": "SEARCHADS.test",
        "team_id": "TEAM123",
        "key_id": "KEY123",
        "private_key": ec_private_key_pem,
    }
    params.update(kwargs)
    return AppleAdsClient(**params)  # type: ignore[arg-type]


class TestConstruction:
    """Tests for client construction."""

    def test_defaults(self, ec_private_key_pem: str) -> None:
        """Test the default base URL and unset account."""
        client = make_client(ec_private_key_pem)
        assert client._base_url == DEFAULT_V1_BASE_URL
        assert client.ad_account_id is None

    def test_ad_account_id_normalized_to_str(self, ec_private_key_pem: str) -> None:
        """Test integer account IDs normalize to strings."""
        client = make_client(ec_private_key_pem, ad_account_id=12345)
        assert client.ad_account_id == "12345"

    def test_base_url_trailing_slash_stripped(self, ec_private_key_pem: str) -> None:
        """Test trailing slashes are removed from base_url."""
        client = make_client(ec_private_key_pem, base_url="https://api.ads.apple.com/v1/")
        assert client._base_url == "https://api.ads.apple.com/v1"

    def test_ad_account_id_settable_after_construction(self, ec_private_key_pem: str) -> None:
        """Test the bootstrap flow: discover accounts, then set the ID."""
        client = make_client(ec_private_key_pem)
        client.ad_account_id = "999"
        assert client.ad_account_id == "999"

    def test_repr_includes_account(self, ec_private_key_pem: str) -> None:
        """Test repr mentions the ad account."""
        client = make_client(ec_private_key_pem, ad_account_id="42")
        assert "42" in repr(client)


class TestRootExport:
    """Tests for the public import surface."""

    def test_importable_from_package_root(self) -> None:
        """Test the root-exports-only public API rule."""
        from asa_api_client import AppleAdsClient as RootClient

        assert RootClient is AppleAdsClient


class TestFromEnv:
    """Tests for from_env construction."""

    def test_from_env_reads_ad_account_id(
        self, monkeypatch: pytest.MonkeyPatch, ec_private_key_pem: str
    ) -> None:
        """Test ASA_AD_ACCOUNT_ID is picked up from the environment."""
        monkeypatch.setenv("ASA_CLIENT_ID", "SEARCHADS.test")
        monkeypatch.setenv("ASA_TEAM_ID", "TEAM123")
        monkeypatch.setenv("ASA_KEY_ID", "KEY123")
        monkeypatch.setenv("ASA_ORG_ID", "111")
        monkeypatch.setenv("ASA_PRIVATE_KEY", ec_private_key_pem)
        monkeypatch.setenv("ASA_AD_ACCOUNT_ID", "67890")

        client = AppleAdsClient.from_env(env_file=None)
        assert client.ad_account_id == "67890"

    def test_from_env_without_ad_account_id(
        self, monkeypatch: pytest.MonkeyPatch, ec_private_key_pem: str
    ) -> None:
        """Test from_env works with no account configured (bootstrap)."""
        monkeypatch.setenv("ASA_CLIENT_ID", "SEARCHADS.test")
        monkeypatch.setenv("ASA_TEAM_ID", "TEAM123")
        monkeypatch.setenv("ASA_KEY_ID", "KEY123")
        monkeypatch.setenv("ASA_ORG_ID", "111")
        monkeypatch.setenv("ASA_PRIVATE_KEY", ec_private_key_pem)
        monkeypatch.delenv("ASA_AD_ACCOUNT_ID", raising=False)

        client = AppleAdsClient.from_env(env_file=None)
        assert client.ad_account_id is None


class TestResourceWiring:
    """Tests that every v1 resource is reachable from the client."""

    EXPECTED: ClassVar[dict[str, str]] = {
        "campaigns": "CampaignResource",
        "ad_accounts": "AdAccountResource",
        "acls": "AclResource",
        "orgs": "OrgResource",
        "advertiser_resources": "AdvertiserResourceResource",
        "ad_groups": "AdGroupResource",
        "keywords": "KeywordResource",
        "negative_keywords": "NegativeKeywordResource",
        "ads": "AdResource",
        "creatives": "CreativeResource",
        "assets": "AssetResource",
        "product_pages": "ProductPageResource",
        "budget_orders": "BudgetOrderResource",
        "apps": "AppResource",
        "geo": "GeoResource",
        "brands": "BrandResource",
        "business_categories": "BusinessCategoryResource",
        "brand_rejection_reasons": "BrandRejectionReasonResource",
        "locations": "LocationResource",
        "location_groups": "LocationGroupResource",
        "reports": "ReportResource",
        "brand_reports": "BrandReportResource",
        "insights": "InsightResource",
        "suggestions": "SuggestionResource",
        "recommendations": "RecommendationResource",
        "change_history": "ChangeHistoryResource",
        "bulk": "BulkOperationResource",
    }

    def test_every_property_returns_its_resource(self, ec_private_key_pem: str) -> None:
        """Test each documented property yields the right resource class."""
        client = make_client(ec_private_key_pem)
        for prop, class_name in self.EXPECTED.items():
            resource = getattr(client, prop)
            assert type(resource).__name__ == class_name, prop

    def test_resources_are_cached(self, ec_private_key_pem: str) -> None:
        """Test repeated property access returns the same instance."""
        client = make_client(ec_private_key_pem)
        assert client.campaigns is client.campaigns
        assert client.reports is client.reports


class TestLifecycle:
    """Tests for context managers and cleanup."""

    def test_sync_context_manager_closes(self, ec_private_key_pem: str) -> None:
        """Test the sync context manager closes cleanly."""
        with make_client(ec_private_key_pem) as client:
            client._get_http_client()
        assert client._http_client is None

    async def test_async_context_manager_closes(self, ec_private_key_pem: str) -> None:
        """Test the async context manager closes cleanly."""
        async with make_client(ec_private_key_pem) as client:
            client._get_async_http_client()
        assert client._async_http_client is None


class TestRetryConfig:
    """Tests for configurable client retry parameters."""

    def test_custom_retry_options_stored_on_client(self, ec_private_key_pem: str) -> None:
        """Test retry options pass through to the client and resource views."""
        client = make_client(
            ec_private_key_pem,
            max_retries=2,
            retry_initial_delay=1.5,
            retry_max_delay=30.0,
            retry_jitter=False,
        )
        assert client.max_retries == 2
        assert client.retry_initial_delay == 1.5
        assert client.retry_max_delay == 30.0
        assert client.retry_jitter is False
        assert client.campaigns._max_retries == 2

    def test_negative_retry_raises_configuration_error(self, ec_private_key_pem: str) -> None:
        """Test negative retry parameters raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="max_retries"):
            make_client(ec_private_key_pem, max_retries=-1)
        with pytest.raises(ConfigurationError, match="retry_initial_delay"):
            make_client(ec_private_key_pem, retry_initial_delay=-0.5)


class TestMultiAccountScoping:
    """Tests for with_account() and resolve_ad_account()."""

    async def test_with_account_isolates_headers_and_shares_transport(
        self, httpx_mock: HTTPXMock, ec_private_key_pem: str
    ) -> None:
        """Concurrent scoped views send distinct X-AP-Context headers and share auth/HTTP."""
        httpx_mock.add_response(
            url=TOKEN_URL,
            json={"access_token": "shared-tok", "token_type": "Bearer", "expires_in": 3600},
        )
        httpx_mock.add_response(
            url=f"{DEFAULT_V1_BASE_URL}/campaigns/query",
            json={"result": []},
            is_reusable=True,
        )

        async with make_client(ec_private_key_pem, ad_account_id="100") as root:
            with root.with_account("200") as acct_a:
                assert acct_a._authenticator is root._authenticator
            # Exiting scoped context manager must not close parent's HTTP pools
            root_async = root._get_async_http_client()
            async with root.with_account("200") as acct_200, root.with_account("300") as acct_300:
                await asyncio.gather(
                    acct_200.campaigns.query_async(),
                    acct_300.campaigns.query_async(),
                )
            assert not root_async.is_closed
            assert root.ad_account_id == "100"

        assert len(httpx_mock.get_requests(url=TOKEN_URL)) == 1
        contexts = {
            req.headers["X-AP-Context"]
            for req in httpx_mock.get_requests(url=f"{DEFAULT_V1_BASE_URL}/campaigns/query")
        }
        assert contexts == {"adAccountId=200", "adAccountId=300"}

    def test_resolve_ad_account_single_and_preferred(
        self, httpx_mock: HTTPXMock, ec_private_key_pem: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """resolve_ad_account discovers sole account or prefers prefer_org_id / ASA_ORG_ID."""
        monkeypatch.delenv("ASA_ORG_ID", raising=False)
        httpx_mock.add_response(
            url=TOKEN_URL,
            json={"access_token": "tok", "token_type": "Bearer", "expires_in": 3600},
            is_reusable=True,
        )
        httpx_mock.add_response(
            url=f"{DEFAULT_V1_BASE_URL}/acls",
            json={
                "result": {
                    "acls": [
                        {"adAccount": {"id": 10, "name": "First"}, "roles": ["Admin"]},
                        {"adAccount": {"id": 20, "name": "Second"}, "roles": ["Admin"]},
                    ]
                }
            },
        )
        client = make_client(ec_private_key_pem)
        resolved = client.resolve_ad_account(prefer_org_id=20)
        assert resolved == "20"
        assert client.ad_account_id == "20"
        # Subsequent call is a no-op returning the already-set account ID
        assert client.resolve_ad_account() == "20"

    async def test_resolve_ad_account_async_sole_account(
        self, httpx_mock: HTTPXMock, ec_private_key_pem: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """resolve_ad_account_async selects the sole accessible account."""
        monkeypatch.delenv("ASA_ORG_ID", raising=False)
        httpx_mock.add_response(
            url=TOKEN_URL,
            json={"access_token": "tok", "token_type": "Bearer", "expires_in": 3600},
        )
        httpx_mock.add_response(
            url=f"{DEFAULT_V1_BASE_URL}/acls",
            json={"result": {"acls": [{"adAccount": {"id": 777, "name": "Only"}, "roles": []}]}},
        )
        async with make_client(ec_private_key_pem) as client:
            resolved = await client.resolve_ad_account_async()
            assert resolved == "777"
            assert client.ad_account_id == "777"
