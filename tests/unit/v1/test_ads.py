"""Tests for the v1 ads resource and models."""

import json
from datetime import datetime

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.ads import (
    Ad,
    AdCreate,
    AdDisplayStatus,
    AdStatus,
    AdSystemLimitedStatusReason,
    AdSystemStatus,
    AdSystemStatusReason,
    AdUpdate,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.ads import AdResource

BASE_URL = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

AD_JSON = {
    "id": 987654321,
    "name": "AwayFinder - Default Product Page",
    "status": "ENABLED",
    "adAccountId": 111222333,
    "campaignId": 444555666,
    "adGroupId": 555666777,
    "creativeId": 666777888,
    "systemStatus": "NOT_RUNNING",
    "systemStatusReasons": ["AD_APPROVAL_PENDING", "CREATIVE_PENDING"],
    "systemStatusLimitingReasons": ["CREATIVE_POLICY_ISSUES"],
    "creationTime": "2025-09-01T08:00:00.000",
    "modificationTime": "2025-09-02T09:30:00.000",
    "displayStatus": "PROCESSING",
    "deleted": False,
}


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


class TestGetAd:
    """Tests for GET /v1/ads/{id}."""

    def test_get_ad(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() issues GET /ads/{id} and parses the full Ad."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/ads/987654321", json={"result": AD_JSON})
        ad = AdResource(v1_client).get(987654321)
        request = httpx_mock.get_requests()[-1]
        assert request.method == "GET"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert ad.id == 987654321
        assert ad.name == "AwayFinder - Default Product Page"
        assert ad.status is AdStatus.ENABLED
        assert ad.ad_account_id == 111222333
        assert ad.campaign_id == 444555666
        assert ad.ad_group_id == 555666777
        assert ad.creative_id == 666777888
        assert ad.system_status is AdSystemStatus.NOT_RUNNING
        assert ad.system_status_reasons == [
            AdSystemStatusReason.AD_APPROVAL_PENDING,
            AdSystemStatusReason.CREATIVE_PENDING,
        ]
        assert ad.system_status_limiting_reasons == [
            AdSystemLimitedStatusReason.CREATIVE_POLICY_ISSUES
        ]
        assert ad.display_status is AdDisplayStatus.PROCESSING
        assert ad.creation_time == datetime(2025, 9, 1, 8, 0, 0)
        assert ad.deleted is False

    def test_get_returns_soft_deleted_ad(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test GET still returns a soft-deleted ad with deleted=true."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/ads/1",
            json={"result": {"id": 1, "deleted": True, "displayStatus": "DELETED"}},
        )
        ad = AdResource(v1_client).get(1)
        assert ad.deleted is True
        assert ad.display_status is AdDisplayStatus.DELETED

    async def test_get_ad_async(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get_async() parses identically to the sync path."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/ads/987654321", json={"result": AD_JSON})
        ad = await AdResource(v1_client).get_async(987654321)
        assert ad.status is AdStatus.ENABLED


class TestCreateAd:
    """Tests for POST /v1/ads."""

    def test_create_posts_bare_aliased_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() POSTs the exact bare (unwrapped) camelCase body."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/ads", json={"result": AD_JSON})
        created = AdResource(v1_client).create(
            AdCreate(
                name="AwayFinder - Default Product Page",
                ad_group_id=555666777,
                creative_id=666777888,
                status=AdStatus.ENABLED,
            )
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "name": "AwayFinder - Default Product Page",
            "adGroupId": 555666777,
            "creativeId": 666777888,
            "status": "ENABLED",
        }
        assert created.id == 987654321
        assert created.status is AdStatus.ENABLED


class TestQueryAds:
    """Tests for POST /v1/ads/query."""

    def test_query_serializes_filters_and_parses_page(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() POSTs the structured body and parses the page."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/ads/query",
            json={
                "result": [AD_JSON],
                "pagination": {"offset": 0, "pageSize": 20, "totalCount": 1},
            },
        )
        page = AdResource(v1_client).query(
            Query()
            .where("adGroupId", "EQUALS", 555666777)
            .order_by("creationTime", "DESC")
            .page(size=20, offset=0, fetch_total_count=True)
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "adGroupId", "operator": "EQUALS", "value": 555666777}],
            "sorting": [{"field": "creationTime", "order": "DESC"}],
            "pagination": {"pageSize": 20, "offset": 0, "fetchTotalCount": True},
        }
        assert len(page) == 1
        assert page[0].ad_group_id == 555666777
        assert page.pagination is not None
        assert page.pagination.total_count == 1
        assert page.has_more is False

    def test_query_for_deleted_ads(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test the deleted EQUALS true filter serializes as documented."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/ads/query", json={"result": []})
        AdResource(v1_client).query(Query().where("deleted", "EQUALS", True))
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"filters": [{"field": "deleted", "operator": "EQUALS", "value": True}]}


class TestUpdateAd:
    """Tests for PUT /v1/ads/{id}."""

    def test_update_puts_partial_bare_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() PUTs only the provided fields, unwrapped."""
        paused = {**AD_JSON, "status": "PAUSED"}
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/ads/987654321", json={"result": paused})
        updated = AdResource(v1_client).update(987654321, AdUpdate(status=AdStatus.PAUSED))
        request = httpx_mock.get_requests()[-1]
        assert request.method == "PUT"
        assert json.loads(request.content) == {"status": "PAUSED"}
        assert updated.status is AdStatus.PAUSED

    def test_update_name_only(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test a name-only update omits status from the body."""
        renamed = {**AD_JSON, "name": "New Name"}
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/ads/987654321", json={"result": renamed})
        AdResource(v1_client).update(987654321, AdUpdate(name="New Name"))
        assert json.loads(httpx_mock.get_requests()[-1].content) == {"name": "New Name"}


class TestDeleteAd:
    """Tests for DELETE /v1/ads/{id}."""

    def test_delete_soft_deletes(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test delete() issues DELETE and tolerates the 200 {} body."""
        mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/ads/987654321", status_code=200, json={})
        assert AdResource(v1_client).delete(987654321) is None
        request = httpx_mock.get_requests()[-1]
        assert request.method == "DELETE"
        assert str(request.url) == f"{BASE_URL}/ads/987654321"


class TestEnums:
    """Tests for enum round-trips."""

    def test_ad_status_round_trip(self) -> None:
        """Test AdStatus survives a serialize/deserialize round-trip."""
        ad = Ad.model_validate({"id": 1, "status": "PAUSED"})
        assert ad.status is AdStatus.PAUSED
        dumped = ad.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["status"] == "PAUSED"
        assert Ad.model_validate(dumped).status is AdStatus.PAUSED

    def test_system_status_reason_values(self) -> None:
        """Test AdSystemStatusReason carries the documented value set."""
        assert AdSystemStatusReason.PRODUCT_PAGE_HIDDEN == "PRODUCT_PAGE_HIDDEN"
        assert len(AdSystemStatusReason) == 20

    def test_display_status_values(self) -> None:
        """Test AdDisplayStatus carries all eight documented values."""
        assert {status.value for status in AdDisplayStatus} == {
            "RUNNING",
            "PAUSED",
            "ON_HOLD",
            "LIMITED",
            "PROCESSING",
            "DELETED",
            "AD_GROUP_ON_HOLD",
            "CAMPAIGN_ON_HOLD",
        }


class TestPartialFailure:
    """Tests for 2xx responses carrying an error block."""

    def test_http_200_with_error_block_raises(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an HTTP 200 body with an error block raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/ads/query",
            json={
                "result": None,
                "error": {
                    "code": "INVALID_FILTER",
                    "message": "unsupported filter field",
                    "details": [{"code": "INVALID_FILTER", "message": "bad field"}],
                },
            },
        )
        with pytest.raises(PartialFailureError, match="unsupported filter field"):
            AdResource(v1_client).query()
