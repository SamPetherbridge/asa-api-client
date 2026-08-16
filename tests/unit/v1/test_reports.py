"""Tests for the v1 reports resources and models."""

import json
from datetime import date

import pytest
from pytest_httpx import HTTPXMock

from asa_api_client.exceptions import PartialFailureError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.reports import (
    AppsGroupBy,
    AppsIncludeRows,
    AppsKeywordMatchType,
    AppsOptions,
    AppsReportingRequest,
    BrandsCreativeType,
    BrandsGroupBy,
    BrandsIncludeRows,
    BrandsKeywordMatchType,
    BrandsOptions,
    BrandsReportingRequest,
    ReportFilter,
    ReportFilterOperator,
    ReportGranularity,
    ReportingStatus,
    ReportingSystemStatus,
    ReportSorting,
    ReportSortOrder,
    ReportTimeRange,
    ReportTimeZone,
    RequestPagination,
)
from asa_api_client.v1.resources.reports import BrandReportResource, ReportResource

BASE_URL = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"


def mock_token(httpx_mock: HTTPXMock) -> None:
    """Register a mocked OAuth token response."""
    httpx_mock.add_response(
        url=TOKEN_URL,
        json={"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600},
    )


class TestAppsCampaignReports:
    """Tests for POST /reports/apps/campaigns/query."""

    def test_posts_to_query_url_and_parses_rows(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test campaigns() POSTs to the campaigns query URL and parses rows."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "id": 542370539,
                                "name": "US Search",
                                "status": "ENABLED",
                                "systemStatus": "RUNNING",
                                "adChannelType": "SEARCH",
                                "billingEvent": "TAPS",
                                "dailyBudget": {"value": {"amount": "100.00", "currency": "USD"}},
                            },
                            "totalMetrics": {
                                "impressions": 1000,
                                "taps": 50,
                                "ttr": 0.05,
                                "localSpend": {"amount": "12.34", "currency": "USD"},
                            },
                        }
                    ]
                },
                "pagination": {"offset": 0, "pageSize": 100, "totalCount": 1},
            },
        )
        response = ReportResource(v1_client).campaigns()
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        assert response.result is not None
        assert response.result.rows is not None
        row = response.result.rows[0]
        assert row.metadata is not None
        assert row.metadata.id == 542370539
        assert row.metadata.status is ReportingStatus.ENABLED
        assert row.metadata.system_status is ReportingSystemStatus.RUNNING
        assert row.metadata.daily_budget is not None
        assert row.metadata.daily_budget.value is not None
        assert row.metadata.daily_budget.value.amount == "100.00"
        assert row.total_metrics is not None
        assert row.total_metrics.taps == 50
        assert row.total_metrics.local_spend is not None
        assert row.total_metrics.local_spend.amount == "12.34"

    def test_serializes_full_request_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the reporting request serializes to the exact documented JSON."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={"result": {"rows": []}},
        )
        request = AppsReportingRequest(
            pagination=RequestPagination(offset=0, page_size=100),
            sorting=[ReportSorting(field="localSpend", order=ReportSortOrder.DESC)],
            filters=[
                ReportFilter(
                    field="campaignId",
                    operator=ReportFilterOperator.IN,
                    value=["100", "200"],
                )
            ],
            fields=["impressions", "taps"],
            group_by=[AppsGroupBy.COUNTRY_OR_REGION],
            time_range=ReportTimeRange(
                start=date(2026, 8, 1),
                end=date(2026, 8, 7),
                time_zone=ReportTimeZone.UTC,
                granularity=ReportGranularity.DAILY,
            ),
            options=AppsOptions(include_rows=[AppsIncludeRows.GRAND_TOTAL]),
        )
        ReportResource(v1_client).campaigns(request)
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {
            "pagination": {"offset": 0, "pageSize": 100},
            "sorting": [{"field": "localSpend", "order": "DESC"}],
            "filters": [{"field": "campaignId", "operator": "IN", "value": ["100", "200"]}],
            "fields": ["impressions", "taps"],
            "groupBy": ["countryOrRegion"],
            "timeRange": {
                "start": "2026-08-01",
                "end": "2026-08-07",
                "timeZone": "UTC",
                "granularity": "DAILY",
            },
            "options": {"includeRows": ["GRAND_TOTAL"]},
        }

    def test_omitted_request_posts_empty_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test calling with no request posts an empty JSON object."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={"result": {"rows": []}},
        )
        ReportResource(v1_client).campaigns()
        assert json.loads(httpx_mock.get_requests()[-1].content) == {}

    def test_sends_account_context_header(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test report queries carry the X-AP-Context header."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={"result": {"rows": []}},
        )
        ReportResource(v1_client).campaigns()
        assert httpx_mock.get_requests()[-1].headers["X-AP-Context"] == "adAccountId=12345"

    def test_parses_granular_metrics(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test granularMetrics parse into dated per-period metric models."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {"id": 1},
                            "totalMetrics": {"impressions": 30},
                            "granularMetrics": [
                                {"date": "2026-08-01", "impressions": 10},
                                {"date": "2026-08-02", "impressions": 20},
                            ],
                        }
                    ]
                }
            },
        )
        response = ReportResource(v1_client).campaigns()
        assert response.result is not None
        assert response.result.rows is not None
        granular = response.result.rows[0].granular_metrics
        assert granular is not None
        assert [metric.date for metric in granular] == [date(2026, 8, 1), date(2026, 8, 2)]
        assert [metric.impressions for metric in granular] == [10, 20]

    def test_parses_grand_total_summary(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the GRAND_TOTAL summary parses into the report summary model."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={
                "result": {
                    "rows": [],
                    "summary": {
                        "grandTotal": {
                            "impressions": 999,
                            "localSpend": {"amount": "55.00", "currency": "USD"},
                        }
                    },
                },
                "pagination": {"offset": 0, "pageSize": 100, "totalCount": 0},
            },
        )
        response = ReportResource(v1_client).campaigns()
        assert response.result is not None
        assert response.result.summary is not None
        assert response.result.summary.grand_total is not None
        assert response.result.summary.grand_total.impressions == 999
        assert response.pagination is not None
        assert response.pagination.total_count == 0

    async def test_async_campaigns_report(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the async campaign report path parses identically."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={"result": {"rows": [{"metadata": {"id": 7}}]}},
        )
        response = await ReportResource(v1_client).campaigns_async()
        assert response.result is not None
        assert response.result.rows is not None
        assert response.result.rows[0].metadata is not None
        assert response.result.rows[0].metadata.id == 7

    def test_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test an HTTP 200 carrying an error block raises PartialFailureError."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/campaigns/query",
            json={
                "result": None,
                "error": {
                    "code": "INVALID_ARGUMENT",
                    "message": "granularity not supported",
                    "details": [{"code": "INVALID_VALUE", "message": "bad granularity"}],
                },
            },
        )
        with pytest.raises(PartialFailureError) as exc_info:
            ReportResource(v1_client).campaigns()
        assert exc_info.value.status_code == 200
        assert exc_info.value.details[0]["code"] == "INVALID_VALUE"


class TestAppsEntityReports:
    """Tests for the remaining APPS report levels."""

    def test_ad_groups_report_url_and_metadata(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test ad_groups() hits adgroups/query and parses ad group metadata."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/adgroups/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "id": 99,
                                "campaignId": 542370539,
                                "name": "AG",
                                "pricingModel": "CPT",
                            },
                            "totalMetrics": {"taps": 3},
                        }
                    ]
                }
            },
        )
        response = ReportResource(v1_client).ad_groups()
        assert response.result is not None
        assert response.result.rows is not None
        metadata = response.result.rows[0].metadata
        assert metadata is not None
        assert metadata.campaign_id == 542370539
        assert metadata.pricing_model is not None
        assert metadata.pricing_model.value == "CPT"

    def test_ads_report_url_and_nested_creative(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test ads() hits ads/query and parses the nested creative object."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/ads/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "id": 5,
                                "campaignId": 1,
                                "adGroupId": 2,
                                "creative": {
                                    "id": 77,
                                    "creativeType": "CUSTOM_PRODUCT_PAGE",
                                    "systemStatus": "VALID",
                                },
                            },
                            "totalMetrics": {"impressions": 12},
                        }
                    ]
                }
            },
        )
        response = ReportResource(v1_client).ads()
        assert response.result is not None
        assert response.result.rows is not None
        metadata = response.result.rows[0].metadata
        assert metadata is not None
        assert metadata.ad_group_id == 2
        assert metadata.creative is not None
        assert metadata.creative.creative_type is not None
        assert metadata.creative.creative_type.value == "CUSTOM_PRODUCT_PAGE"

    def test_keywords_report_metadata_and_insights(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test keywords() hits keywords/query and parses insights."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/keywords/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "id": 11,
                                "campaignId": 1,
                                "adGroupId": 2,
                                "text": "puzzle game",
                                "matchType": "EXACT",
                                "status": "ACTIVE",
                                "bid": {"amount": "1.50", "currency": "USD"},
                            },
                            "totalMetrics": {"taps": 8},
                            "insights": {"bidRecommendation": {"suggestedBidAmount": 2.25}},
                        }
                    ]
                }
            },
        )
        response = ReportResource(v1_client).keywords()
        assert response.result is not None
        assert response.result.rows is not None
        row = response.result.rows[0]
        assert row.metadata is not None
        assert row.metadata.match_type is AppsKeywordMatchType.EXACT
        assert row.metadata.bid is not None
        assert row.metadata.bid.amount == "1.50"
        assert row.insights is not None
        assert row.insights.bid_recommendation is not None
        assert row.insights.bid_recommendation.suggested_bid_amount == 2.25

    def test_search_terms_report_metadata(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test search_terms() hits searchterms/query and parses the term text."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/apps/searchterms/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "searchTermText": "solitaire",
                                "searchTermSource": "AUTO",
                                "keyword": {"id": 11, "text": "card game", "matchType": "BROAD"},
                            },
                            "totalMetrics": {"impressions": 40},
                        }
                    ]
                }
            },
        )
        response = ReportResource(v1_client).search_terms()
        assert response.result is not None
        assert response.result.rows is not None
        metadata = response.result.rows[0].metadata
        assert metadata is not None
        assert metadata.search_term_text == "solitaire"
        assert metadata.keyword is not None
        assert metadata.keyword.match_type is AppsKeywordMatchType.BROAD


class TestBrandReports:
    """Tests for the business-brands report endpoints."""

    def test_campaigns_report_url_and_action_metrics(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test brand campaigns() hits business-brands/campaigns/query."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/business-brands/campaigns/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "id": 800,
                                "promotedObjectType": "BUSINESS_BRAND",
                                "status": "ENABLED",
                            },
                            "totalMetrics": {
                                "taps": 4,
                                "getDirections": {"tap": 3},
                                "costPerAction": {"tap": {"amount": "0.75", "currency": "USD"}},
                                "actionsPerTap": {"tap": 0.5},
                            },
                        }
                    ]
                }
            },
        )
        response = BrandReportResource(v1_client).campaigns()
        assert response.result is not None
        assert response.result.rows is not None
        row = response.result.rows[0]
        assert row.metadata is not None
        assert row.metadata.promoted_object_type == "BUSINESS_BRAND"
        assert row.total_metrics is not None
        assert row.total_metrics.get_directions is not None
        assert row.total_metrics.get_directions.tap == 3
        assert row.total_metrics.cost_per_action is not None
        assert row.total_metrics.cost_per_action.tap is not None
        assert row.total_metrics.cost_per_action.tap.amount == "0.75"
        assert row.total_metrics.actions_per_tap is not None
        assert row.total_metrics.actions_per_tap.tap == 0.5

    def test_serializes_brands_request_body(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test the brands reporting request serializes with brands dimensions."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/business-brands/campaigns/query",
            json={"result": {"rows": []}},
        )
        request = BrandsReportingRequest(
            filters=[
                ReportFilter(
                    field="campaignId",
                    operator=ReportFilterOperator.EQUALS,
                    value="800",
                )
            ],
            group_by=[BrandsGroupBy.LOCATION_ID, BrandsGroupBy.SUPPLY_PLACEMENT],
            time_range=ReportTimeRange(
                start=date(2026, 8, 1),
                end=date(2026, 8, 7),
                granularity=ReportGranularity.WEEKLY,
            ),
            options=BrandsOptions(include_rows=[BrandsIncludeRows.GRAND_TOTAL]),
        )
        BrandReportResource(v1_client).campaigns(request)
        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {
            "filters": [{"field": "campaignId", "operator": "EQUALS", "value": "800"}],
            "groupBy": ["locationId", "supplyPlacement"],
            "timeRange": {
                "start": "2026-08-01",
                "end": "2026-08-07",
                "granularity": "WEEKLY",
            },
            "options": {"includeRows": ["GRAND_TOTAL"]},
        }

    def test_ad_groups_report_url(self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient) -> None:
        """Test brand ad_groups() hits business-brands/adgroups/query."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/business-brands/adgroups/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {"id": 12, "campaignId": 800, "locationId": "loc-9"},
                            "totalMetrics": {"impressions": 2},
                        }
                    ]
                }
            },
        )
        response = BrandReportResource(v1_client).ad_groups()
        assert response.result is not None
        assert response.result.rows is not None
        metadata = response.result.rows[0].metadata
        assert metadata is not None
        assert metadata.location_id == "loc-9"

    def test_ads_report_nested_creative(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test brand ads() parses the nested creative with no flat creativeId."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/business-brands/ads/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "id": 31,
                                "creative": {
                                    "id": 41,
                                    "creativeType": "LOCAL_ADS_SEARCH_CREATIVE",
                                    "systemStatus": "PENDING",
                                },
                            },
                            "totalMetrics": {"taps": 1},
                        }
                    ]
                }
            },
        )
        response = BrandReportResource(v1_client).ads()
        assert response.result is not None
        assert response.result.rows is not None
        metadata = response.result.rows[0].metadata
        assert metadata is not None
        assert metadata.creative is not None
        assert metadata.creative.creative_type is BrandsCreativeType.LOCAL_ADS_SEARCH_CREATIVE

    def test_keywords_report_match_type(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test brand keywords() parses the Maps-specific match types."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/business-brands/keywords/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {"id": 21, "text": "coffee", "matchType": "CATEGORY"},
                            "totalMetrics": {"impressions": 6},
                        }
                    ]
                }
            },
        )
        response = BrandReportResource(v1_client).keywords()
        assert response.result is not None
        assert response.result.rows is not None
        metadata = response.result.rows[0].metadata
        assert metadata is not None
        assert metadata.match_type is BrandsKeywordMatchType.CATEGORY

    def test_search_terms_report_metadata(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test brand search_terms() hits business-brands/searchterms/query."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/business-brands/searchterms/query",
            json={
                "result": {
                    "rows": [
                        {
                            "metadata": {
                                "searchTermText": "coffee near me",
                                "keyword": {"id": 21, "matchType": "PHRASE"},
                            },
                            "totalMetrics": {"taps": 2},
                        }
                    ]
                }
            },
        )
        response = BrandReportResource(v1_client).search_terms()
        assert response.result is not None
        assert response.result.rows is not None
        metadata = response.result.rows[0].metadata
        assert metadata is not None
        assert metadata.search_term_text == "coffee near me"
        assert metadata.keyword is not None
        assert metadata.keyword.match_type is BrandsKeywordMatchType.PHRASE

    def test_200_with_error_block_raises_partial_failure(
        self, httpx_mock: HTTPXMock, v1_client: AppleAdsClient
    ) -> None:
        """Test brand reports raise PartialFailureError on 2xx error blocks."""
        mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{BASE_URL}/reports/business-brands/keywords/query",
            json={
                "result": None,
                "error": {"code": "INVALID_ARGUMENT", "message": "EMPTY_METRICS unsupported"},
            },
        )
        with pytest.raises(PartialFailureError, match="EMPTY_METRICS unsupported"):
            BrandReportResource(v1_client).keywords()


class TestEnums:
    """Enum round-trip tests for report models."""

    def test_granularity_round_trips_through_request_json(self) -> None:
        """Test granularity survives a dump/parse round trip as the same enum."""
        request = AppsReportingRequest(
            time_range=ReportTimeRange(granularity=ReportGranularity.HOURLY)
        )
        dumped = request.model_dump(by_alias=True, exclude_none=True, mode="json")
        assert dumped == {"timeRange": {"granularity": "HOURLY"}}
        reparsed = AppsReportingRequest.model_validate(dumped)
        assert reparsed.time_range is not None
        assert reparsed.time_range.granularity is ReportGranularity.HOURLY

    def test_group_by_enums_use_documented_values(self) -> None:
        """Test groupBy enums carry the exact documented camelCase values."""
        assert AppsGroupBy.COUNTRY_OR_REGION.value == "countryOrRegion"
        assert AppsGroupBy.DEVICE_CLASS.value == "deviceClass"
        assert BrandsGroupBy.LOCATION_ID.value == "locationId"
        assert ReportTimeZone.ORTZ.value == "ORTZ"
        assert AppsIncludeRows.EMPTY_METRICS.value == "EMPTY_METRICS"
