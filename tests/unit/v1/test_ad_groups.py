"""Tests for the v1 ad groups resource and models."""

import json
from datetime import datetime

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.ad_groups import (
    AdGroup,
    AdGroupCreate,
    AdGroupDisplayStatus,
    AdGroupStatus,
    AdGroupSystemStatus,
    AdGroupSystemStatusReason,
    AdGroupTargeting,
    AdGroupUpdate,
    BidStrategy,
    BidStrategyGoal,
    BidStrategyType,
    PricingModel,
    TargetingData,
)
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.ad_groups import AdGroupResource

BASE_URL = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"


def _mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a stub OAuth token response for the client's auth flow."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "expires_in": 3600, "token_type": "Bearer"},
    )


class TestAdGroupResourceConfig:
    """Tests for the resource's static configuration."""

    def test_resource_configuration(self, v1_client: AppleAdsClient) -> None:
        """Test base_path, model_class, wrapper, and context requirements."""
        resource = AdGroupResource(v1_client)
        assert resource.base_path == "adgroups"
        assert resource.model_class is AdGroup
        assert resource.payload_wrapper is None
        assert resource.requires_account_context is True


class TestGetAdGroup:
    """Tests for GET /v1/adgroups/{id}."""

    def test_get_ad_group(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() issues GET to the item path and parses the result."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/adgroups/2001",
            json={
                "result": {
                    "id": 2001,
                    "name": "US iPhone",
                    "adAccountId": 12345,
                    "campaignId": 1000,
                    "startTime": "2025-09-01T00:00:00.000",
                    "pricingModel": "CPT",
                    "automatedKeywordsOptIn": True,
                    "automatedKeywordsRequired": False,
                    "status": "ENABLED",
                    "systemStatus": "NOT_RUNNING",
                    "systemStatusReasons": ["CAMPAIGN_NOT_RUNNING"],
                    "displayStatus": "ON_HOLD",
                    "bidStrategy": {
                        "bidStrategyType": "MANUAL_CPT",
                        "bidStrategyGoal": "TAP",
                        "bid": {"amount": "2.50", "currency": "USD"},
                    },
                    "targeting": {
                        "deviceClass": {"include": ["IPHONE"]},
                        "minAge": {"include": ["18"]},
                        "appDownloader": {"exclude": ["123456789"]},
                    },
                    "deleted": False,
                    "creationTime": "2025-08-01T10:00:00.000",
                    "modificationTime": "2025-08-02T10:00:00.000",
                },
                "error": None,
            },
        )
        ad_group = AdGroupResource(v1_client).get(2001)
        request = httpx_mock.get_requests(url=f"{BASE_URL}/adgroups/2001")[0]
        assert request.method == "GET"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert ad_group.id == 2001
        assert ad_group.campaign_id == 1000
        assert ad_group.pricing_model is PricingModel.CPT
        assert ad_group.status is AdGroupStatus.ENABLED
        assert ad_group.system_status is AdGroupSystemStatus.NOT_RUNNING
        assert ad_group.system_status_reasons == [AdGroupSystemStatusReason.CAMPAIGN_NOT_RUNNING]
        assert ad_group.display_status is AdGroupDisplayStatus.ON_HOLD
        assert ad_group.bid_strategy is not None
        assert ad_group.bid_strategy.bid_strategy_type is BidStrategyType.MANUAL_CPT
        assert ad_group.bid_strategy.bid == Money(amount="2.50", currency="USD")
        assert ad_group.targeting is not None
        assert ad_group.targeting.device_class == TargetingData(include=["IPHONE"])
        assert ad_group.targeting.min_age == TargetingData(include=["18"])
        assert ad_group.targeting.app_downloader == TargetingData(exclude=["123456789"])
        assert ad_group.deleted is False
        assert ad_group.start_time == datetime(2025, 9, 1)

    def test_get_returns_deleted_ad_group(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test get-by-id parses soft-deleted ad groups (deleted: true)."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/adgroups/2002",
            json={"result": {"id": 2002, "deleted": True, "displayStatus": "DELETED"}},
        )
        ad_group = AdGroupResource(v1_client).get(2002)
        assert ad_group.deleted is True
        assert ad_group.display_status is AdGroupDisplayStatus.DELETED

    async def test_get_ad_group_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async get path parses identically."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/adgroups/2001",
            json={"result": {"id": 2001, "status": "PAUSED"}},
        )
        ad_group = await AdGroupResource(v1_client).get_async(2001)
        assert ad_group.id == 2001
        assert ad_group.status is AdGroupStatus.PAUSED


class TestQueryAdGroups:
    """Tests for POST /v1/adgroups/query."""

    def test_query_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() POSTs the exact filter/pagination body to /query."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/adgroups/query",
            json={
                "result": [{"id": 2001, "name": "A", "campaignId": 1000}],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            },
        )
        page = AdGroupResource(v1_client).query(
            Query().where("campaignId", "EQUALS", 1000).page(size=10)
        )
        request = httpx_mock.get_requests(url=f"{BASE_URL}/adgroups/query")[0]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "filters": [{"field": "campaignId", "operator": "EQUALS", "value": 1000}],
            "pagination": {"pageSize": 10},
        }
        assert len(page) == 1
        assert page[0].campaign_id == 1000
        assert page.has_more is False

    def test_query_without_arguments_posts_empty_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an empty query posts {} and parses an empty page."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/adgroups/query", json={"result": []})
        page = AdGroupResource(v1_client).query()
        request = httpx_mock.get_requests(url=f"{BASE_URL}/adgroups/query")[0]
        assert json.loads(request.content) == {}
        assert len(page) == 0


class TestCreateAdGroup:
    """Tests for POST /v1/adgroups."""

    def test_create_posts_flat_aliased_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() POSTs the flat camelCase body with no wrapper."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/adgroups",
            json={"result": {"id": 2001, "name": "US iPhone", "campaignId": 1000}},
        )
        data = AdGroupCreate(
            name="US iPhone",
            campaign_id=1000,
            pricing_model=PricingModel.CPT,
            start_time=datetime(2026, 1, 1),
            automated_keywords_opt_in=False,
            status=AdGroupStatus.ENABLED,
            bid_strategy=BidStrategy(
                bid_strategy_type=BidStrategyType.MANUAL_CPT,
                bid_strategy_goal=BidStrategyGoal.TAP,
                bid=Money(amount="1.50", currency="USD"),
            ),
            targeting=AdGroupTargeting(
                device_class=TargetingData(include=["IPHONE", "IPAD"]),
                app_downloader=TargetingData(exclude=["123456789"]),
            ),
        )
        created = AdGroupResource(v1_client).create(data)
        request = httpx_mock.get_requests(url=f"{BASE_URL}/adgroups")[0]
        assert request.method == "POST"
        assert json.loads(request.content) == {
            "name": "US iPhone",
            "campaignId": 1000,
            "pricingModel": "CPT",
            "startTime": "2026-01-01T00:00:00",
            "automatedKeywordsOptIn": False,
            "status": "ENABLED",
            "bidStrategy": {
                "bidStrategyType": "MANUAL_CPT",
                "bidStrategyGoal": "TAP",
                "bid": {"amount": "1.50", "currency": "USD"},
            },
            "targeting": {
                "deviceClass": {"include": ["IPHONE", "IPAD"]},
                "appDownloader": {"exclude": ["123456789"]},
            },
        }
        assert created.id == 2001
        assert created.name == "US iPhone"

    def test_create_model_has_no_cpa_cap_field(self) -> None:
        """Test the deprecated cpaCap is not modeled on create."""
        assert "cpa_cap" not in AdGroupCreate.model_fields
        assert "cpa_cap" not in AdGroupUpdate.model_fields
        assert "cpa_cap" not in AdGroup.model_fields


class TestUpdateAdGroup:
    """Tests for PUT /v1/adgroups/{id}."""

    def test_update_puts_partial_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() PUTs only the changed fields, aliased."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/adgroups/2001",
            json={"result": {"id": 2001, "status": "PAUSED"}},
        )
        data = AdGroupUpdate(
            status=AdGroupStatus.PAUSED,
            bid_strategy=BidStrategy(
                bid_strategy_type=BidStrategyType.MAX_CONVERSIONS,
                bid_strategy_goal=BidStrategyGoal.INSTALL,
            ),
        )
        updated = AdGroupResource(v1_client).update(2001, data)
        request = httpx_mock.get_requests(url=f"{BASE_URL}/adgroups/2001")[0]
        assert request.method == "PUT"
        assert json.loads(request.content) == {
            "status": "PAUSED",
            "bidStrategy": {
                "bidStrategyType": "MAX_CONVERSIONS",
                "bidStrategyGoal": "INSTALL",
            },
        }
        assert updated.status is AdGroupStatus.PAUSED

    def test_update_targeting_dimension(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a partial targeting update serializes only included dimensions."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/adgroups/2001", json={"result": {"id": 2001}})
        data = AdGroupUpdate(
            targeting=AdGroupTargeting(daypart=TargetingData(include=["8", "9", "10"]))
        )
        AdGroupResource(v1_client).update(2001, data)
        request = httpx_mock.get_requests(url=f"{BASE_URL}/adgroups/2001")[0]
        assert json.loads(request.content) == {
            "targeting": {"daypart": {"include": ["8", "9", "10"]}}
        }


class TestDeleteAdGroup:
    """Tests for DELETE /v1/adgroups/{id}."""

    def test_delete_issues_delete_and_returns_none(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test delete() sends DELETE to the item path and returns None."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{BASE_URL}/adgroups/2001", json={})
        assert AdGroupResource(v1_client).delete(2001) is None
        request = httpx_mock.get_requests(url=f"{BASE_URL}/adgroups/2001")[0]
        assert request.method == "DELETE"


class TestPartialFailure:
    """Tests for error blocks inside HTTP 200 responses."""

    def test_http_200_with_error_block_raises(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error raises PartialFailureError."""
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/adgroups/2001",
            json={
                "result": None,
                "error": {
                    "code": "INVALID_BID_STRATEGY",
                    "message": "bidStrategyType and bidStrategyGoal must be sent together",
                    "details": [{"code": "INVALID_BID_STRATEGY", "message": "mismatched pairing"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            AdGroupResource(v1_client).get(2001)
        assert exc_info.value.details[0]["code"] == "INVALID_BID_STRATEGY"


class TestEnums:
    """Tests for enum values and round-trips."""

    def test_pricing_model_round_trip(self) -> None:
        """Test PricingModel parses from and serializes back to its wire value."""
        ad_group = AdGroup.model_validate({"id": 1, "pricingModel": "CPM"})
        assert ad_group.pricing_model is PricingModel.CPM
        dumped = ad_group.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["pricingModel"] == "CPM"

    def test_bid_strategy_pairing_values(self) -> None:
        """Test the documented BidStrategyType and BidStrategyGoal values exist."""
        assert {member.value for member in BidStrategyType} == {
            "MANUAL_CPT",
            "MANUAL_CPM",
            "MAX_CONVERSIONS",
            "MAX_ENGAGEMENTS",
        }
        assert {member.value for member in BidStrategyGoal} == {
            "IMPRESSION",
            "INSTALL",
            "TAP",
        }

    def test_display_status_values(self) -> None:
        """Test AdGroupDisplayStatus carries the exact documented values."""
        assert {member.value for member in AdGroupDisplayStatus} == {
            "CAMPAIGN_ON_HOLD",
            "DELETED",
            "LIMITED",
            "ON_HOLD",
            "PAUSED",
            "PROCESSING",
            "RUNNING",
        }
