"""Tests for the v1 bulk operations resource."""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.bulk import (
    BulkKeywordCreate,
    BulkKeywordUpdate,
    BulkNegativeKeywordCreate,
    BulkNegativeKeywordUpdate,
    BulkOperation,
    BulkRequestItem,
)
from asa_api_client.v1.models.keywords import (
    KeywordMatchType,
    KeywordStatus,
    NegativeKeywordStatus,
)
from asa_api_client.v1.resources.bulk import BulkOperationResource

BASE_URL = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

KEYWORD_JSON = {
    "id": 300,
    "adAccountId": 999,
    "campaignId": 100,
    "adGroupId": 200,
    "text": "coffee",
    "matchType": "EXACT",
    "bid": {"amount": "1.50", "currency": "USD"},
    "status": "ENABLED",
    "displayStatus": "RUNNING",
    "deleted": False,
    "creationTime": "2025-06-01T10:00:00.000",
    "modificationTime": "2025-06-01T10:00:00.000",
}

NEGATIVE_KEYWORD_JSON = {
    "id": 400,
    "adAccountId": 999,
    "campaignId": 100,
    "adGroupId": None,
    "text": "free",
    "matchType": "BROAD",
    "status": "ENABLED",
    "deleted": False,
    "creationTime": "2025-06-01T10:00:00.000",
    "modificationTime": "2025-06-01T10:00:00.000",
}


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


class TestBulkKeywordCreate:
    """Tests for POST /v1/keywords/bulk-create."""

    def test_create_keywords_posts_bulk_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create_keywords() POSTs {allowPartialSuccess, items} with data wrappers."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-create",
            json={
                "result": [
                    {
                        "correlationId": 1,
                        "operation": "CREATE",
                        "success": True,
                        "result": KEYWORD_JSON,
                        "error": None,
                    }
                ],
                "error": None,
            },
        )
        results = BulkOperationResource(v1_client).create_keywords(
            [
                BulkKeywordCreate(
                    ad_group_id=200,
                    text="coffee",
                    match_type=KeywordMatchType.EXACT,
                    bid=Money.usd("1.50"),
                    status=KeywordStatus.ENABLED,
                )
            ]
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.url == f"{BASE_URL}/keywords/bulk-create"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(request.content) == {
            "allowPartialSuccess": False,
            "items": [
                {
                    "correlationId": 1,
                    "data": {
                        "adGroupId": 200,
                        "text": "coffee",
                        "matchType": "EXACT",
                        "bid": {"amount": "1.50", "currency": "USD"},
                        "status": "ENABLED",
                    },
                }
            ],
        }
        assert len(results) == 1
        assert results[0].correlation_id == 1
        assert results[0].operation is BulkOperation.CREATE
        assert results[0].success is True
        assert results[0].error is None
        keyword = results[0].result
        assert keyword is not None
        assert keyword.id == 300
        assert keyword.match_type is KeywordMatchType.EXACT
        assert keyword.bid == Money(amount="1.50", currency="USD")

    def test_create_keywords_with_explicit_items(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test explicit BulkRequestItem correlation IDs pass through verbatim."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-create",
            json={"result": [], "error": None},
        )
        BulkOperationResource(v1_client).create_keywords(
            [
                BulkRequestItem(
                    correlation_id=42,
                    data=BulkKeywordCreate(ad_group_id=200, text="tea"),
                )
            ],
            allow_partial_success=True,
        )
        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "allowPartialSuccess": True,
            "items": [{"correlationId": 42, "data": {"adGroupId": 200, "text": "tea"}}],
        }

    async def test_create_keywords_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async variant hits the same endpoint and parses results."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-create",
            json={
                "result": [
                    {
                        "correlationId": 1,
                        "operation": "CREATE",
                        "success": True,
                        "result": KEYWORD_JSON,
                        "error": None,
                    }
                ],
                "error": None,
            },
        )
        results = await BulkOperationResource(v1_client).create_keywords_async(
            [BulkKeywordCreate(ad_group_id=200, text="coffee")]
        )
        assert httpx_mock.get_requests()[-1].method == "POST"
        assert results[0].success is True

    def test_partial_success_surfaces_per_item_failures(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test allowPartialSuccess responses expose typed per-item errors without raising."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-create",
            json={
                "result": [
                    {
                        "correlationId": 1,
                        "operation": "CREATE",
                        "success": True,
                        "result": KEYWORD_JSON,
                        "error": None,
                    },
                    {
                        "correlationId": 2,
                        "operation": "CREATE",
                        "success": False,
                        "result": None,
                        "error": {
                            "code": "DUPLICATE_KEYWORD",
                            "message": "keyword already exists",
                        },
                    },
                ],
                "error": None,
            },
        )
        results = BulkOperationResource(v1_client).create_keywords(
            [
                BulkKeywordCreate(ad_group_id=200, text="coffee"),
                BulkKeywordCreate(ad_group_id=200, text="coffee"),
            ],
            allow_partial_success=True,
        )
        assert [r.success for r in results] == [True, False]
        assert results[1].result is None
        assert results[1].error is not None
        assert results[1].error.code == "DUPLICATE_KEYWORD"

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 200 carrying a top-level error block raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-create",
            json={
                "result": None,
                "error": {
                    "code": "TOO_MANY_ITEMS",
                    "message": "bulk request exceeds the maximum item count",
                    "details": [{"code": "TOO_MANY_ITEMS", "message": "split the batch"}],
                },
            },
        )
        with pytest.raises(PartialFailureError, match="maximum item count") as exc_info:
            BulkOperationResource(v1_client).create_keywords(
                [BulkKeywordCreate(ad_group_id=200, text="coffee")]
            )
        assert exc_info.value.details[0]["code"] == "TOO_MANY_ITEMS"


class TestBulkKeywordUpdate:
    """Tests for POST /v1/keywords/bulk-update."""

    def test_update_keywords_posts_bulk_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update_keywords() serializes id/bid/status data payloads."""
        mock_token(httpx_mock)
        updated = {**KEYWORD_JSON, "status": "PAUSED", "bid": {"amount": "2.50", "currency": "USD"}}
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-update",
            json={
                "result": [
                    {
                        "correlationId": 1,
                        "operation": "UPDATE",
                        "success": True,
                        "result": updated,
                        "error": None,
                    }
                ],
                "error": None,
            },
        )
        results = BulkOperationResource(v1_client).update_keywords(
            [
                BulkKeywordUpdate(
                    id=300,
                    bid=Money.usd("2.50"),
                    status=KeywordStatus.PAUSED,
                )
            ]
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.url == f"{BASE_URL}/keywords/bulk-update"
        assert json.loads(request.content) == {
            "allowPartialSuccess": False,
            "items": [
                {
                    "correlationId": 1,
                    "data": {
                        "id": 300,
                        "bid": {"amount": "2.50", "currency": "USD"},
                        "status": "PAUSED",
                    },
                }
            ],
        }
        assert results[0].operation is BulkOperation.UPDATE
        keyword = results[0].result
        assert keyword is not None
        assert keyword.status is KeywordStatus.PAUSED

    async def test_update_keywords_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async update variant parses per-item results."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-update",
            json={
                "result": [
                    {
                        "correlationId": 1,
                        "operation": "UPDATE",
                        "success": True,
                        "result": KEYWORD_JSON,
                        "error": None,
                    }
                ],
                "error": None,
            },
        )
        results = await BulkOperationResource(v1_client).update_keywords_async(
            [BulkKeywordUpdate(id=300, status=KeywordStatus.PAUSED)]
        )
        assert results[0].correlation_id == 1


class TestBulkNegativeKeywordCreate:
    """Tests for POST /v1/negative-keywords/bulk-create."""

    def test_create_negative_keywords_mixes_levels(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test campaign- and ad-group-level negatives mix in one request."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/bulk-create",
            json={
                "result": [
                    {
                        "correlationId": 1,
                        "operation": "CREATE",
                        "success": True,
                        "result": NEGATIVE_KEYWORD_JSON,
                        "error": None,
                    },
                    {
                        "correlationId": 2,
                        "operation": "CREATE",
                        "success": True,
                        "result": {**NEGATIVE_KEYWORD_JSON, "id": 401, "adGroupId": 200},
                        "error": None,
                    },
                ],
                "error": None,
            },
        )
        results = BulkOperationResource(v1_client).create_negative_keywords(
            [
                BulkNegativeKeywordCreate(
                    campaign_id=100,
                    text="free",
                    match_type=KeywordMatchType.BROAD,
                    status=NegativeKeywordStatus.ENABLED,
                ),
                BulkNegativeKeywordCreate(campaign_id=100, ad_group_id=200, text="free"),
            ]
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.url == f"{BASE_URL}/negative-keywords/bulk-create"
        assert json.loads(request.content) == {
            "allowPartialSuccess": False,
            "items": [
                {
                    "correlationId": 1,
                    "data": {
                        "campaignId": 100,
                        "text": "free",
                        "matchType": "BROAD",
                        "status": "ENABLED",
                    },
                },
                {
                    "correlationId": 2,
                    "data": {"campaignId": 100, "adGroupId": 200, "text": "free"},
                },
            ],
        }
        assert results[0].result is not None
        assert results[0].result.ad_group_id is None
        assert results[1].result is not None
        assert results[1].result.ad_group_id == 200

    async def test_create_negative_keywords_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async negative-keyword create variant."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/bulk-create",
            json={"result": [], "error": None},
        )
        results = await BulkOperationResource(v1_client).create_negative_keywords_async(
            [BulkNegativeKeywordCreate(campaign_id=100, text="free")]
        )
        assert results == []


class TestBulkNegativeKeywordUpdate:
    """Tests for POST /v1/negative-keywords/bulk-update."""

    def test_update_negative_keywords_posts_status_only(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update_negative_keywords() serializes id/status payloads."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/bulk-update",
            json={
                "result": [
                    {
                        "correlationId": 1,
                        "operation": "UPDATE",
                        "success": True,
                        "result": {**NEGATIVE_KEYWORD_JSON, "status": "PAUSED"},
                        "error": None,
                    }
                ],
                "error": None,
            },
        )
        results = BulkOperationResource(v1_client).update_negative_keywords(
            [BulkNegativeKeywordUpdate(id=400, status=NegativeKeywordStatus.PAUSED)]
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.url == f"{BASE_URL}/negative-keywords/bulk-update"
        assert json.loads(request.content) == {
            "allowPartialSuccess": False,
            "items": [{"correlationId": 1, "data": {"id": 400, "status": "PAUSED"}}],
        }
        negative = results[0].result
        assert negative is not None
        assert negative.status is NegativeKeywordStatus.PAUSED

    async def test_update_negative_keywords_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async negative-keyword update variant."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/bulk-update",
            json={"result": [], "error": None},
        )
        results = await BulkOperationResource(v1_client).update_negative_keywords_async(
            [BulkNegativeKeywordUpdate(id=400, status=NegativeKeywordStatus.ENABLED)]
        )
        assert results == []


class TestBulkEnums:
    """Enum round-trip tests for bulk models."""

    def test_bulk_operation_round_trips(self) -> None:
        """Test BulkOperation values survive serialization round-trips."""
        assert BulkOperation("CREATE") is BulkOperation.CREATE
        assert BulkOperation("UPDATE") is BulkOperation.UPDATE
        assert BulkOperation("DELETE") is BulkOperation.DELETE
        assert BulkOperation.CREATE.value == "CREATE"

    def test_match_type_round_trips_through_create_model(self) -> None:
        """Test KeywordMatchType round-trips through BulkKeywordCreate JSON."""
        data = BulkKeywordCreate(ad_group_id=1, text="x", match_type=KeywordMatchType.CATEGORY)
        dumped = data.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["matchType"] == "CATEGORY"
        parsed = BulkKeywordCreate.model_validate(dumped)
        assert parsed.match_type is KeywordMatchType.CATEGORY
