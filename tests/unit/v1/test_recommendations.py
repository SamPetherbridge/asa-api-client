"""Tests for the v1 recommendations resource and models."""

import json
from datetime import datetime

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.base import Money
from asa_api_client.v1.models.recommendations import (
    ApplyDailyCapRecommendation,
    ApplyTargetCpaRecommendation,
    DailyCapRecommendation,
    RecommendationCategory,
    RecommendationFilterCondition,
    RecommendationFilterOperator,
    RecommendationPromotedObjectType,
    RecommendationQueryPagination,
    RecommendationQueryRequest,
    RecommendationSorting,
    RecommendationSortingOrder,
    RecommendationState,
    RecommendationStatus,
    TargetCpaRecommendation,
)
from asa_api_client.v1.resources.recommendations import RecommendationResource

BASE_URL = "https://api.ads.apple.com/v1/recommendations"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

TCPA_RECOMMENDATION_JSON = {
    "id": "rec-tcpa-1",
    "recommendationType": "TCPA",
    "promotedObjectId": "123456789",
    "promotedObjectType": "APPSTORE_APP",
    "campaignId": 542370539,
    "campaignName": "US Search",
    "state": "AVAILABLE",
    "status": "ENABLED",
    "recommendedTargetCPA": {"amount": "2.50", "currency": "USD"},
    "bidStrategy": {
        "bidStrategyType": "MAX_CONVERSIONS",
        "bidStrategyGoal": "INSTALL",
        "bidAmount": {"amount": "1.00", "currency": "USD"},
    },
    "averageCPT": {"amount": "0.80", "currency": "USD"},
    "averageCPA": {"amount": "3.10", "currency": "USD"},
    "expectedTaps": 1200,
    "expectedCPA": {"amount": "2.40", "currency": "USD"},
    "expectedInstalls": 400,
    "expectedSpend": {"amount": "960.00", "currency": "USD"},
    "impression": 50000,
    "installs": 350,
    "spend": {"amount": "1085.00", "currency": "USD"},
    "taps": 1300,
    "ttr": 0.026,
    "creationTime": "2026-08-01T08:00:00.000",
    "modificationTime": "2026-08-02T08:00:00.000",
    "expirationTime": "2026-09-01T08:00:00.000",
}

TCPA_HISTORY_JSON = {
    "recommendationId": "rec-tcpa-1",
    "recommendationType": "TCPA",
    "promotedObjectId": "123456789",
    "promotedObjectType": "APPSTORE_APP",
    "campaignId": 542370539,
    "campaignName": "US Search",
    "state": "APPLIED",
    "status": "ENABLED",
    "appliedTargetCPA": {"amount": "2.00", "currency": "USD"},
    "recommendedTargetCPA": {"amount": "2.50", "currency": "USD"},
    "rank": 1,
    "installs": 350,
    "spend": {"amount": "1085.00", "currency": "USD"},
    "expectedCPA": {"amount": "2.40", "currency": "USD"},
    "creationTime": "2026-08-01T08:00:00.000",
    "appliedTime": "2026-08-05T09:30:00.000",
    "expirationTime": "2026-09-01T08:00:00.000",
}

DAILY_CAP_RECOMMENDATION_JSON = {
    "id": "rec-dc-1",
    "recommendationType": "DAILYCAP",
    "promotedObjectId": "123456789",
    "promotedObjectType": "APPSTORE_APP",
    "campaignId": 542370539,
    "campaignName": "US Search",
    "state": "AVAILABLE",
    "status": "ENABLED",
    "suggestedDailyBudgetAmount": {"amount": "150.00", "currency": "USD"},
    "dailyBudget": {"amount": "100.00", "currency": "USD"},
    "bidStrategy": {"bidStrategyType": "MAX_CONVERSIONS", "bidStrategyGoal": "INSTALL"},
    "installs": 350,
    "spend": {"amount": "1085.00", "currency": "USD"},
    "impression": 50000,
    "taps": 1300,
    "ttr": 0.026,
    "expectedImpressions": 62000,
    "expectedInstalls": 425,
    "expectedSpend": {"amount": "1310.00", "currency": "USD"},
    "expectedTaps": 1600,
    "expectedCpa": {"amount": "3.05", "currency": "USD"},
    "creationTime": "2026-08-01T08:00:00.000",
    "expirationTime": "2026-09-01T08:00:00.000",
}

DAILY_CAP_HISTORY_JSON = {
    "recommendationId": "rec-dc-1",
    "recommendationType": "DAILYCAP",
    "promotedObjectId": "123456789",
    "promotedObjectType": "APPSTORE_APP",
    "campaignId": 542370539,
    "state": "APPLIED",
    "status": "ENABLED",
    "appliedDailyBudgetAmount": {"amount": "175.00", "currency": "USD"},
    "suggestedDailyBudgetAmount": {"amount": "150.00", "currency": "USD"},
    "rank": 2,
    "expectedSpend": {"amount": "1310.00", "currency": "USD"},
    "expectedSpendLow": {"amount": "1200.00", "currency": "USD"},
    "expectedSpendHigh": {"amount": "1400.00", "currency": "USD"},
    "expectedInstalls": 425,
    "expectedInstallsLow": 400,
    "expectedInstallsHigh": 450,
    "expectedCpa": {"amount": "3.05", "currency": "USD"},
    "expectedCpaLow": {"amount": "2.90", "currency": "USD"},
    "expectedCpaHigh": {"amount": "3.20", "currency": "USD"},
    "appliedTime": "2026-08-05T09:30:00.000",
}


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Mock Apple's OAuth token endpoint for the real client fixture."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


def build_query() -> RecommendationQueryRequest:
    """Build a representative query with the mandatory promoted-object filters."""
    return RecommendationQueryRequest.for_promoted_object(
        "123456789",
        RecommendationPromotedObjectType.APPSTORE_APP,
        filters=[
            RecommendationFilterCondition(
                field="state",
                operator=RecommendationFilterOperator.EQUALS,
                value=["AVAILABLE"],
            )
        ],
        sorting=[
            RecommendationSorting(field="creationTime", order=RecommendationSortingOrder.DESC)
        ],
        pagination=RecommendationQueryPagination(offset=0, page_size=50),
    )


EXPECTED_QUERY_BODY = {
    "filters": [
        {"field": "promotedObjectId", "operator": "EQUALS", "value": ["123456789"]},
        {"field": "promotedObjectType", "operator": "EQUALS", "value": ["APPSTORE_APP"]},
        {"field": "state", "operator": "EQUALS", "value": ["AVAILABLE"]},
    ],
    "sorting": [{"field": "creationTime", "order": "DESC"}],
    "pagination": {"offset": 0, "pageSize": 50},
}


class TestTargetCpaQuery:
    """Tests for POST /v1/recommendations/target-cpas/query."""

    def test_query_target_cpas(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test query_target_cpas() POSTs the exact body and parses the page."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/target-cpas/query",
            json={
                "result": [TCPA_RECOMMENDATION_JSON],
                "pagination": {"offset": 0, "pageSize": 50, "totalCount": 1},
            },
        )
        page = RecommendationResource(v1_client).query_target_cpas(build_query())
        request = httpx_mock.get_request(url=f"{BASE_URL}/target-cpas/query")
        assert request is not None
        assert request.method == "POST"
        assert request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(request.content) == EXPECTED_QUERY_BODY
        assert len(page) == 1
        assert page.has_more is False
        rec = page[0]
        assert rec.id == "rec-tcpa-1"
        assert rec.recommendation_type is RecommendationCategory.TCPA
        assert rec.promoted_object_type is RecommendationPromotedObjectType.APPSTORE_APP
        assert rec.campaign_id == 542370539
        assert rec.state is RecommendationState.AVAILABLE
        assert rec.status is RecommendationStatus.ENABLED
        assert rec.recommended_target_cpa == Money(amount="2.50", currency="USD")
        assert rec.expected_cpa == Money(amount="2.40", currency="USD")
        assert rec.bid_strategy is not None
        assert rec.bid_strategy.bid_strategy_type == "MAX_CONVERSIONS"
        assert rec.bid_strategy.bid_amount == Money(amount="1.00", currency="USD")
        assert rec.impression == 50000
        assert rec.ttr == 0.026
        assert rec.creation_time == datetime(2026, 8, 1, 8)

    async def test_query_target_cpas_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_target_cpas_async() parses the result identically."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/target-cpas/query",
            json={
                "result": [TCPA_RECOMMENDATION_JSON],
                "pagination": {"offset": 0, "pageSize": 50, "totalCount": 1},
            },
        )
        page = await RecommendationResource(v1_client).query_target_cpas_async(build_query())
        assert len(page) == 1
        assert page[0].state is RecommendationState.AVAILABLE


class TestTargetCpaApplyDismiss:
    """Tests for POST /v1/recommendations/target-cpas/{apply,dismiss}."""

    def test_apply_target_cpas_posts_bare_array(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test apply_target_cpas() POSTs a bare JSON array and parses history."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/target-cpas/apply",
            json={"result": [TCPA_HISTORY_JSON], "pagination": None, "error": None},
        )
        histories = RecommendationResource(v1_client).apply_target_cpas(
            [
                ApplyTargetCpaRecommendation(
                    id="rec-tcpa-1",
                    promoted_object_id="123456789",
                    promoted_object_type=RecommendationPromotedObjectType.APPSTORE_APP,
                    applied_target_cpa=Money(amount="2.00", currency="USD"),
                )
            ]
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/target-cpas/apply")
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == [
            {
                "id": "rec-tcpa-1",
                "promotedObjectId": "123456789",
                "promotedObjectType": "APPSTORE_APP",
                "appliedTargetCPA": {"amount": "2.00", "currency": "USD"},
            }
        ]
        assert len(histories) == 1
        history = histories[0]
        assert history.recommendation_id == "rec-tcpa-1"
        assert history.state is RecommendationState.APPLIED
        assert history.applied_target_cpa == Money(amount="2.00", currency="USD")
        assert history.recommended_target_cpa == Money(amount="2.50", currency="USD")
        assert history.rank == 1
        assert history.applied_time == datetime(2026, 8, 5, 9, 30)

    def test_dismiss_target_cpas_omits_override(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test dismiss_target_cpas() omits appliedTargetCPA when unset."""
        mock_token(httpx_mock)
        dismissed = {**TCPA_HISTORY_JSON, "state": "DISMISSED"}
        dismissed.pop("appliedTargetCPA")
        httpx_mock.add_response(
            url=f"{BASE_URL}/target-cpas/dismiss",
            json={"result": [dismissed], "pagination": None},
        )
        histories = RecommendationResource(v1_client).dismiss_target_cpas(
            [
                ApplyTargetCpaRecommendation(
                    id="rec-tcpa-1",
                    promoted_object_id="123456789",
                    promoted_object_type="APPSTORE_APP",
                )
            ]
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/target-cpas/dismiss")
        assert request is not None
        assert json.loads(request.content) == [
            {
                "id": "rec-tcpa-1",
                "promotedObjectId": "123456789",
                "promotedObjectType": "APPSTORE_APP",
            }
        ]
        assert histories[0].state is RecommendationState.DISMISSED
        assert histories[0].applied_target_cpa is None

    async def test_dismiss_target_cpas_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test dismiss_target_cpas_async() parses the history list."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/target-cpas/dismiss",
            json={"result": [{**TCPA_HISTORY_JSON, "state": "DISMISSED"}], "pagination": None},
        )
        histories = await RecommendationResource(v1_client).dismiss_target_cpas_async(
            [
                ApplyTargetCpaRecommendation(
                    id="rec-tcpa-1",
                    promoted_object_id="123456789",
                    promoted_object_type="APPSTORE_APP",
                )
            ]
        )
        assert histories[0].state is RecommendationState.DISMISSED


class TestDailyBudgetQuery:
    """Tests for POST /v1/recommendations/daily-budgets/query."""

    def test_query_daily_budgets(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test query_daily_budgets() POSTs the exact body and parses the page."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/daily-budgets/query",
            json={
                "result": [DAILY_CAP_RECOMMENDATION_JSON],
                "pagination": {"offset": 0, "pageSize": 50, "totalCount": 1},
            },
        )
        page = RecommendationResource(v1_client).query_daily_budgets(build_query())
        request = httpx_mock.get_request(url=f"{BASE_URL}/daily-budgets/query")
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == EXPECTED_QUERY_BODY
        assert len(page) == 1
        rec = page[0]
        assert rec.id == "rec-dc-1"
        assert rec.recommendation_type is RecommendationCategory.DAILYCAP
        assert rec.suggested_daily_budget_amount == Money(amount="150.00", currency="USD")
        assert rec.daily_budget == Money(amount="100.00", currency="USD")
        assert rec.expected_cpa == Money(amount="3.05", currency="USD")
        assert rec.expected_impressions == 62000

    async def test_query_daily_budgets_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test query_daily_budgets_async() parses the result identically."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/daily-budgets/query",
            json={
                "result": [DAILY_CAP_RECOMMENDATION_JSON],
                "pagination": {"offset": 0, "pageSize": 50, "totalCount": 1},
            },
        )
        page = await RecommendationResource(v1_client).query_daily_budgets_async(build_query())
        assert page[0].recommendation_type is RecommendationCategory.DAILYCAP


class TestDailyBudgetApplyDismiss:
    """Tests for POST /v1/recommendations/daily-budgets/{apply,dismiss}."""

    def test_apply_daily_budgets_posts_bare_array(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test apply_daily_budgets() POSTs a bare JSON array and parses history."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/daily-budgets/apply",
            json={"result": [DAILY_CAP_HISTORY_JSON], "pagination": None},
        )
        histories = RecommendationResource(v1_client).apply_daily_budgets(
            [
                ApplyDailyCapRecommendation(
                    id="rec-dc-1",
                    promoted_object_id="123456789",
                    promoted_object_type=RecommendationPromotedObjectType.APPSTORE_APP,
                    applied_daily_budget=Money(amount="175.00", currency="USD"),
                )
            ]
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/daily-budgets/apply")
        assert request is not None
        assert request.method == "POST"
        assert json.loads(request.content) == [
            {
                "id": "rec-dc-1",
                "promotedObjectId": "123456789",
                "promotedObjectType": "APPSTORE_APP",
                "appliedDailyBudget": {"amount": "175.00", "currency": "USD"},
            }
        ]
        history = histories[0]
        assert history.recommendation_id == "rec-dc-1"
        assert history.state is RecommendationState.APPLIED
        assert history.applied_daily_budget_amount == Money(amount="175.00", currency="USD")
        assert history.expected_spend_low == Money(amount="1200.00", currency="USD")
        assert history.expected_spend_high == Money(amount="1400.00", currency="USD")
        assert history.expected_installs_low == 400
        assert history.expected_cpa_high == Money(amount="3.20", currency="USD")

    async def test_apply_daily_budgets_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test apply_daily_budgets_async() parses the history list."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/daily-budgets/apply",
            json={"result": [DAILY_CAP_HISTORY_JSON], "pagination": None},
        )
        histories = await RecommendationResource(v1_client).apply_daily_budgets_async(
            [
                ApplyDailyCapRecommendation(
                    id="rec-dc-1",
                    promoted_object_id="123456789",
                    promoted_object_type="APPSTORE_APP",
                )
            ]
        )
        assert histories[0].recommendation_id == "rec-dc-1"

    def test_dismiss_daily_budgets(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test dismiss_daily_budgets() hits the dismiss path with a bare array."""
        mock_token(httpx_mock)
        dismissed = {**DAILY_CAP_HISTORY_JSON, "state": "DISMISSED"}
        dismissed.pop("appliedDailyBudgetAmount")
        httpx_mock.add_response(
            url=f"{BASE_URL}/daily-budgets/dismiss",
            json={"result": [dismissed], "pagination": None},
        )
        histories = RecommendationResource(v1_client).dismiss_daily_budgets(
            [
                ApplyDailyCapRecommendation(
                    id="rec-dc-1",
                    promoted_object_id="123456789",
                    promoted_object_type="APPSTORE_APP",
                )
            ]
        )
        request = httpx_mock.get_request(url=f"{BASE_URL}/daily-budgets/dismiss")
        assert request is not None
        assert json.loads(request.content) == [
            {
                "id": "rec-dc-1",
                "promotedObjectId": "123456789",
                "promotedObjectType": "APPSTORE_APP",
            }
        ]
        assert histories[0].state is RecommendationState.DISMISSED
        assert histories[0].applied_daily_budget_amount is None


class TestErrors:
    """Tests for error handling."""

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx response carrying an error block raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/target-cpas/query",
            json={
                "result": None,
                "pagination": None,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "query rejected",
                    "details": [
                        {
                            "code": "MISSING_REQUIRED_FILTER",
                            "message": "Filter 'promotedObjectId' is required",
                            "info": {"field": "promotedObjectId", "location": "filters"},
                        }
                    ],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            RecommendationResource(v1_client).query_target_cpas(build_query())
        assert exc_info.value.details[0]["code"] == "MISSING_REQUIRED_FILTER"


class TestEnumsAndQueryObjects:
    """Tests for enum values and the recommendation-specific query objects."""

    def test_recommendation_state_values(self) -> None:
        """Test the state enum uses DELETE (not DELETED) as its archived value."""
        assert {state.value for state in RecommendationState} == {
            "AVAILABLE",
            "APPLIED",
            "DISMISSED",
            "DELETE",
        }

    def test_recommendation_status_values(self) -> None:
        """Test the status enum carries the exact documented values."""
        assert {status.value for status in RecommendationStatus} == {
            "ENABLED",
            "DISABLED",
            "DELETED",
        }

    def test_recommendation_category_values(self) -> None:
        """Test the category enum covers merged and system-generated values."""
        assert {category.value for category in RecommendationCategory} == {
            "KEYWORD",
            "SKEYWORD",
            "DAILYCAP",
            "SDAILYCAP",
            "TCPA",
            "STCPA",
            "BID",
            "SBID",
        }

    def test_filter_operator_values(self) -> None:
        """Test the filter operator enum matches the documented operator set."""
        assert {op.value for op in RecommendationFilterOperator} == {
            "EQUALS",
            "NOT_EQUALS",
            "IN",
            "CONTAINS_ANY",
            "CONTAINS_ALL",
            "LESS_THAN",
            "LESS_THAN_OR_EQUAL_TO",
            "GREATER_THAN",
            "GREATER_THAN_OR_EQUAL_TO",
            "BETWEEN",
            "STARTS_WITH",
            "ENDS_WITH",
            "LIKE",
        }

    def test_state_enum_round_trip(self) -> None:
        """Test the DELETE state parses from and dumps back to its wire value."""
        rec = TargetCpaRecommendation.model_validate({"state": "DELETE", "status": "DELETED"})
        assert rec.state is RecommendationState.DELETE
        assert rec.status is RecommendationStatus.DELETED
        dumped = rec.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped == {"state": "DELETE", "status": "DELETED"}

    def test_expected_cpa_alias_casing_differs_by_object(self) -> None:
        """Test expectedCPA (target CPA) vs expectedCpa (daily budget) aliases."""
        tcpa = TargetCpaRecommendation.model_validate(
            {"expectedCPA": {"amount": "2.40", "currency": "USD"}}
        )
        assert tcpa.expected_cpa == Money(amount="2.40", currency="USD")
        assert "expectedCPA" in tcpa.model_dump(by_alias=True, exclude_none=True)
        daily = DailyCapRecommendation.model_validate(
            {"expectedCpa": {"amount": "3.05", "currency": "USD"}}
        )
        assert daily.expected_cpa == Money(amount="3.05", currency="USD")
        assert "expectedCpa" in daily.model_dump(by_alias=True, exclude_none=True)

    def test_for_promoted_object_prepends_mandatory_filters(self) -> None:
        """Test the query builder always leads with the two required filters."""
        query = RecommendationQueryRequest.for_promoted_object("999", "BUSINESS_BRAND")
        payload = query.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert payload == {
            "filters": [
                {"field": "promotedObjectId", "operator": "EQUALS", "value": ["999"]},
                {"field": "promotedObjectType", "operator": "EQUALS", "value": ["BUSINESS_BRAND"]},
            ]
        }

    def test_filter_condition_serializes_ignore_case(self) -> None:
        """Test ignoreCase serializes under its alias and defaults to omitted."""
        condition = RecommendationFilterCondition(
            field="campaignName",
            operator=RecommendationFilterOperator.STARTS_WITH,
            value=["us"],
            ignore_case=True,
        )
        assert condition.model_dump(by_alias=True, exclude_none=True) == {
            "field": "campaignName",
            "operator": "STARTS_WITH",
            "value": ["us"],
            "ignoreCase": True,
        }
        sorting = RecommendationSorting(field="creationTime")
        assert sorting.model_dump(by_alias=True, exclude_none=True) == {"field": "creationTime"}
