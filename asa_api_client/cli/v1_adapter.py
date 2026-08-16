"""Adapter running the analyze fetch pipeline against the Platform API v1.

:class:`V1FetchAdapter` wraps a v1
:class:`~asa_api_client.v1.client.AppleAdsClient` and exposes exactly
the narrow client surface ``cli/fetch.py`` consumes (see
:class:`~asa_api_client.cli.fetch.FetchClient`): an app search, a
campaign listing, and the five async report levels. Report responses
are converted into genuine v5
:class:`~asa_api_client.models.reports.ReportingResponse` instances so
everything downstream of the fetch layer is untouched.

Mapping notes:

- ``adam_id`` is derived from a campaign's ``promotedObjectId`` when
  ``promotedObjectType`` is ``APPSTORE_APP``; Apple Maps
  (``BUSINESS_BRAND``) campaigns are skipped because the App Store
  report endpoints never return rows for them.
- v1 metric names map onto their v5 aliases one-for-one except
  ``cpt``/``cpm``, which become ``avgCPT``/``avgCPM``.
- v1 campaigns have no lifetime budget field, so ``budget_amount`` is
  always ``None`` (the pipeline only uses it as a currency fallback).
"""

from collections.abc import Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from asa_api_client.models.reports import ReportingResponse
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.campaigns import Campaign, PromotedObjectType
from asa_api_client.v1.models.reports import (
    AppsMetrics,
    AppsReportingAd,
    AppsReportingAdGroup,
    AppsReportingCampaign,
    AppsReportingRequest,
    ReportFilter,
    ReportFilterOperator,
    ReportGranularity,
    ReportingKeyword,
    ReportingSearchTerm,
    ReportTimeRange,
    ReportTimeZone,
    RequestPagination,
)

if TYPE_CHECKING:
    from asa_api_client.v1.models.apps import AppInfo
    from asa_api_client.v1.models.base import Money, V1Pagination

_REPORT_PAGE_SIZE = 5000
_APP_SEARCH_LIMIT = 500

_RowT_co = TypeVar("_RowT_co", covariant=True)


class _V1ResultLike(Protocol[_RowT_co]):
    """Structural view of a v1 report result container."""

    @property
    def rows(self) -> Sequence[_RowT_co] | None:
        """The report rows, if any."""
        ...


class _V1ResponseLike(Protocol[_RowT_co]):
    """Structural view of a v1 report response envelope."""

    @property
    def result(self) -> _V1ResultLike[_RowT_co] | None:
        """The result container."""
        ...

    @property
    def pagination(self) -> "V1Pagination | None":
        """Pagination metadata."""
        ...


@dataclass(frozen=True)
class CampaignSummary:
    """The campaign fields the analyze scope resolution consumes.

    Attributes:
        id: The campaign ID.
        name: The campaign name.
        adam_id: The promoted App Store app's adam ID.
        daily_budget_amount: The daily budget, if set.
        budget_amount: The lifetime budget; always None for v1 (the API
            has no campaign-level lifetime budget field).
    """

    id: int | None
    name: str | None
    adam_id: int
    daily_budget_amount: "Money | None"
    budget_amount: "Money | None" = None


def _enum_str(value: Any) -> str | None:
    """Return an enum/string value as a plain string, or None.

    Args:
        value: A StrEnum member, string, or None.

    Returns:
        The string value, or None when the input is None.
    """
    return None if value is None else str(value)


def _money_payload(money: "Money | None") -> dict[str, str] | None:
    """Convert a v1 Money into a v5 SpendRow-shaped dict.

    Args:
        money: The v1 monetary value, or None.

    Returns:
        An ``{"amount", "currency"}`` dict, or None.
    """
    if money is None:
        return None
    return {"amount": money.amount, "currency": money.currency}


def _metrics_payload(metrics: AppsMetrics | None) -> dict[str, Any] | None:
    """Convert v1 APPS metrics into a v5 MetricData-shaped dict.

    The v1 aliases match v5 one-for-one except ``cpt``/``cpm``, which
    v5 names ``avgCPT``/``avgCPM``.

    Args:
        metrics: One v1 metrics object (total or granular), or None.

    Returns:
        A dict parseable by the v5 ``MetricData`` model, or None.
    """
    if metrics is None:
        return None
    data = metrics.model_dump(by_alias=True, exclude_none=True, mode="json")
    for v1_name, v5_name in (("cpt", "avgCPT"), ("cpm", "avgCPM")):
        if v1_name in data:
            data[v5_name] = data.pop(v1_name)
    return data


def _campaign_metadata(meta: AppsReportingCampaign | None) -> dict[str, Any]:
    """Map v1 campaign report metadata onto v5 metadata fields."""
    if meta is None:
        return {}
    return {
        "campaignId": meta.id,
        "campaignName": meta.name,
        "campaignStatus": _enum_str(meta.status),
        "deleted": meta.deleted,
    }


def _ad_group_metadata(meta: AppsReportingAdGroup | None) -> dict[str, Any]:
    """Map v1 ad group report metadata onto v5 metadata fields."""
    if meta is None:
        return {}
    return {
        "campaignId": meta.campaign_id,
        "adGroupId": meta.id,
        "adGroupName": meta.name,
        "adGroupStatus": _enum_str(meta.status),
        "deleted": meta.deleted,
    }


def _keyword_metadata(meta: ReportingKeyword | None) -> dict[str, Any]:
    """Map v1 keyword report metadata onto v5 metadata fields."""
    if meta is None:
        return {}
    return {
        "campaignId": meta.campaign_id,
        "adGroupId": meta.ad_group_id,
        "adGroupName": meta.ad_group.name if meta.ad_group else None,
        "keywordId": meta.id,
        "keyword": meta.text,
        "keywordStatus": _enum_str(meta.status),
        "matchType": _enum_str(meta.match_type),
        "bidAmount": _money_payload(meta.bid),
        "deleted": meta.deleted,
    }


def _search_term_metadata(meta: ReportingSearchTerm | None) -> dict[str, Any]:
    """Map v1 search term report metadata onto v5 metadata fields."""
    if meta is None:
        return {}
    keyword = meta.keyword
    return {
        "campaignId": meta.campaign_id,
        "adGroupId": meta.ad_group_id,
        "adGroupName": meta.ad_group.name if meta.ad_group else None,
        "searchTermText": meta.search_term_text,
        "searchTermSource": meta.search_term_source,
        "keywordId": keyword.id if keyword else None,
        "keyword": keyword.text if keyword else None,
        "matchType": _enum_str(keyword.match_type) if keyword else None,
    }


def _ad_metadata(meta: AppsReportingAd | None) -> dict[str, Any]:
    """Map v1 ad report metadata onto v5 metadata fields."""
    if meta is None:
        return {}
    creative = meta.creative
    return {
        "campaignId": meta.campaign_id,
        "adGroupId": meta.ad_group_id,
        "adId": meta.id,
        "adName": meta.name,
        "adDisplayStatus": _enum_str(meta.display_status),
        "creativeId": creative.id if creative else None,
        "creativeType": _enum_str(creative.creative_type) if creative else None,
        "language": (
            creative.creative_spec.language if creative and creative.creative_spec else None
        ),
        "deleted": meta.deleted,
    }


def _row_payload(
    metadata: dict[str, Any],
    total: AppsMetrics | None,
    granular: Sequence[AppsMetrics] | None,
) -> dict[str, Any]:
    """Build one v5 report row dict from converted v1 pieces.

    Args:
        metadata: v5-aliased metadata fields (None values dropped).
        total: The v1 total metrics, if present.
        granular: The v1 per-period metrics, if present.

    Returns:
        A dict parseable by the v5 ``ReportRow`` model.
    """
    payload: dict[str, Any] = {
        "metadata": {key: value for key, value in metadata.items() if value is not None}
    }
    total_payload = _metrics_payload(total)
    if total_payload is not None:
        payload["total"] = total_payload
    if granular:
        payload["granularity"] = [_metrics_payload(entry) for entry in granular]
    return payload


def _time_range(
    start: date, end: date, timezone: str, *, force_ortz: bool = False
) -> ReportTimeRange:
    """Build a DAILY v1 report time range from the v5-style arguments.

    Args:
        start: Range start (inclusive).
        end: Range end (inclusive).
        timezone: The v5-style timezone string ("UTC" or other).
        force_ortz: Force ORTZ regardless of ``timezone`` (search term
            reports only support ORTZ).

    Returns:
        The v1 time range with daily granularity.
    """
    utc = timezone.upper() == "UTC" and not force_ortz
    return ReportTimeRange(
        start=start,
        end=end,
        time_zone=ReportTimeZone.UTC if utc else ReportTimeZone.ORTZ,
        granularity=ReportGranularity.DAILY,
    )


def _campaign_filter(campaign_id: int) -> list[ReportFilter]:
    """Build the single-campaign report filter."""
    return [
        ReportFilter(
            field="campaignId", operator=ReportFilterOperator.EQUALS, value=str(campaign_id)
        )
    ]


class _AppsShim:
    """Maps the v5 ``apps.search`` call onto v1 app search."""

    def __init__(self, client: AppleAdsClient) -> None:
        """Store the wrapped v1 client.

        Args:
            client: The v1 API client.
        """
        self._client = client

    def search(self, *, query: str = "", return_own_apps: bool = False) -> "list[AppInfo]":
        """Search apps, mapping the v5 parameter names onto v1.

        An empty ``query`` is dropped (v1 rejects short queries) and
        ``return_own_apps`` becomes v1's ``returnOwnedApps``.

        Args:
            query: Free-text search; empty means "own apps only".
            return_own_apps: Restrict to apps owned by the organization.

        Returns:
            The matching apps; items expose ``adam_id``/``app_name``.
        """
        page = self._client.apps.search(
            query=query or None,
            return_owned_apps=True if return_own_apps else None,
            limit=_APP_SEARCH_LIMIT,
        )
        return list(page)


class _CampaignsShim:
    """Maps the v5 ``campaigns.list`` call onto the v1 query endpoint."""

    def __init__(self, client: AppleAdsClient) -> None:
        """Store the wrapped v1 client.

        Args:
            client: The v1 API client.
        """
        self._client = client

    def list(self) -> Iterator[CampaignSummary]:
        """Yield App Store campaigns in the shape the fetch layer expects.

        Apple Maps (``BUSINESS_BRAND``) campaigns are skipped: the App
        Store report endpoints never return rows for them and they have
        no adam ID.

        Yields:
            One :class:`CampaignSummary` per App Store campaign.
        """
        for campaign in self._client.campaigns.iter_all():
            summary = _campaign_summary(campaign)
            if summary is not None:
                yield summary


def _campaign_summary(campaign: Campaign) -> CampaignSummary | None:
    """Map a v1 campaign to a summary, or None when not an app campaign.

    Args:
        campaign: The v1 campaign read model.

    Returns:
        The mapped summary, or None for non-App-Store campaigns or ones
        whose ``promotedObjectId`` is not a numeric adam ID.
    """
    if campaign.promoted_object_type is not PromotedObjectType.APPSTORE_APP:
        return None
    try:
        adam_id = int(campaign.promoted_object_id or "")
    except ValueError:
        return None
    daily_budget = campaign.daily_budget.value if campaign.daily_budget else None
    return CampaignSummary(
        id=campaign.id,
        name=campaign.name,
        adam_id=adam_id,
        daily_budget_amount=daily_budget,
    )


class _ReportsShim:
    """Runs v1 report queries and converts them to v5 responses."""

    def __init__(self, client: AppleAdsClient) -> None:
        """Store the wrapped v1 client.

        Args:
            client: The v1 API client.
        """
        self._client = client

    async def _paged(
        self,
        run: "Callable[[AppsReportingRequest], Awaitable[_V1ResponseLike[_RowT_co]]]",
        *,
        filters: list[ReportFilter] | None,
        time_range: ReportTimeRange,
    ) -> list[_RowT_co]:
        """Collect every row of a v1 report across pagination.

        Args:
            run: The bound v1 async report method to call per page.
            filters: Report filters, or None for no filtering.
            time_range: The daily time range to report over.

        Returns:
            All rows from every page, in order.
        """
        rows: list[_RowT_co] = []
        offset = 0
        while True:
            request = AppsReportingRequest(
                filters=filters,
                time_range=time_range,
                pagination=RequestPagination(offset=offset, page_size=_REPORT_PAGE_SIZE),
            )
            response = await run(request)
            page = list(response.result.rows or []) if response.result else []
            rows.extend(page)
            total = response.pagination.total_count if response.pagination else None
            if not page:
                return rows
            if total is not None and offset + len(page) >= total:
                return rows
            # No total count reported: a short page means we're done.
            if total is None and len(page) < _REPORT_PAGE_SIZE:
                return rows
            offset += len(page)

    async def campaigns_async(
        self,
        start_date: date,
        end_date: date,
        *,
        campaign_ids: list[int] | None = None,
        timezone: str = "UTC",
    ) -> ReportingResponse:
        """Run a campaign-level daily report and convert it to v5 shape.

        Args:
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).
            campaign_ids: Campaigns to include, or None for all.
            timezone: "UTC" or an ORTZ-style timezone.

        Returns:
            A v5 ReportingResponse with per-day granularity rows.
        """
        filters = None
        if campaign_ids:
            filters = [
                ReportFilter(
                    field="campaignId",
                    operator=ReportFilterOperator.IN,
                    value=[str(cid) for cid in campaign_ids],
                )
            ]
        rows = await self._paged(
            self._client.reports.campaigns_async,
            filters=filters,
            time_range=_time_range(start_date, end_date, timezone),
        )
        return ReportingResponse.model_validate(
            {
                "row": [
                    _row_payload(
                        _campaign_metadata(row.metadata), row.total_metrics, row.granular_metrics
                    )
                    for row in rows
                ]
            }
        )

    async def ad_groups_async(
        self, campaign_id: int, start_date: date, end_date: date, *, timezone: str = "UTC"
    ) -> ReportingResponse:
        """Run an ad-group-level daily report for one campaign.

        Args:
            campaign_id: The campaign to report on.
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).
            timezone: "UTC" or an ORTZ-style timezone.

        Returns:
            A v5 ReportingResponse with per-day granularity rows.
        """
        rows = await self._paged(
            self._client.reports.ad_groups_async,
            filters=_campaign_filter(campaign_id),
            time_range=_time_range(start_date, end_date, timezone),
        )
        return ReportingResponse.model_validate(
            {
                "row": [
                    _row_payload(
                        _ad_group_metadata(row.metadata), row.total_metrics, row.granular_metrics
                    )
                    for row in rows
                ]
            }
        )

    async def keywords_async(
        self, campaign_id: int, start_date: date, end_date: date, *, timezone: str = "UTC"
    ) -> ReportingResponse:
        """Run a keyword-level daily report for one campaign.

        Args:
            campaign_id: The campaign to report on.
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).
            timezone: "UTC" or an ORTZ-style timezone.

        Returns:
            A v5 ReportingResponse with per-day granularity rows.
        """
        rows = await self._paged(
            self._client.reports.keywords_async,
            filters=_campaign_filter(campaign_id),
            time_range=_time_range(start_date, end_date, timezone),
        )
        return ReportingResponse.model_validate(
            {
                "row": [
                    _row_payload(
                        _keyword_metadata(row.metadata), row.total_metrics, row.granular_metrics
                    )
                    for row in rows
                ]
            }
        )

    async def search_terms_async(
        self, campaign_id: int, start_date: date, end_date: date, *, timezone: str = "UTC"
    ) -> ReportingResponse:
        """Run a search-term-level daily report for one campaign.

        v1 search term reports only support the ORTZ timezone, so the
        ``timezone`` argument is ignored and ORTZ is always used.

        Args:
            campaign_id: The campaign to report on.
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).
            timezone: Accepted for interface parity; always ORTZ.

        Returns:
            A v5 ReportingResponse with per-day granularity rows.
        """
        rows = await self._paged(
            self._client.reports.search_terms_async,
            filters=_campaign_filter(campaign_id),
            time_range=_time_range(start_date, end_date, timezone, force_ortz=True),
        )
        return ReportingResponse.model_validate(
            {
                "row": [
                    _row_payload(
                        _search_term_metadata(row.metadata),
                        row.total_metrics,
                        row.granular_metrics,
                    )
                    for row in rows
                ]
            }
        )

    async def ads_async(
        self, campaign_id: int, start_date: date, end_date: date, *, timezone: str = "UTC"
    ) -> ReportingResponse:
        """Run an ad-level daily report for one campaign.

        Args:
            campaign_id: The campaign to report on.
            start_date: Range start (inclusive).
            end_date: Range end (inclusive).
            timezone: "UTC" or an ORTZ-style timezone.

        Returns:
            A v5 ReportingResponse with per-day granularity rows.
        """
        rows = await self._paged(
            self._client.reports.ads_async,
            filters=_campaign_filter(campaign_id),
            time_range=_time_range(start_date, end_date, timezone),
        )
        return ReportingResponse.model_validate(
            {
                "row": [
                    _row_payload(
                        _ad_metadata(row.metadata), row.total_metrics, row.granular_metrics
                    )
                    for row in rows
                ]
            }
        )


class V1FetchAdapter:
    """Presents a v1 AppleAdsClient through the fetch-client surface.

    Satisfies :class:`~asa_api_client.cli.fetch.FetchClient`, so the
    analyze pipeline runs unchanged against the Platform API v1.

    Attributes:
        apps: App search shim.
        campaigns: Campaign listing shim.
        reports: Report shims returning v5 ``ReportingResponse``.
    """

    apps: _AppsShim
    campaigns: _CampaignsShim
    reports: _ReportsShim

    def __init__(self, client: AppleAdsClient) -> None:
        """Wrap a v1 client.

        Args:
            client: The configured v1 API client.
        """
        self._client = client
        self.apps = _AppsShim(client)
        self.campaigns = _CampaignsShim(client)
        self.reports = _ReportsShim(client)

    def close(self) -> None:
        """Close the wrapped client's HTTP resources."""
        self._client.close()

    async def aclose(self) -> None:
        """Close the wrapped client's HTTP resources asynchronously."""
        await self._client.aclose()
