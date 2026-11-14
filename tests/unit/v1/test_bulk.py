"""Tests for the v1 bulk operations resource."""

import json

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.bulk import (
    BulkKeywordCreate,
    BulkKeywordDelete,
    BulkKeywordUpdate,
    BulkNegativeKeywordCreate,
    BulkNegativeKeywordDelete,
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


class TestBulkDelete:
    """Tests for POST /v1/{keywords,negative-keywords}/bulk-delete."""

    def test_delete_keywords_accepts_bare_ids_and_models(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test delete_keywords() accepts bare IDs, models, and explicit request items."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-delete",
            json={
                "result": [
                    {"correlationId": 1, "operation": "DELETE", "success": True},
                    {
                        "correlationId": 99,
                        "operation": "DELETE",
                        "success": False,
                        "error": {
                            "code": "ENTITY_NOT_FOUND",
                            "message": "The specified keyword ID does not exist.",
                        },
                    },
                ],
                "error": None,
            },
        )
        results = BulkOperationResource(v1_client).delete_keywords(
            [
                300,
                BulkRequestItem(correlation_id=99, data=BulkKeywordDelete(id=301)),
            ],
            allow_partial_success=True,
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.url == f"{BASE_URL}/keywords/bulk-delete"
        assert json.loads(request.content) == {
            "allowPartialSuccess": True,
            "items": [
                {"correlationId": 1, "data": {"id": 300}},
                {"correlationId": 99, "data": {"id": 301}},
            ],
        }
        assert len(results) == 2
        assert results[0].operation is BulkOperation.DELETE
        assert results[0].success is True
        assert results[0].result is None
        assert results[1].correlation_id == 99
        assert results[1].success is False
        assert results[1].error is not None
        assert results[1].error.code == "ENTITY_NOT_FOUND"

    async def test_delete_keywords_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test async keyword bulk-delete."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-delete",
            json={
                "result": [{"correlationId": 1, "operation": "DELETE", "success": True}],
                "error": None,
            },
        )
        results = await BulkOperationResource(v1_client).delete_keywords_async([300])
        assert results[0].success is True

    def test_delete_negative_keywords(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test delete_negative_keywords() serializes IDs and parses outcomes."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/bulk-delete",
            json={
                "result": [{"correlationId": 1, "operation": "DELETE", "success": True}],
                "error": None,
            },
        )
        results = BulkOperationResource(v1_client).delete_negative_keywords(
            [BulkNegativeKeywordDelete(id=400)]
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert request.url == f"{BASE_URL}/negative-keywords/bulk-delete"
        assert json.loads(request.content) == {
            "allowPartialSuccess": False,
            "items": [{"correlationId": 1, "data": {"id": 400}}],
        }
        assert results[0].operation is BulkOperation.DELETE
        assert results[0].success is True

    async def test_delete_negative_keywords_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test async negative-keyword bulk-delete."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/negative-keywords/bulk-delete",
            json={"result": [], "error": None},
        )
        results = await BulkOperationResource(v1_client).delete_negative_keywords_async([400])
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


class TestBulkAutoChunking:
    """Tests for automatic 5,000-item batching in BulkOperationResource."""

    def test_empty_items_returns_empty_without_http_call(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Empty bulk lists return [] immediately without hitting the API."""
        assert BulkOperationResource(v1_client).delete_keywords([]) == []
        assert httpx_mock.get_requests() == []

    def test_splits_over_5000_items_with_continuous_correlation_ids(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Lists > 5,000 split into sequential 5,000-item chunks with continuous correlationId."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-delete",
            json={
                "result": [
                    {"correlationId": i, "operation": "DELETE", "success": True}
                    for i in range(1, 5001)
                ],
                "error": None,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-delete",
            json={
                "result": [
                    {"correlationId": 5001, "operation": "DELETE", "success": True},
                    {"correlationId": 5002, "operation": "DELETE", "success": True},
                ],
                "error": None,
            },
        )

        ids = list(range(10_001, 15_003))  # 5,002 keyword IDs
        results = BulkOperationResource(v1_client).delete_keywords(ids, allow_partial_success=True)

        requests = httpx_mock.get_requests(url=f"{BASE_URL}/keywords/bulk-delete")
        assert len(requests) == 2
        first_body = json.loads(requests[0].content)
        second_body = json.loads(requests[1].content)
        assert len(first_body["items"]) == 5000
        assert first_body["items"][0]["correlationId"] == 1
        assert first_body["items"][-1]["correlationId"] == 5000
        assert second_body["items"] == [
            {"correlationId": 5001, "data": {"id": 15001}},
            {"correlationId": 5002, "data": {"id": 15002}},
        ]
        assert len(results) == 5002
        assert results[-1].correlation_id == 5002

    async def test_splits_over_5000_items_async(
        self,
        httpx_mock: HTTPXMock,
        v1_client: AppleAdsClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Async bulk calls also split chunks at MAX_BULK_ITEMS."""
        monkeypatch.setattr("asa_api_client.v1.resources.bulk.MAX_BULK_ITEMS", 2)
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-update",
            json={
                "result": [
                    {"correlationId": 1, "operation": "UPDATE", "success": True},
                    {"correlationId": 2, "operation": "UPDATE", "success": True},
                ],
                "error": None,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/keywords/bulk-update",
            json={
                "result": [{"correlationId": 3, "operation": "UPDATE", "success": True}],
                "error": None,
            },
        )
        updates = [BulkKeywordUpdate(id=i, status=KeywordStatus.PAUSED) for i in (10, 20, 30)]
        results = await BulkOperationResource(v1_client).update_keywords_async(updates)
        assert [r.correlation_id for r in results] == [1, 2, 3]
        assert len(httpx_mock.get_requests(url=f"{BASE_URL}/keywords/bulk-update")) == 2
