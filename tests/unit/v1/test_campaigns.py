"""Tests for the v1 campaigns resource and models."""

import json
from datetime import datetime

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.campaigns import (
    BidStrategy,
    BidStrategyGoal,
    BidStrategyType,
    BillingEvent,
    Campaign,
    CampaignCreate,
    CampaignDisplayStatus,
    CampaignStatus,
    CampaignSystemLimitedStatusReason,
    CampaignSystemStatus,
    CampaignSystemStatusReason,
    CampaignTargeting,
    CampaignUpdate,
    DailyBudget,
    PromotedObjectType,
    RegulationResponse,
    RegulationResponseValue,
    RegulationType,
    SharedBudgetAssignment,
    SupplyPlacement,
    SupplySource,
    TargetingData,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.campaigns import CampaignResource

BASE_URL = "https://api.ads.apple.com/v1"


@pytest.fixture(autouse=True)
def _mock_token_endpoint(httpx_mock: HTTPXMock) -> None:
    """Mock the OAuth token endpoint so the authenticator can proceed."""
    httpx_mock.add_response(
        url="https://appleid.apple.com/auth/oauth2/token",
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
        is_optional=True,
        is_reusable=True,
    )


def _api_requests(httpx_mock: HTTPXMock) -> list:
    """Return captured API requests, excluding the OAuth token request."""
    return [r for r in httpx_mock.get_requests() if r.url.host != "appleid.apple.com"]


class TestGetCampaign:
    """Tests for GET /v1/campaigns/{id}."""

    def test_get_campaign(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test get() issues GET to the item URL and parses the result."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/542370549",
            json={"result": {"id": 542370549, "name": "Test", "status": "ENABLED"}},
        )
        campaign = CampaignResource(v1_client).get(542370549)
        request = _api_requests(httpx_mock)[0]
        assert request.method == "GET"
        assert str(request.url) == f"{BASE_URL}/campaigns/542370549"
        assert campaign.id == 542370549
        assert campaign.name == "Test"
        assert campaign.status is CampaignStatus.ENABLED

    def test_get_campaign_parses_full_read_model(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the full Campaign read model parses from camelCase JSON."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/1",
            json={
                "result": {
                    "id": 1,
                    "adAccountId": 999,
                    "name": "Full",
                    "billingEvent": "TAPS",
                    "paymentModel": "PAYG",
                    "startTime": "2026-06-07T00:00:00.000",
                    "promotedObjectType": "APPSTORE_APP",
                    "promotedObjectId": "123456789",
                    "status": "PAUSED",
                    "systemStatus": "NOT_RUNNING",
                    "systemStatusReasons": ["PAUSED_BY_USER"],
                    "systemStatusLimitingReasons": ["AD_GROUPS_LIMITED"],
                    "displayStatus": "PAUSED",
                    "dailyBudget": {"value": {"amount": "50.00", "currency": "USD"}},
                    "sharedBudgets": [{"budgetId": 42}],
                    "targeting": {
                        "supplySource": {"include": ["APPSTORE"]},
                        "supplyPlacement": {"include": ["APPSTORE_SEARCH_RESULTS"]},
                        "countryOrRegion": {"include": ["US", "AU"]},
                    },
                    "bidStrategy": {
                        "bidStrategyType": "MANUAL_CPT",
                        "bidStrategyGoal": "TAP",
                        "bid": {"amount": "1.50", "currency": "USD"},
                    },
                    "regulationResponses": [
                        {"regulationType": "CAMPAIGN_SAPIN_LAW", "responseValue": "NOT_AGENT"}
                    ],
                    "creationTime": "2026-01-01T00:00:00.000",
                    "modificationTime": "2026-02-01T00:00:00.000",
                    "deleted": False,
                }
            },
        )
        campaign = CampaignResource(v1_client).get(1)
        assert campaign.ad_account_id == 999
        assert campaign.billing_event is BillingEvent.TAPS
        assert campaign.payment_model == "PAYG"
        assert campaign.promoted_object_type is PromotedObjectType.APPSTORE_APP
        assert campaign.promoted_object_id == "123456789"
        assert campaign.system_status is CampaignSystemStatus.NOT_RUNNING
        assert campaign.system_status_reasons == [CampaignSystemStatusReason.PAUSED_BY_USER]
        assert campaign.system_status_limiting_reasons == [
            CampaignSystemLimitedStatusReason.AD_GROUPS_LIMITED
        ]
        assert campaign.display_status is CampaignDisplayStatus.PAUSED
        assert campaign.daily_budget is not None
        assert campaign.daily_budget.value == Money(amount="50.00", currency="USD")
        assert campaign.shared_budgets == [SharedBudgetAssignment(budget_id=42)]
        assert campaign.targeting is not None
        assert campaign.targeting.country_or_region is not None
        assert campaign.targeting.country_or_region.include == ["US", "AU"]
        assert campaign.bid_strategy is not None
        assert campaign.bid_strategy.bid_strategy_type is BidStrategyType.MANUAL_CPT
        assert campaign.bid_strategy.bid_strategy_goal is BidStrategyGoal.TAP
        assert campaign.regulation_responses == [
            RegulationResponse(
                regulation_type=RegulationType.CAMPAIGN_SAPIN_LAW,
                response_value=RegulationResponseValue.NOT_AGENT,
            )
        ]
        assert campaign.deleted is False


class TestQueryCampaigns:
    """Tests for POST /v1/campaigns/query."""

    def test_query_campaigns_serializes_filters(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query() POSTs the exact filter/pagination body."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/query",
            json={
                "result": [{"id": 1, "name": "A"}],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            },
        )
        page = CampaignResource(v1_client).query(
            Query().where("status", "EQUALS", "ENABLED").page(size=10)
        )
        request = _api_requests(httpx_mock)[0]
        assert request.method == "POST"
        assert str(request.url) == f"{BASE_URL}/campaigns/query"
        assert json.loads(request.content) == {
            "filters": [{"field": "status", "operator": "EQUALS", "value": "ENABLED"}],
            "pagination": {"pageSize": 10},
        }
        assert len(page) == 1
        assert page[0].name == "A"
        assert page.has_more is False

    def test_query_without_arguments_posts_empty_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an empty query posts an empty JSON object."""
        httpx_mock.add_response(url=f"{BASE_URL}/campaigns/query", json={"result": []})
        page = CampaignResource(v1_client).query()
        assert json.loads(_api_requests(httpx_mock)[0].content) == {}
        assert len(page) == 0


class TestCreateCampaign:
    """Tests for POST /v1/campaigns."""

    def test_create_posts_unwrapped_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test create() POSTs the exact aliased, unwrapped body."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns",
            json={"result": {"id": 7, "name": "New", "status": "ENABLED"}},
        )
        created = CampaignResource(v1_client).create(
            CampaignCreate(
                ad_account_id=12345,
                name="New",
                billing_event=BillingEvent.TAPS,
                promoted_object_type=PromotedObjectType.APPSTORE_APP,
                promoted_object_id="123456789",
                daily_budget=DailyBudget(value=Money(amount="100.00", currency="USD")),
                targeting=CampaignTargeting(
                    supply_source=TargetingData(include=[SupplySource.APPSTORE]),
                    supply_placement=TargetingData(
                        include=[SupplyPlacement.APPSTORE_SEARCH_RESULTS]
                    ),
                    country_or_region=TargetingData(include=["US"]),
                ),
                bid_strategy=BidStrategy(
                    bid_strategy_type=BidStrategyType.MANUAL_CPT,
                    bid_strategy_goal=BidStrategyGoal.TAP,
                    bid=Money(amount="1.00", currency="USD"),
                ),
            )
        )
        request = _api_requests(httpx_mock)[0]
        assert request.method == "POST"
        assert str(request.url) == f"{BASE_URL}/campaigns"
        assert json.loads(request.content) == {
            "adAccountId": 12345,
            "name": "New",
            "billingEvent": "TAPS",
            "promotedObjectType": "APPSTORE_APP",
            "promotedObjectId": "123456789",
            "dailyBudget": {"value": {"amount": "100.00", "currency": "USD"}},
            "targeting": {
                "supplySource": {"include": ["APPSTORE"]},
                "supplyPlacement": {"include": ["APPSTORE_SEARCH_RESULTS"]},
                "countryOrRegion": {"include": ["US"]},
            },
            "bidStrategy": {
                "bidStrategyType": "MANUAL_CPT",
                "bidStrategyGoal": "TAP",
                "bid": {"amount": "1.00", "currency": "USD"},
            },
        }
        assert created.id == 7
        assert created.status is CampaignStatus.ENABLED

    def test_create_serializes_start_time_with_milliseconds(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test start/end times serialize as yyyy-MM-ddTHH:mm:ss.SSS UTC."""
        httpx_mock.add_response(url=f"{BASE_URL}/campaigns", json={"result": {"id": 8}})
        CampaignResource(v1_client).create(
            CampaignCreate(
                ad_account_id=12345,
                name="Timed",
                billing_event=BillingEvent.TAPS,
                promoted_object_type=PromotedObjectType.APPSTORE_APP,
                promoted_object_id="123456789",
                daily_budget=DailyBudget(value=Money(amount="10.00", currency="USD")),
                targeting=CampaignTargeting(country_or_region=TargetingData(include=["US"])),
                start_time=datetime(2026, 6, 7),
                end_time=datetime(2026, 7, 1, 12, 30, 15, 500000),
            )
        )
        body = json.loads(_api_requests(httpx_mock)[0].content)
        assert body["startTime"] == "2026-06-07T00:00:00.000"
        assert body["endTime"] == "2026-07-01T12:30:15.500"


class TestUpdateCampaign:
    """Tests for PUT /v1/campaigns/{id}."""

    def test_update_puts_only_changed_fields(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test update() PUTs only the provided fields, aliased."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/55",
            json={"result": {"id": 55, "name": "Renamed", "status": "PAUSED"}},
        )
        updated = CampaignResource(v1_client).update(
            55,
            CampaignUpdate(
                name="Renamed",
                status=CampaignStatus.PAUSED,
                daily_budget=DailyBudget(value=Money(amount="25.00", currency="USD")),
            ),
        )
        request = _api_requests(httpx_mock)[0]
        assert request.method == "PUT"
        assert str(request.url) == f"{BASE_URL}/campaigns/55"
        assert json.loads(request.content) == {
            "name": "Renamed",
            "status": "PAUSED",
            "dailyBudget": {"value": {"amount": "25.00", "currency": "USD"}},
        }
        assert updated.name == "Renamed"
        assert updated.status is CampaignStatus.PAUSED


class TestDeleteCampaign:
    """Tests for DELETE /v1/campaigns/{id}."""

    def test_delete_issues_delete_and_returns_none(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test delete() sends DELETE and tolerates the null-result body."""
        httpx_mock.add_response(url=f"{BASE_URL}/campaigns/55", json={"result": None})
        assert CampaignResource(v1_client).delete(55) is None
        request = _api_requests(httpx_mock)[0]
        assert request.method == "DELETE"
        assert str(request.url) == f"{BASE_URL}/campaigns/55"


class TestLegacyAppLimitedStatusReasonDetails:
    """Tests for GET /v1/campaigns/{id}/legacy-app-limited-status-reason-details."""

    def test_legacy_details_gets_and_parses_map(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the custom endpoint GETs the sub-path and parses the map."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/9/legacy-app-limited-status-reason-details",
            json={
                "result": {
                    "countryOrRegionLimitedStatusReasons": {
                        "US": ["App under review"],
                        "AU": [],
                    }
                }
            },
        )
        details = CampaignResource(v1_client).legacy_app_limited_status_reason_details(9)
        request = _api_requests(httpx_mock)[0]
        assert request.method == "GET"
        assert (
            str(request.url) == f"{BASE_URL}/campaigns/9/legacy-app-limited-status-reason-details"
        )
        assert details.country_or_region_limited_status_reasons == {
            "US": ["App under review"],
            "AU": [],
        }

    async def test_legacy_details_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async variant of the custom endpoint."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/9/legacy-app-limited-status-reason-details",
            json={"result": {"countryOrRegionLimitedStatusReasons": {"US": ["reason"]}}},
        )
        details = await CampaignResource(v1_client).legacy_app_limited_status_reason_details_async(
            9
        )
        assert details.country_or_region_limited_status_reasons == {"US": ["reason"]}


class TestEnums:
    """Tests for enum round-trips."""

    def test_billing_event_round_trip(self) -> None:
        """Test BillingEvent parses from and serializes to its wire value."""
        assert BillingEvent("TAPS") is BillingEvent.TAPS
        assert BillingEvent.IMPRESSIONS.value == "IMPRESSIONS"

    def test_campaign_status_round_trip_through_model(self) -> None:
        """Test CampaignStatus survives a model parse/dump round-trip."""
        campaign = Campaign.model_validate({"id": 1, "status": "PAUSED"})
        assert campaign.status is CampaignStatus.PAUSED
        dumped = campaign.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["status"] == "PAUSED"

    def test_regulation_response_value_members(self) -> None:
        """Test RegulationResponseValue carries the documented values."""
        assert RegulationResponseValue("NOT_ANSWERED") is RegulationResponseValue.NOT_ANSWERED
        assert RegulationResponseValue.FRENCH_BUSINESS.value == "FRENCH_BUSINESS"


class TestPartialFailure:
    """Tests for 200-with-error-block handling."""

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error block raises."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/campaigns/query",
            json={
                "result": None,
                "error": {
                    "code": "PARTIAL",
                    "message": "some items failed",
                    "details": [{"code": "INVALID_ARGUMENT", "message": "bad filter"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            CampaignResource(v1_client).query()
        assert exc_info.value.details[0]["code"] == "INVALID_ARGUMENT"
