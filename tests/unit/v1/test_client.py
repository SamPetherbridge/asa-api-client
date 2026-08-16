"""Tests for the AppleAdsClient."""

from typing import ClassVar

import pytest

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
