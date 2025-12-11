"""Report resource for the Apple Search Ads API.

Provides methods for generating performance reports.
"""

from datetime import date
from typing import TYPE_CHECKING, Any

from asa_api_client.logging import get_logger
from asa_api_client.models.reports import (
    GranularityType,
    ReportingRequest,
    ReportingResponse,
)
from asa_api_client.resources.base import BaseResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient

logger = get_logger(__name__)


class ReportResource(BaseResource[ReportingResponse, ReportingRequest, ReportingRequest]):
    """Resource for generating performance reports.

    Reports provide detailed performance metrics for campaigns,
    ad groups, keywords, and search terms.

    Example:
        Get a campaign report::

            from datetime import date
            from asa_api_client.models import GranularityType

            report = client.reports.campaigns(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                granularity=GranularityType.DAILY,
            )

            for row in report.row:
                print(f"{row.metadata.campaign_name}: {row.total.impressions} impressions")

            # Convert to DataFrame
            df = report.to_dataframe()

        Get a keyword report for specific campaigns::

            report = client.reports.keywords(
                campaign_ids=[123, 456],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

        Get search term report::

            report = client.reports.search_terms(
                campaign_id=123,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )
    """

    base_path = "reports"
    model_class = ReportingResponse

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the report resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        super().__init__(client)

    def _build_report_request(
        self,
        start_date: date,
        end_date: date,
        *,
        granularity: GranularityType = GranularityType.DAILY,
        group_by: list[str] | None = None,
        selector: dict[str, Any] | None = None,
        return_grand_totals: bool = True,
        return_row_totals: bool = True,
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        """Build a report request payload.

        Args:
            start_date: Report start date.
            end_date: Report end date.
            granularity: Time granularity for the report.
            group_by: Fields to group by.
            selector: Optional selector for filtering.
            return_grand_totals: Whether to include grand totals.
            return_row_totals: Whether to include row totals.
            timezone: Timezone for the report.

        Returns:
            The report request payload.
        """
        request: dict[str, Any] = {
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "granularity": granularity.value,
            "returnGrandTotals": return_grand_totals,
            "returnRowTotals": return_row_totals,
            "timeZone": timezone,
        }

        if group_by:
            request["groupBy"] = group_by

        # Selector is required by the API with at least orderBy
        if selector:
            # Ensure orderBy is present
            if "orderBy" not in selector:
                selector["orderBy"] = [{"field": "localSpend", "sortOrder": "DESCENDING"}]
            request["selector"] = selector
        else:
            # Default selector with required orderBy
            request["selector"] = {"orderBy": [{"field": "localSpend", "sortOrder": "DESCENDING"}]}

        return request

    def _parse_report_response(self, data: dict[str, Any]) -> ReportingResponse:
        """Parse a report response.

        Args:
            data: The raw API response.

        Returns:
            The parsed ReportingResponse.
        """
        report_data = data.get("data", data)
        if "reportingDataResponse" in report_data:
            report_data = report_data["reportingDataResponse"]
        return ReportingResponse.model_validate(report_data)

    def campaigns(
        self,
        start_date: date,
        end_date: date,
        *,
        campaign_ids: list[int] | None = None,
        granularity: GranularityType = GranularityType.DAILY,
        group_by: list[str] | None = None,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get a campaign-level performance report.

        Args:
            start_date: Report start date.
            end_date: Report end date.
            campaign_ids: Optional list of campaign IDs to filter.
            granularity: Time granularity (HOURLY, DAILY, WEEKLY, MONTHLY).
            group_by: Optional fields to group by.
            timezone: Timezone for the report.

        Returns:
            The campaign report with performance metrics.

        Example:
            Get daily campaign report::

                report = client.reports.campaigns(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    granularity=GranularityType.DAILY,
                )
        """
        selector = None
        if campaign_ids:
            selector = {
                "conditions": [
                    {
                        "field": "campaignId",
                        "operator": "IN",
                        "values": [str(cid) for cid in campaign_ids],
                    }
                ]
            }

        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            group_by=group_by,
            selector=selector,
            timezone=timezone,
        )

        data = self._request("POST", "campaigns", json=request)
        return self._parse_report_response(data)

    async def campaigns_async(
        self,
        start_date: date,
        end_date: date,
        *,
        campaign_ids: list[int] | None = None,
        granularity: GranularityType = GranularityType.DAILY,
        group_by: list[str] | None = None,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get a campaign-level performance report asynchronously.

        Args:
            start_date: Report start date.
            end_date: Report end date.
            campaign_ids: Optional list of campaign IDs to filter.
            granularity: Time granularity.
            group_by: Optional fields to group by.
            timezone: Timezone for the report.

        Returns:
            The campaign report with performance metrics.
        """
        selector = None
        if campaign_ids:
            selector = {
                "conditions": [
                    {
                        "field": "campaignId",
                        "operator": "IN",
                        "values": [str(cid) for cid in campaign_ids],
                    }
                ]
            }

        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            group_by=group_by,
            selector=selector,
            timezone=timezone,
        )

        data = await self._request_async("POST", "campaigns", json=request)
        return self._parse_report_response(data)

    def ad_groups(
        self,
        campaign_id: int,
        start_date: date,
        end_date: date,
        *,
        granularity: GranularityType = GranularityType.DAILY,
        group_by: list[str] | None = None,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get an ad group-level performance report.

        Args:
            campaign_id: The campaign ID to report on.
            start_date: Report start date.
            end_date: Report end date.
            granularity: Time granularity.
            group_by: Optional fields to group by.
            timezone: Timezone for the report.

        Returns:
            The ad group report with performance metrics.
        """
        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            group_by=group_by,
            timezone=timezone,
        )

        data = self._request("POST", f"campaigns/{campaign_id}/adgroups", json=request)
        return self._parse_report_response(data)

    async def ad_groups_async(
        self,
        campaign_id: int,
        start_date: date,
        end_date: date,
        *,
        granularity: GranularityType = GranularityType.DAILY,
        group_by: list[str] | None = None,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get an ad group-level performance report asynchronously.

        Args:
            campaign_id: The campaign ID to report on.
            start_date: Report start date.
            end_date: Report end date.
            granularity: Time granularity.
            group_by: Optional fields to group by.
            timezone: Timezone for the report.

        Returns:
            The ad group report with performance metrics.
        """
        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            group_by=group_by,
            timezone=timezone,
        )

        data = await self._request_async("POST", f"campaigns/{campaign_id}/adgroups", json=request)
        return self._parse_report_response(data)

    def keywords(
        self,
        campaign_id: int,
        start_date: date,
        end_date: date,
        *,
        ad_group_ids: list[int] | None = None,
        granularity: GranularityType = GranularityType.DAILY,
        group_by: list[str] | None = None,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get a keyword-level performance report.

        Args:
            campaign_id: The campaign ID to report on.
            start_date: Report start date.
            end_date: Report end date.
            ad_group_ids: Optional list of ad group IDs to filter.
            granularity: Time granularity.
            group_by: Optional fields to group by.
            timezone: Timezone for the report.

        Returns:
            The keyword report with performance metrics.
        """
        selector = None
        if ad_group_ids:
            selector = {
                "conditions": [
                    {
                        "field": "adGroupId",
                        "operator": "IN",
                        "values": [str(agid) for agid in ad_group_ids],
                    }
                ]
            }

        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            group_by=group_by,
            selector=selector,
            timezone=timezone,
        )

        data = self._request("POST", f"campaigns/{campaign_id}/keywords", json=request)
        return self._parse_report_response(data)

    async def keywords_async(
        self,
        campaign_id: int,
        start_date: date,
        end_date: date,
        *,
        ad_group_ids: list[int] | None = None,
        granularity: GranularityType = GranularityType.DAILY,
        group_by: list[str] | None = None,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get a keyword-level performance report asynchronously.

        Args:
            campaign_id: The campaign ID to report on.
            start_date: Report start date.
            end_date: Report end date.
            ad_group_ids: Optional list of ad group IDs to filter.
            granularity: Time granularity.
            group_by: Optional fields to group by.
            timezone: Timezone for the report.

        Returns:
            The keyword report with performance metrics.
        """
        selector = None
        if ad_group_ids:
            selector = {
                "conditions": [
                    {
                        "field": "adGroupId",
                        "operator": "IN",
                        "values": [str(agid) for agid in ad_group_ids],
                    }
                ]
            }

        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            group_by=group_by,
            selector=selector,
            timezone=timezone,
        )

        data = await self._request_async("POST", f"campaigns/{campaign_id}/keywords", json=request)
        return self._parse_report_response(data)

    def search_terms(
        self,
        campaign_id: int,
        start_date: date,
        end_date: date,
        *,
        ad_group_id: int | None = None,
        granularity: GranularityType = GranularityType.DAILY,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get a search term performance report.

        Search term reports show which actual search queries triggered
        your ads and their performance.

        Args:
            campaign_id: The campaign ID to report on.
            start_date: Report start date.
            end_date: Report end date.
            ad_group_id: Optional ad group ID to filter.
            granularity: Time granularity.
            timezone: Timezone for the report.

        Returns:
            The search term report with performance metrics.
        """
        selector = None
        if ad_group_id:
            selector = {
                "conditions": [
                    {
                        "field": "adGroupId",
                        "operator": "EQUALS",
                        "values": [str(ad_group_id)],
                    }
                ]
            }

        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            selector=selector,
            timezone=timezone,
        )

        data = self._request("POST", f"campaigns/{campaign_id}/searchterms", json=request)
        return self._parse_report_response(data)

    async def search_terms_async(
        self,
        campaign_id: int,
        start_date: date,
        end_date: date,
        *,
        ad_group_id: int | None = None,
        granularity: GranularityType = GranularityType.DAILY,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Get a search term performance report asynchronously.

        Args:
            campaign_id: The campaign ID to report on.
            start_date: Report start date.
            end_date: Report end date.
            ad_group_id: Optional ad group ID to filter.
            granularity: Time granularity.
            timezone: Timezone for the report.

        Returns:
            The search term report with performance metrics.
        """
        selector = None
        if ad_group_id:
            selector = {
                "conditions": [
                    {
                        "field": "adGroupId",
                        "operator": "EQUALS",
                        "values": [str(ad_group_id)],
                    }
                ]
            }

        request = self._build_report_request(
            start_date,
            end_date,
            granularity=granularity,
            selector=selector,
            timezone=timezone,
        )

        data = await self._request_async(
            "POST", f"campaigns/{campaign_id}/searchterms", json=request
        )
        return self._parse_report_response(data)
