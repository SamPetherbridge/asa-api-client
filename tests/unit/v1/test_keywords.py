"""Tests for the v1 keywords and negative keywords resources."""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.keywords import (
    Keyword,
    KeywordCreate,
    KeywordDisplayStatus,
    KeywordMatchType,
    KeywordStatus,
    KeywordUpdate,
    NegativeKeyword,
    NegativeKeywordCreate,
    NegativeKeywordStatus,
    NegativeKeywordUpdate,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.keywords import (
    KeywordResource,
    NegativeKeywordResource,
)

BASE_URL = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

KEYWORD_JSON = {
    "adAccountId": 999,
    "campaignId": 100,
    "adGroupId": 200,
    "text": "coffee",
    "matchType": "EXACT",
    "bid": {"amount": "1.50", "currency": "USD"},
    "status": "ENABLED",
    "id": 300,
    "creationTime": "2026-01-01T00:00:00.000Z",
    "modificationTime": "2026-01-02T00:00:00.000Z",
    "deleted": False,
    "displayStatus": "RUNNING",
}

NEGATIVE_KEYWORD_JSON = {
    "adAccountId": 999,
    "campaignId": 100,
    "text": "free",
    "matchType": "BROAD",
    "status": "ENABLED",
    "id": 400,
    "creationTime": "2026-01-01T00:00:00.000Z",
    "modificationTime": "2026-01-02T00:00:00.000Z",
    "deleted": False,
}


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


class TestKeywordResource:
    """Tests for KeywordResource endpoints."""

    def test_create_keyword_posts_bare_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() POSTs an unwrapped, aliased KeywordCreate body."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/keywords", json={"result": KEYWORD_JSON})
        keyword = KeywordResource(v1_client).create(
            KeywordCreate(
                ad_group_id=200,
                text="coffee",
                match_type=KeywordMatchType.EXACT,
                bid=Money.usd("1.50"),
                status=KeywordStatus.ENABLED,
            )
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "adGroupId": 200,
            "text": "coffee",
            "matchType": "EXACT",
            "bid": {"amount": "1.50", "currency": "USD"},
            "status": "ENABLED",
        }
        assert keyword.id == 300
        assert keyword.bid == Money(amount="1.50", currency="USD")

    def test_create_keyword_omits_unset_bid(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() omits bid entirely to default to the ad group bid."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/keywords", json={"result": KEYWORD_JSON})
        KeywordResource(v1_client).create(KeywordCreate(ad_group_id=200, text="coffee"))
        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "adGroupId": 200,
            "text": "coffee",
        }

    def test_get_keyword_parses_full_model(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get() hits GET /keywords/{id} and parses every field."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/keywords/300", json={"result": KEYWORD_JSON})
        keyword = KeywordResource(v1_client).get(300)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert keyword.ad_account_id == 999
        assert keyword.campaign_id == 100
        assert keyword.ad_group_id == 200
        assert keyword.text == "coffee"
        assert keyword.match_type is KeywordMatchType.EXACT
        assert keyword.status is KeywordStatus.ENABLED
        assert keyword.display_status is KeywordDisplayStatus.RUNNING
        assert keyword.deleted is False

    def test_get_deleted_keyword_still_parses(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test soft-deleted keywords come back with deleted=True, not 404."""
        deleted_json = {**KEYWORD_JSON, "deleted": True, "displayStatus": "DELETED"}
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/keywords/300", json={"result": deleted_json})
        keyword = KeywordResource(v1_client).get(300)
        assert keyword.deleted is True
        assert keyword.display_status is KeywordDisplayStatus.DELETED

    def test_query_keywords_posts_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() POSTs the filter body to /keywords/query and parses the page."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/query",
            json={
                "result": [KEYWORD_JSON],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            },
        )
        page = KeywordResource(v1_client).query(
            Query().where("adGroupId", "EQUALS", 200).page(size=10)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "adGroupId", "operator": "EQUALS", "value": 200}],
            "pagination": {"pageSize": 10},
        }
        assert len(page) == 1
        assert page[0].id == 300
        assert page.has_more is False

    def test_update_keyword_puts_bid_and_status(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() PUTs only bid and status as a bare body."""
        updated_json = {**KEYWORD_JSON, "status": "PAUSED"}
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/keywords/300", json={"result": updated_json})
        keyword = KeywordResource(v1_client).update(
            300, KeywordUpdate(bid=Money.usd("2.00"), status=KeywordStatus.PAUSED)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "PUT"
        assert json.loads(request.content) == {
            "bid": {"amount": "2.00", "currency": "USD"},
            "status": "PAUSED",
        }
        assert keyword.status is KeywordStatus.PAUSED

    def test_delete_keyword(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test delete() sends DELETE /keywords/{id} and returns None."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/keywords/300", json={})
        KeywordResource(v1_client).delete(300)
        assert httpx_mock.get_requests()[-1].method == "DELETE"

    def test_keyword_200_with_error_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an HTTP 200 carrying an error block raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords",
            json={
                "result": None,
                "error": {
                    "code": "INVALID_KEYWORD",
                    "message": "keyword rejected",
                    "details": [{"code": "DUPLICATE_KEYWORD", "message": "already exists"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            KeywordResource(v1_client).create(KeywordCreate(ad_group_id=200, text="coffee"))
        assert exc_info.value.details[0]["code"] == "DUPLICATE_KEYWORD"

    def test_match_type_enum_round_trip(self) -> None:
        """Test KeywordMatchType survives a serialize/parse round trip."""
        keyword = Keyword.model_validate({"id": 1, "matchType": "CATEGORY"})
        assert keyword.match_type is KeywordMatchType.CATEGORY
        dumped = keyword.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["matchType"] == "CATEGORY"
        assert Keyword.model_validate(dumped).match_type is KeywordMatchType.CATEGORY

    def test_display_status_enum_values(self) -> None:
        """Test KeywordDisplayStatus exposes every documented value."""
        assert {status.value for status in KeywordDisplayStatus} == {
            "RUNNING",
            "PAUSED",
            "DELETED",
            "AD_GROUP_ON_HOLD",
            "CAMPAIGN_ON_HOLD",
        }


class TestNegativeKeywordResource:
    """Tests for NegativeKeywordResource endpoints."""

    def test_create_campaign_level_negative(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() sends campaignId only for a campaign-level negative."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords", json={"result": NEGATIVE_KEYWORD_JSON}
        )
        negative = NegativeKeywordResource(v1_client).create(
            NegativeKeywordCreate(campaign_id=100, text="free")
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {"campaignId": 100, "text": "free"}
        assert negative.id == 400
        assert negative.ad_group_id is None

    def test_create_ad_group_level_negative(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() sends adGroupId (no campaignId) for an ad-group negative."""
        response_json = {**NEGATIVE_KEYWORD_JSON, "adGroupId": 200}
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/negative-keywords", json={"result": response_json})
        negative = NegativeKeywordResource(v1_client).create(
            NegativeKeywordCreate(
                ad_group_id=200,
                text="free",
                match_type=KeywordMatchType.EXACT,
                status=NegativeKeywordStatus.ENABLED,
            )
        )
        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "adGroupId": 200,
            "text": "free",
            "matchType": "EXACT",
            "status": "ENABLED",
        }
        assert negative.ad_group_id == 200

    def test_get_negative_keyword(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() parses a campaign-level negative without adGroupId."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/400", json={"result": NEGATIVE_KEYWORD_JSON}
        )
        negative = NegativeKeywordResource(v1_client).get(400)
        assert httpx_mock.get_requests()[-1].method == "GET"
        assert negative.campaign_id == 100
        assert negative.ad_group_id is None
        assert negative.match_type is KeywordMatchType.BROAD
        assert negative.status is NegativeKeywordStatus.ENABLED

    def test_query_negative_keywords_with_is_null_filter(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() serializes the valueless IS_NULL adGroupId filter."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/query",
            json={
                "result": [NEGATIVE_KEYWORD_JSON],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = NegativeKeywordResource(v1_client).query(
            Query().where("adGroupId", "IS_NULL").where("campaignId", "EQUALS", 100)
        )
        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "filters": [
                {"field": "adGroupId", "operator": "IS_NULL"},
                {"field": "campaignId", "operator": "EQUALS", "value": 100},
            ]
        }
        assert page[0].text == "free"

    def test_update_negative_keyword_status_only(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() PUTs a status-only bare body."""
        updated_json = {**NEGATIVE_KEYWORD_JSON, "status": "PAUSED"}
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/400", json={"result": updated_json}
        )
        negative = NegativeKeywordResource(v1_client).update(
            400, NegativeKeywordUpdate(status=NegativeKeywordStatus.PAUSED)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "PUT"
        assert json.loads(request.content) == {"status": "PAUSED"}
        assert negative.status is NegativeKeywordStatus.PAUSED

    def test_delete_negative_keyword(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test delete() sends DELETE /negative-keywords/{id}."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/negative-keywords/400", json={})
        NegativeKeywordResource(v1_client).delete(400)
        assert httpx_mock.get_requests()[-1].method == "DELETE"

    def test_negative_200_with_error_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx negative-keyword response with an error block raises."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/400",
            json={"result": None, "error": {"code": "FAILED", "message": "nope"}},
        )
        with pytest.raises(PartialFailureError):
            NegativeKeywordResource(v1_client).get(400)

    def test_negative_status_enum_round_trip(self) -> None:
        """Test NegativeKeywordStatus survives a serialize/parse round trip."""
        negative = NegativeKeyword.model_validate({"id": 1, "status": "PAUSED"})
        assert negative.status is NegativeKeywordStatus.PAUSED
        dumped = negative.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["status"] == "PAUSED"
        assert NegativeKeyword.model_validate(dumped).status is NegativeKeywordStatus.PAUSED
