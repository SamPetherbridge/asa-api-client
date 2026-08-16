"""Tests for the v1 insights resource and models."""

import json
from datetime import date

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.insights import (
    ImpressionShareGranularity,
    ImpressionShareOptions,
    ImpressionShareQueryRequest,
    ImpressionShareReportType,
    ImpressionShareRow,
    ImpressionShareTimeRange,
    InsightsFilter,
    InsightsPagination,
    InsightsSorting,
    KeywordInsights,
    SearchTermPopularityGranularity,
    SearchTermPopularityQueryRequest,
    SearchTermPopularityRow,
    SearchTermPopularityTimeRange,
)
from asa_api_client.v1.resources.insights import InsightResource

BASE_URL = "https://api.ads.apple.com/v1"
IMPRESSION_SHARE_URL = f"{BASE_URL}/insights/apps/impression-share/query"
POPULARITY_URL = f"{BASE_URL}/insights/apps/search-term-popularity/query"


@pytest.fixture(autouse=True)
def _mock_token_endpoint(httpx_mock: HTTPXMock) -> None:
    """Mock Apple's OAuth token endpoint for every test in this module."""
    httpx_mock.add_response(
        url="https://appleid.apple.com/auth/oauth2/token",
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
        is_optional=True,
        is_reusable=True,
    )


class TestImpressionShare:
    """Tests for POST /v1/insights/apps/impression-share/query."""

    def test_query_impression_share_serializes_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the impression share request body serializes with exact aliases."""
        httpx_mock.add_response(
            url=IMPRESSION_SHARE_URL,
            json={
                "result": {
                    "rows": [
                        {
                            "day": "2026-07-01",
                            "appName": "AwayFinder",
                            "promotedObjectId": "543210012",
                            "countryOrRegion": "US",
                            "searchTerm": "travel finder",
                            "lowImpressionShare": 0.23,
                            "highImpressionShare": 0.23,
                            "rank": 1,
                            "searchPopularity1to5": 4,
                        }
                    ]
                },
                "pagination": {"offset": 0, "pageSize": 100, "totalCount": 1},
            },
        )
        request = ImpressionShareQueryRequest(
            fields=[],
            filters=[
                InsightsFilter(field="promotedObjectId", operator="EQUALS", value="543210012")
            ],
            sorting=[InsightsSorting(field="highImpressionShare", order="DESC")],
            time_range=ImpressionShareTimeRange(
                start=date(2026, 7, 1),
                end=date(2026, 7, 7),
                granularity=ImpressionShareGranularity.DAILY,
            ),
            pagination=InsightsPagination(offset=0, page_size=100),
            options=ImpressionShareOptions(
                impression_share_report_type=ImpressionShareReportType.FIRST_SLOT
            ),
        )
        page = InsightResource(v1_client).query_impression_share(request)

        http_request = httpx_mock.get_requests(url=IMPRESSION_SHARE_URL)[0]
        assert http_request.method == "POST"
        assert http_request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(http_request.content) == {
            "fields": [],
            "filters": [{"field": "promotedObjectId", "operator": "EQUALS", "value": "543210012"}],
            "sorting": [{"field": "highImpressionShare", "order": "DESC"}],
            "timeRange": {"start": "2026-07-01", "end": "2026-07-07", "granularity": "DAILY"},
            "pagination": {"offset": 0, "pageSize": 100},
            "options": {"impressionShareReportType": "FIRST_SLOT"},
        }
        assert len(page) == 1
        row = page[0]
        assert isinstance(row, ImpressionShareRow)
        assert row.day == date(2026, 7, 1)
        assert row.app_name == "AwayFinder"
        assert row.promoted_object_id == "543210012"
        assert row.low_impression_share == 0.23
        assert row.high_impression_share == 0.23
        assert row.rank == 1
        assert row.search_popularity_1_to_5 == 4
        assert page.has_more is False

    def test_query_impression_share_weekly_rows(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test weekly granularity serializes and week rows parse."""
        httpx_mock.add_response(
            url=IMPRESSION_SHARE_URL,
            json={
                "result": {
                    "rows": [
                        {
                            "week": "2026-06-28",
                            "promotedObjectId": "543210012",
                            "countryOrRegion": "US",
                            "lowImpressionShare": 0.91,
                            "highImpressionShare": 1,
                        }
                    ]
                }
            },
        )
        request = ImpressionShareQueryRequest(
            filters=[
                InsightsFilter(field="promotedObjectId", operator="EQUALS", value="543210012")
            ],
            time_range=ImpressionShareTimeRange(
                start=date(2026, 6, 28),
                end=date(2026, 7, 25),
                granularity=ImpressionShareGranularity.WEEKLY_SUN_SAT,
            ),
        )
        page = InsightResource(v1_client).query_impression_share(request)
        body = json.loads(httpx_mock.get_requests(url=IMPRESSION_SHARE_URL)[0].content)
        assert body == {
            "filters": [{"field": "promotedObjectId", "operator": "EQUALS", "value": "543210012"}],
            "timeRange": {
                "start": "2026-06-28",
                "end": "2026-07-25",
                "granularity": "WEEKLY_SUN_SAT",
            },
        }
        assert page[0].week == date(2026, 6, 28)
        assert page[0].high_impression_share == 1

    async def test_query_impression_share_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async impression share query hits the same endpoint."""
        httpx_mock.add_response(
            url=IMPRESSION_SHARE_URL,
            json={"result": {"rows": [{"searchTerm": "travel", "rank": 2}]}},
        )
        request = ImpressionShareQueryRequest(
            filters=[InsightsFilter(field="promotedObjectId", operator="EQUALS", value="1")],
            time_range=ImpressionShareTimeRange(
                start=date(2026, 7, 1),
                end=date(2026, 7, 7),
                granularity=ImpressionShareGranularity.DAILY,
            ),
        )
        page = await InsightResource(v1_client).query_impression_share_async(request)
        assert page[0].search_term == "travel"
        assert page[0].rank == 2

    def test_http_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a 2xx impression share response carrying an error block raises."""
        httpx_mock.add_response(
            url=IMPRESSION_SHARE_URL,
            json={
                "result": None,
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "promotedObjectId filter is required",
                    "details": [{"code": "MISSING_FILTER", "message": "promotedObjectId required"}],
                },
            },
        )
        request = ImpressionShareQueryRequest(
            filters=[],
            time_range=ImpressionShareTimeRange(
                start=date(2026, 7, 1),
                end=date(2026, 7, 7),
                granularity=ImpressionShareGranularity.DAILY,
            ),
        )
        with pytest.raises(PartialFailureError) as exc_info:
            InsightResource(v1_client).query_impression_share(request)
        assert exc_info.value.details[0]["code"] == "MISSING_FILTER"


class TestSearchTermPopularity:
    """Tests for POST /v1/insights/apps/search-term-popularity/query."""

    def test_query_search_term_popularity_serializes_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the popularity request body serializes with exact aliases."""
        httpx_mock.add_response(
            url=POPULARITY_URL,
            json={
                "result": {
                    "rows": [
                        {
                            "week": "2026-07-05",
                            "countryOrRegion": "US",
                            "genre": "TRAVEL",
                            "searchTerm": "trip planner",
                            "rankInGenre": 1,
                            "searchPopularityInGenre": 100,
                            "searchPopularity1to100": 87,
                            "searchPopularity1to5": 5,
                        }
                    ]
                },
                "pagination": {"offset": 0, "pageSize": 500, "totalCount": 1},
            },
        )
        request = SearchTermPopularityQueryRequest(
            fields=[
                "rankInGenre",
                "searchPopularityInGenre",
                "searchPopularity1to100",
                "searchPopularity1to5",
            ],
            filters=[
                InsightsFilter(field="countryOrRegion", operator="EQUALS", value="US"),
                InsightsFilter(field="genre", operator="EQUALS", value="TRAVEL"),
            ],
            sorting=[InsightsSorting(field="rankInGenre", order="ASC")],
            time_range=SearchTermPopularityTimeRange(
                start=date(2026, 7, 5),
                end=date(2026, 7, 11),
                granularity=SearchTermPopularityGranularity.WEEKLY_SUN_SAT,
            ),
            pagination=InsightsPagination(offset=0, page_size=500),
        )
        page = InsightResource(v1_client).query_search_term_popularity(request)

        http_request = httpx_mock.get_requests(url=POPULARITY_URL)[0]
        assert http_request.method == "POST"
        assert http_request.headers["X-AP-Context"] == "adAccountId=12345"
        assert json.loads(http_request.content) == {
            "fields": [
                "rankInGenre",
                "searchPopularityInGenre",
                "searchPopularity1to100",
                "searchPopularity1to5",
            ],
            "filters": [
                {"field": "countryOrRegion", "operator": "EQUALS", "value": "US"},
                {"field": "genre", "operator": "EQUALS", "value": "TRAVEL"},
            ],
            "sorting": [{"field": "rankInGenre", "order": "ASC"}],
            "timeRange": {
                "start": "2026-07-05",
                "end": "2026-07-11",
                "granularity": "WEEKLY_SUN_SAT",
            },
            "pagination": {"offset": 0, "pageSize": 500},
        }
        row = page[0]
        assert isinstance(row, SearchTermPopularityRow)
        assert row.week == date(2026, 7, 5)
        assert row.genre == "TRAVEL"
        assert row.search_term == "trip planner"
        assert row.rank_in_genre == 1
        assert row.search_popularity_in_genre == 100
        assert row.search_popularity_1_to_100 == 87
        assert row.search_popularity_1_to_5 == 5
        assert page.has_more is False

    def test_query_search_term_popularity_minimal_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test unset optional request sections are omitted from the body."""
        httpx_mock.add_response(
            url=POPULARITY_URL,
            json={
                "result": {
                    "rows": [
                        {
                            "month": "2026-07",
                            "countryOrRegion": "US",
                            "genre": "PRODUCTIVITY_UTILITIES",
                            "searchTerm": "todo list",
                        }
                    ]
                }
            },
        )
        request = SearchTermPopularityQueryRequest(
            time_range=SearchTermPopularityTimeRange(
                start=date(2026, 7, 1),
                end=date(2026, 7, 31),
                granularity=SearchTermPopularityGranularity.MONTHLY,
            )
        )
        page = InsightResource(v1_client).query_search_term_popularity(request)
        assert json.loads(httpx_mock.get_requests(url=POPULARITY_URL)[0].content) == {
            "timeRange": {"start": "2026-07-01", "end": "2026-07-31", "granularity": "MONTHLY"}
        }
        assert page[0].month == "2026-07"
        assert page[0].week is None

    async def test_query_search_term_popularity_async(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async popularity query parses rows."""
        httpx_mock.add_response(
            url=POPULARITY_URL,
            json={"result": {"rows": [{"searchTerm": "trip planner", "rankInGenre": 3}]}},
        )
        request = SearchTermPopularityQueryRequest(
            time_range=SearchTermPopularityTimeRange(
                start=date(2026, 7, 5),
                end=date(2026, 7, 11),
                granularity=SearchTermPopularityGranularity.WEEKLY_SUN_SAT,
            )
        )
        page = await InsightResource(v1_client).query_search_term_popularity_async(request)
        assert page[0].rank_in_genre == 3

    def test_empty_result_container_parses_to_empty_page(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test a null result container yields an empty page."""
        httpx_mock.add_response(url=POPULARITY_URL, json={"result": None})
        request = SearchTermPopularityQueryRequest(
            time_range=SearchTermPopularityTimeRange(
                start=date(2026, 7, 5),
                end=date(2026, 7, 11),
                granularity=SearchTermPopularityGranularity.WEEKLY_SUN_SAT,
            )
        )
        page = InsightResource(v1_client).query_search_term_popularity(request)
        assert len(page) == 0
        assert page.has_more is False


class TestModels:
    """Tests for insights model serialization behavior."""

    def test_impression_share_granularity_enum_round_trip(self) -> None:
        """Test ImpressionShareGranularity survives a parse/serialize round trip."""
        time_range = ImpressionShareTimeRange.model_validate(
            {"start": "2026-06-28", "end": "2026-07-25", "granularity": "WEEKLY_SUN_SAT"}
        )
        assert time_range.granularity is ImpressionShareGranularity.WEEKLY_SUN_SAT
        dumped = time_range.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped["granularity"] == "WEEKLY_SUN_SAT"
        assert ImpressionShareGranularity("DAILY").value == "DAILY"

    def test_search_term_popularity_granularity_values(self) -> None:
        """Test SearchTermPopularityGranularity has the exact documented values."""
        assert SearchTermPopularityGranularity.WEEKLY_SUN_SAT.value == "WEEKLY_SUN_SAT"
        assert SearchTermPopularityGranularity.MONTHLY.value == "MONTHLY"
        assert SearchTermPopularityGranularity("MONTHLY") is (
            SearchTermPopularityGranularity.MONTHLY
        )

    def test_impression_share_report_type_enum_round_trip(self) -> None:
        """Test ImpressionShareReportType parses and serializes documented values."""
        options = ImpressionShareOptions.model_validate({"impressionShareReportType": "ALL_SLOTS"})
        assert options.impression_share_report_type is ImpressionShareReportType.ALL_SLOTS
        dumped = options.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {"impressionShareReportType": "ALL_SLOTS"}

    def test_impression_share_row_uses_camel_case_aliases(self) -> None:
        """Test ImpressionShareRow parses camelCase and dumps with aliases."""
        row = ImpressionShareRow.model_validate(
            {
                "day": "2026-07-01",
                "appName": "AwayFinder",
                "promotedObjectId": "543210012",
                "lowImpressionShare": 0.0,
                "highImpressionShare": 0.0,
                "searchPopularity1to5": 2,
            }
        )
        assert row.app_name == "AwayFinder"
        assert row.low_impression_share == 0.0
        dumped = row.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped == {
            "day": "2026-07-01",
            "appName": "AwayFinder",
            "promotedObjectId": "543210012",
            "lowImpressionShare": 0.0,
            "highImpressionShare": 0.0,
            "searchPopularity1to5": 2,
        }

    def test_keyword_insights_parses_bid_recommendation(self) -> None:
        """Test KeywordInsights parses the nested bid recommendation amount."""
        insights = KeywordInsights.model_validate(
            {"bidRecommendation": {"suggestedBidAmount": 2.35}}
        )
        assert insights.bid_recommendation is not None
        assert insights.bid_recommendation.suggested_bid_amount == 2.35
        dumped = insights.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {"bidRecommendation": {"suggestedBidAmount": 2.35}}
