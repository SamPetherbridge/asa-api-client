"""Report models for the Apple Search Ads API.

This module contains models for requesting and receiving performance
reports from the Apple Search Ads API.
"""

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    import pandas as pd


class GranularityType(StrEnum):
    """Time granularity for report data.

    Attributes:
        HOURLY: Data aggregated by hour.
        DAILY: Data aggregated by day.
        WEEKLY: Data aggregated by week.
        MONTHLY: Data aggregated by month.
    """

    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class ReportGroupBy(StrEnum):
    """Grouping options for report data."""

    COUNTRY_OR_REGION = "countryOrRegion"
    COUNTRY_CODE = "countryCode"
    ADMIN_AREA = "adminArea"
    LOCALITY = "locality"
    DEVICE_CLASS = "deviceClass"
    AGE_RANGE = "ageRange"
    GENDER = "gender"


class ReportingRequest(BaseModel):
    """Request model for generating reports.

    Example:
        Request a daily campaign report::

            request = ReportingRequest(
                start_time=date(2024, 1, 1),
                end_time=date(2024, 1, 31),
                granularity=GranularityType.DAILY,
            )

            report = client.reports.campaigns(
                campaign_ids=[123, 456],
                request=request,
            )

        Request with grouping::

            request = ReportingRequest(
                start_time=date(2024, 1, 1),
                end_time=date(2024, 1, 31),
                granularity=GranularityType.DAILY,
                group_by=[ReportGroupBy.COUNTRY_OR_REGION],
            )
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    start_time: date = Field(alias="startTime")
    end_time: date = Field(alias="endTime")
    granularity: GranularityType = GranularityType.DAILY
    group_by: list[ReportGroupBy] | None = Field(default=None, alias="groupBy")
    return_grand_totals: bool = Field(default=True, alias="returnGrandTotals")
    return_records_with_no_metrics: bool = Field(default=False, alias="returnRecordsWithNoMetrics")
    return_row_totals: bool = Field(default=True, alias="returnRowTotals")
    time_zone: str = Field(default="UTC", alias="timeZone")
    selector: dict[str, Any] | None = None


class SpendRow(BaseModel):
    """Spend data for a specific time period.

    Attributes:
        amount: The spend amount.
        currency: The currency code.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: str
    currency: str


class MetricData(BaseModel):
    """Performance metrics from a report.

    Attributes:
        impressions: Number of ad impressions.
        taps: Number of taps (clicks) on ads.
        installs: Number of app installs.
        new_downloads: Number of new downloads.
        redownloads: Number of redownloads.
        lat_on_installs: Installs with LAT (Limit Ad Tracking) on.
        lat_off_installs: Installs with LAT off.
        ttr: Tap-through rate (taps / impressions).
        avg_cpa: Average cost per acquisition.
        avg_cpt: Average cost per tap.
        local_spend: Spend in local currency.
        conversion_rate: Conversion rate (installs / taps).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    impressions: int = 0
    taps: int = 0
    installs: int = 0
    new_downloads: int = Field(default=0, alias="newDownloads")
    redownloads: int = 0
    lat_on_installs: int = Field(default=0, alias="latOnInstalls")
    lat_off_installs: int = Field(default=0, alias="latOffInstalls")
    ttr: float | None = None  # Can be None when no impressions
    avg_cpa: SpendRow | None = Field(default=None, alias="avgCPA")
    avg_cpt: SpendRow | None = Field(default=None, alias="avgCPT")
    local_spend: SpendRow | None = Field(default=None, alias="localSpend")
    # Can be None when no taps
    conversion_rate: float | None = Field(default=None, alias="conversionRate")


class ReportMetadata(BaseModel):
    """Metadata about a report row.

    Contains identifiers and details about the entity the metrics
    apply to (campaign, ad group, keyword, etc.).

    Attributes:
        campaign_id: The campaign ID.
        campaign_name: The campaign name.
        ad_group_id: The ad group ID (if applicable).
        ad_group_name: The ad group name (if applicable).
        keyword_id: The keyword ID (if applicable).
        keyword: The keyword text (if applicable).
        match_type: The keyword match type (if applicable).
        country_or_region: The country/region code (if grouped).
        date: The date for this data point.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    campaign_id: int | None = Field(default=None, alias="campaignId")
    campaign_name: str | None = Field(default=None, alias="campaignName")
    campaign_status: str | None = Field(default=None, alias="campaignStatus")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    ad_group_name: str | None = Field(default=None, alias="adGroupName")
    ad_group_status: str | None = Field(default=None, alias="adGroupStatus")
    keyword_id: int | None = Field(default=None, alias="keywordId")
    keyword: str | None = None
    keyword_status: str | None = Field(default=None, alias="keywordStatus")
    match_type: str | None = Field(default=None, alias="matchType")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")
    search_term_text: str | None = Field(default=None, alias="searchTermText")
    search_term_source: str | None = Field(default=None, alias="searchTermSource")
    bid_amount: SpendRow | None = Field(default=None, alias="bidAmount")
    deleted: bool = False
    date: str | None = None


class ReportRow(BaseModel):
    """A single row of report data.

    Combines metadata about the entity with its performance metrics.

    Attributes:
        metadata: Information about the entity.
        total: The performance metrics.
        granularity: Time-granular breakdown of metrics.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    metadata: ReportMetadata
    total: MetricData | None = None
    granularity: list[MetricData] | None = None
    insights: dict[str, Any] | None = None
    other: bool = False


class GrandTotals(BaseModel):
    """Grand totals across all report rows.

    Attributes:
        total: Aggregated metrics across all rows.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    total: MetricData | None = None


class ReportingResponse(BaseModel):
    """Response from a reporting request.

    Contains the rows of report data along with grand totals
    and pagination information.

    Attributes:
        row: List of report rows.
        grand_totals: Aggregated totals across all rows.

    Example:
        Process report data::

            report = client.reports.campaigns(
                campaign_ids=[123],
                request=ReportingRequest(
                    start_time=date(2024, 1, 1),
                    end_time=date(2024, 1, 31),
                    granularity=GranularityType.DAILY,
                ),
            )

            for row in report.row:
                print(f"{row.metadata.campaign_name}: {row.total.impressions} impressions")

            # Convert to pandas DataFrame
            df = report.to_dataframe()
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    row: list[ReportRow] = Field(default_factory=list)
    grand_totals: GrandTotals | None = Field(default=None, alias="grandTotals")

    def to_dataframe(self) -> "pd.DataFrame":
        """Convert report data to a pandas DataFrame.

        This method requires pandas to be installed. Install with:
        `pip install asa-api[pandas]`

        Returns:
            A pandas DataFrame with report data flattened into rows.

        Raises:
            ImportError: If pandas is not installed.

        Example:
            Convert report to DataFrame::

                df = report.to_dataframe()
                print(df.columns)
                # ['campaign_id', 'campaign_name', 'date', 'impressions', ...]
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install asa-api[pandas]"
            ) from None

        rows_data: list[dict[str, Any]] = []

        for row in self.row:
            base_data: dict[str, Any] = {}

            # Add metadata fields
            if row.metadata:
                meta_dict = row.metadata.model_dump(by_alias=False, exclude_none=True)
                # Flatten bid_amount if present
                if meta_dict.get("bid_amount"):
                    meta_dict["bid_amount"] = meta_dict["bid_amount"].get("amount")
                base_data.update(meta_dict)

            # Add total metrics if present
            if row.total:
                total_dict = row.total.model_dump(by_alias=False, exclude_none=True)
                # Flatten spend fields
                for field in ["avg_cpa", "avg_cpt", "local_spend"]:
                    if total_dict.get(field):
                        total_dict[field] = total_dict[field].get("amount")
                base_data.update(total_dict)

            rows_data.append(base_data)

        return pd.DataFrame(rows_data)

    def to_records(self) -> list[dict[str, Any]]:
        """Convert report data to a list of dictionaries.

        This is useful when you don't want to use pandas but need
        the data in a simple format for processing.

        Returns:
            A list of dictionaries with report data.
        """
        rows_data: list[dict[str, Any]] = []

        for row in self.row:
            row_data: dict[str, Any] = {}

            if row.metadata:
                row_data["metadata"] = row.metadata.model_dump(by_alias=False, exclude_none=True)

            if row.total:
                row_data["total"] = row.total.model_dump(by_alias=False, exclude_none=True)

            if row.granularity:
                row_data["granularity"] = [
                    g.model_dump(by_alias=False, exclude_none=True) for g in row.granularity
                ]

            rows_data.append(row_data)

        return rows_data


class SearchTermReportRow(BaseModel):
    """A row in a search term report.

    Search term reports show which actual search queries triggered
    your ads.

    Attributes:
        metadata: Information about the search term.
        total: Performance metrics for this search term.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    metadata: ReportMetadata
    total: MetricData | None = None
    granularity: list[MetricData] | None = None


class ImpressionShareReportRow(BaseModel):
    """A row in an impression share report (from CSV download).

    Impression share shows how often your ads appeared compared
    to the total available impressions. Values are percentage ranges (0.0-1.0).

    Attributes:
        date: The date for this data point.
        app_name: The app name.
        adam_id: The app's adam ID.
        country_or_region: The country/region code.
        search_term: The search term that triggered impressions.
        low_impression_share: Low end of impression share range (0.0-1.0).
        high_impression_share: High end of impression share range (0.0-1.0).
        rank: Your rank (ONE, TWO, THREE, FOUR, or GREATER_THAN_FOUR).
        search_popularity: Popularity of the search term (1-5 scale).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    date: str | None = None
    app_name: str | None = Field(default=None, alias="appName")
    adam_id: str | None = Field(default=None, alias="adamId")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    search_term: str | None = Field(default=None, alias="searchTerm")
    low_impression_share: float | None = Field(default=None, alias="lowImpressionShare")
    high_impression_share: float | None = Field(default=None, alias="highImpressionShare")
    rank: str | None = None  # ONE, TWO, THREE, FOUR, GREATER_THAN_FOUR
    search_popularity: int | None = Field(default=None, alias="searchPopularity")

    @property
    def share_range_pct(self) -> str:
        """Format impression share as percentage range string."""
        if self.low_impression_share is None and self.high_impression_share is None:
            return "N/A"
        low = f"{int(self.low_impression_share * 100)}" if self.low_impression_share else "0"
        high = f"{int(self.high_impression_share * 100)}" if self.high_impression_share else "?"
        return f"{low}-{high}%"


class ImpressionShareDateRange(StrEnum):
    """Date range options for weekly impression share reports."""

    LAST_WEEK = "LAST_WEEK"
    LAST_2_WEEKS = "LAST_2_WEEKS"
    LAST_4_WEEKS = "LAST_4_WEEKS"


class ImpressionShareReportStatus(StrEnum):
    """Status of an impression share report."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImpressionShareReportRequest(BaseModel):
    """Request model for creating an impression share report.

    Impression share reports are async - you create a report request,
    then poll for results.

    Example:
        Create a daily impression share report::

            request = ImpressionShareReportRequest(
                name="my_report",
                start_time=date(2024, 1, 1),
                end_time=date(2024, 1, 31),
                granularity=GranularityType.DAILY,
            )
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = "impression_share_report"
    start_time: date = Field(alias="startTime")
    end_time: date = Field(alias="endTime")
    granularity: GranularityType = GranularityType.DAILY
    date_range: ImpressionShareDateRange | None = Field(default=None, alias="dateRange")
    selector: dict[str, Any] | None = None
    return_records_with_no_metrics: bool = Field(default=True, alias="returnRecordsWithNoMetrics")
    return_row_totals: bool = Field(default=False, alias="returnRowTotals")
    return_grand_totals: bool = Field(default=False, alias="returnGrandTotals")


class ImpressionShareReport(BaseModel):
    """An impression share report with metadata and download URL.

    Note: Impression share data is not returned inline. Once the report
    is complete, use `download_uri` to fetch the CSV data, or use the
    `get_impression_share()` convenience method which auto-downloads.

    Attributes:
        id: The report ID.
        name: The report name.
        state: Current state of the report (QUEUED, RUNNING, COMPLETED, FAILED).
        start_time: Report start date.
        end_time: Report end date.
        granularity: Time granularity (DAILY or WEEKLY).
        download_uri: URL to download the CSV data (available when complete).
        row: Parsed report rows (populated after downloading CSV).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    name: str | None = None
    state: ImpressionShareReportStatus | str = Field(alias="state")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    granularity: GranularityType | str | None = None
    date_range: str | None = Field(default=None, alias="dateRange")
    download_uri: str | None = Field(default=None, alias="downloadUri")
    row: list[ImpressionShareReportRow] = Field(default_factory=list)
    grand_totals: GrandTotals | None = Field(default=None, alias="grandTotals")

    @property
    def is_complete(self) -> bool:
        """Check if the report has finished generating."""
        return self.state == ImpressionShareReportStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if the report generation failed."""
        return self.state == ImpressionShareReportStatus.FAILED

    def to_dataframe(self) -> "pd.DataFrame":
        """Convert impression share report to a pandas DataFrame.

        Returns:
            A DataFrame with impression share data.

        Raises:
            ImportError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install with: pip install asa-api-client[pandas]"
            ) from None

        rows_data: list[dict[str, Any]] = []

        for row in self.row:
            row_data: dict[str, Any] = {
                "date": row.date,
                "app_name": row.app_name,
                "adam_id": row.adam_id,
                "country_or_region": row.country_or_region,
                "search_term": row.search_term,
                "low_impression_share": row.low_impression_share,
                "high_impression_share": row.high_impression_share,
                "rank": row.rank,
                "search_popularity": row.search_popularity,
            }
            rows_data.append(row_data)

        return pd.DataFrame(rows_data)
