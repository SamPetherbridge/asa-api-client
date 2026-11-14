"""Tests for v5 write-path bug fixes (Issue #30)."""

import json
import warnings

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pytest_httpx import HTTPXMock

from asa_api_client.client import AppleSearchAdsClient
from asa_api_client.exceptions import NotFoundError, PartialFailureError
from asa_api_client.models import (
    CampaignUpdate,
    KeywordStatus,
    KeywordUpdate,
    Money,
)

BASE_URL = "https://api.searchads.apple.com/api/v5"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

CAMPAIGN_JSON = {
    "id": 100,
    "orgId": 999,
    "name": "Test Campaign",
    "adamId": 123456789,
    "countriesOrRegions": ["US"],
    "status": "ENABLED",
    "servingStatus": "RUNNING",
    "displayStatus": "RUNNING",
    "supplySources": ["APPSTORE_SEARCH_RESULTS"],
    "dailyBudgetAmount": {"amount": "150", "currency": "USD"},
    "modificationTime": "2026-08-06T00:00:00.000",
}

KEYWORD_JSON = {
    "id": 789,
    "campaignId": 100,
    "adGroupId": 200,
    "text": "productivity",
    "matchType": "EXACT",
    "status": "PAUSED",
    "bidAmount": {"amount": "2.50", "currency": "USD"},
    "modificationTime": "2026-08-06T00:00:00.000",
    "deleted": False,
}


@pytest.fixture(scope="module")
def ec_pem() -> str:
    """Generate a throwaway EC P-256 private key in PEM format."""
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


@pytest.fixture
def v5_client(ec_pem: str) -> AppleSearchAdsClient:
    """Construct a v5 client with deprecation warning suppressed."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return AppleSearchAdsClient(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            org_id=999,
            private_key=ec_pem,
        )


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "tok", "token_type": "Bearer", "expires_in": 3600},
    )


class TestV5CampaignUpdate:
    """Tests for wrapped campaign update payloads."""

    def test_campaign_update_wraps_payload(
        self, httpx_mock: HTTPXMock, v5_client: AppleSearchAdsClient
    ) -> None:
        """PUT /campaigns/{id} nests fields under {'campaign': {...}}."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/100",
            json={"data": CAMPAIGN_JSON, "error": None},
        )
        updated = v5_client.campaigns.update(
            100, CampaignUpdate(daily_budget_amount=Money.usd(150))
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "PUT"
        assert json.loads(request.content) == {
            "campaign": {"dailyBudgetAmount": {"amount": "150", "currency": "USD"}}
        }
        assert updated.id == 100

    async def test_campaign_update_async_wraps_payload(
        self, httpx_mock: HTTPXMock, v5_client: AppleSearchAdsClient
    ) -> None:
        """Async PUT /campaigns/{id} also nests fields under {'campaign': {...}}."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/100",
            json={"data": CAMPAIGN_JSON, "error": None},
        )
        updated = await v5_client.campaigns.update_async(
            100, CampaignUpdate(daily_budget_amount=Money.usd(150))
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "PUT"
        assert json.loads(request.content) == {
            "campaign": {"dailyBudgetAmount": {"amount": "150", "currency": "USD"}}
        }
        assert updated.id == 100


class TestV5KeywordSingleUpdate:
    """Tests for single-keyword update delegating to bulk endpoint."""

    def test_keyword_update_delegates_to_bulk(
        self, httpx_mock: HTTPXMock, v5_client: AppleSearchAdsClient
    ) -> None:
        """KeywordResource.update() calls PUT targetingkeywords/bulk."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/100/adgroups/200/targetingkeywords/bulk",
            json={"data": [KEYWORD_JSON], "pagination": None, "error": None},
        )
        kw = (
            v5_client.campaigns(100)
            .ad_groups(200)
            .keywords.update(789, KeywordUpdate(status=KeywordStatus.PAUSED))
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "PUT"
        assert request.url == f"{BASE_URL}/campaigns/100/adgroups/200/targetingkeywords/bulk"
        assert json.loads(request.content) == [{"id": 789, "status": "PAUSED"}]
        assert kw.id == 789
        assert kw.status == KeywordStatus.PAUSED

    async def test_keyword_update_async_delegates_to_bulk(
        self, httpx_mock: HTTPXMock, v5_client: AppleSearchAdsClient
    ) -> None:
        """KeywordResource.update_async() calls PUT targetingkeywords/bulk."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/100/adgroups/200/targetingkeywords/bulk",
            json={"data": [KEYWORD_JSON], "pagination": None, "error": None},
        )
        kw = await (
            v5_client.campaigns(100)
            .ad_groups(200)
            .keywords.update_async(789, KeywordUpdate(status=KeywordStatus.PAUSED))
        )
        assert kw.id == 789

    def test_keyword_update_empty_response_raises_not_found(
        self, httpx_mock: HTTPXMock, v5_client: AppleSearchAdsClient
    ) -> None:
        """Empty bulk data array raises NotFoundError instead of IndexError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/100/adgroups/200/targetingkeywords/bulk",
            json={"data": [], "pagination": None, "error": None},
        )
        with pytest.raises(NotFoundError):
            v5_client.campaigns(100).ad_groups(200).keywords.update(
                789, KeywordUpdate(status=KeywordStatus.PAUSED)
            )


class TestV5PartialErrorOn200:
    """Tests for surfacing HTTP 200 error blocks in v5 responses."""

    def test_bulk_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v5_client: AppleSearchAdsClient
    ) -> None:
        """HTTP 200 with error.errors raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/100/adgroups/200/targetingkeywords/bulk",
            json={
                "data": [],
                "pagination": None,
                "error": {
                    "errors": [
                        {
                            "messageCode": "NOT_SAME_CURRENCY_AS_ORG_CURRENCY",
                            "message": "Bid currency AUD does not match org currency USD",
                            "field": "bidAmount.currency",
                        }
                    ]
                },
            },
        )
        with pytest.raises(PartialFailureError, match="does not match org currency") as exc_info:
            v5_client.campaigns(100).ad_groups(200).keywords.update_bulk(
                [(789, KeywordUpdate(bid_amount=Money(amount="2.00", currency="AUD")))]
            )
        assert exc_info.value.status_code == 200
        assert exc_info.value.details[0]["messageCode"] == "NOT_SAME_CURRENCY_AS_ORG_CURRENCY"

    async def test_async_bulk_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v5_client: AppleSearchAdsClient
    ) -> None:
        """Async HTTP 200 with error.errors also raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/100/adgroups/200/targetingkeywords/bulk",
            json={
                "data": [],
                "pagination": None,
                "error": {
                    "errors": [
                        {
                            "messageCode": "NOT_SAME_CURRENCY_AS_ORG_CURRENCY",
                            "message": "Currency mismatch",
                            "field": "bidAmount.currency",
                        }
                    ]
                },
            },
        )
        with pytest.raises(PartialFailureError, match="Currency mismatch"):
            await (
                v5_client.campaigns(100)
                .ad_groups(200)
                .keywords.update_bulk_async(
                    [(789, KeywordUpdate(bid_amount=Money(amount="2.00", currency="AUD")))]
                )
            )
