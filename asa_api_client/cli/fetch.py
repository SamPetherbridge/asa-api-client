"""Async data fetching for the ``asa analyze`` command.

Owns everything network-shaped against the Apple Ads Platform API v1:
scope resolution, chunked report fetching with bounded concurrency and
auto-pagination, the prior-period comparison fetch, and flattening v1
report rows into daily DataFrames.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import pandas as pd

from asa_api_client.cli.dates import SEARCH_TERM_LOOKBACK, chunk_windows, prior_window
from asa_api_client.exceptions import AppleAdsError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.campaigns import Campaign, PromotedObjectType
from asa_api_client.v1.models.reports import (
    AppsAdGroupReportRow,
    AppsAdReportRow,
    AppsCampaignReportRow,
    AppsKeywordReportRow,
    AppsMetrics,
    AppsReportingAd,
    AppsReportingAdGroup,
    AppsReportingCampaign,
    AppsReportingRequest,
    AppsSearchTermReportRow,
    ReportFilter,
    ReportFilterOperator,
    ReportGranularity,
    ReportingKeyword,
    ReportingSearchTerm,
    ReportTimeRange,
    ReportTimeZone,
)

LEVELS: list[tuple[str, str]] = [
    ("campaigns", "Campaigns"),
    ("ad_groups", "Ad Groups"),
    ("keywords", "Keywords"),
    ("search_terms", "Search Terms"),
    ("ads", "Ads"),
]
LEVEL_LABELS = dict(LEVELS)
CONCURRENCY = 5
_REPORT_PAGE_SIZE = 5000
_APP_SEARCH_LIMIT = 500


class ScopeError(Exception):
    """No campaigns matched the requested scope."""


class LevelFetchError(Exception):
    """An entire reporting level failed to fetch."""


@dataclass
class LevelData:
    """Fetched daily data for one reporting level."""

    label: str
    daily: pd.DataFrame
    notes: list[str] = field(default_factory=list)


@dataclass
class FetchResult:
    """Everything fetched for one analyze run."""

    levels: dict[str, LevelData]
    prior_campaigns: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


def _enum_str(value: Any) -> str | None:
    """Return an enum/string value as a plain string, or None."""
    return None if value is None else str(value)


def _campaign_metadata(meta: AppsReportingCampaign | None) -> dict[str, object]:
    """Map v1 campaign report metadata to normalized snake_case columns."""
    if meta is None:
        return {}
    return {
        "campaign_id": meta.id,
        "campaign_name": meta.name,
        "campaign_status": _enum_str(meta.status),
        "deleted": meta.deleted,
    }


def _ad_group_metadata(meta: AppsReportingAdGroup | None) -> dict[str, object]:
    """Map v1 ad group report metadata to normalized snake_case columns."""
    if meta is None:
        return {}
    return {
        "campaign_id": meta.campaign_id,
        "ad_group_id": meta.id,
        "ad_group_name": meta.name,
        "ad_group_status": _enum_str(meta.status),
        "deleted": meta.deleted,
    }


def _keyword_metadata(meta: ReportingKeyword | None) -> dict[str, object]:
    """Map v1 keyword report metadata to normalized snake_case columns."""
    if meta is None:
        return {}
    return {
        "campaign_id": meta.campaign_id,
        "ad_group_id": meta.ad_group_id,
        "ad_group_name": meta.ad_group.name if meta.ad_group else None,
        "keyword_id": meta.id,
        "keyword": meta.text,
        "keyword_status": _enum_str(meta.status),
        "match_type": _enum_str(meta.match_type),
        "bid_amount": meta.bid.amount if meta.bid else None,
        "deleted": meta.deleted,
    }


def _search_term_metadata(meta: ReportingSearchTerm | None) -> dict[str, object]:
    """Map v1 search term report metadata to normalized snake_case columns."""
    if meta is None:
        return {}
    keyword = meta.keyword
    return {
        "campaign_id": meta.campaign_id,
        "ad_group_id": meta.ad_group_id,
        "ad_group_name": meta.ad_group.name if meta.ad_group else None,
        "search_term_text": meta.search_term_text,
        "search_term_source": meta.search_term_source,
        "keyword_id": keyword.id if keyword else None,
        "keyword": keyword.text if keyword else None,
        "match_type": _enum_str(keyword.match_type) if keyword else None,
    }


def _ad_metadata(meta: AppsReportingAd | None) -> dict[str, object]:
    """Map v1 ad report metadata to normalized snake_case columns."""
    if meta is None:
        return {}
    creative = meta.creative
    return {
        "campaign_id": meta.campaign_id,
        "ad_group_id": meta.ad_group_id,
        "ad_id": meta.id,
        "ad_name": meta.name,
        "ad_display_status": _enum_str(meta.display_status),
        "creative_id": creative.id if creative else None,
        "creative_type": _enum_str(creative.creative_type) if creative else None,
        "language": (
            creative.creative_spec.language if creative and creative.creative_spec else None
        ),
        "deleted": meta.deleted,
    }


def _metric_dict(entry: AppsMetrics) -> dict[str, object]:
    """Flatten one ``AppsMetrics`` object into scalar snake_case columns."""
    raw = entry.model_dump(by_alias=False, exclude_none=True, mode="json")
    for v1_key, col_key in (("cpt", "avg_cpt"), ("cpm", "avg_cpm")):
        if v1_key in raw:
            raw[col_key] = raw.pop(v1_key)
    for key, value in list(raw.items()):
        if isinstance(value, dict) and "amount" in value:
            raw[key] = value.get("amount")
    return raw


def flatten_rows(
    rows: Sequence[Any],
    metadata_fn: Callable[[Any], dict[str, object]],
) -> pd.DataFrame:
    """Flatten typed v1 report rows into one DataFrame row per entity-day.

    Uses each row's ``granular_metrics`` breakdown (falling back to
    ``total_metrics`` when absent) so DAILY reports preserve per-day
    resolution.

    Args:
        rows: Sequence of v1 report row models.
        metadata_fn: Callable mapping ``row.metadata`` to snake_case fields.

    Returns:
        A DataFrame with snake_case metadata and metric columns.
    """
    records: list[dict[str, object]] = []
    for row in rows:
        meta = {k: v for k, v in metadata_fn(row.metadata).items() if v is not None}
        entries: Sequence[AppsMetrics] = row.granular_metrics or (
            [row.total_metrics] if row.total_metrics is not None else []
        )
        for entry in entries:
            records.append({**meta, **_metric_dict(entry)})
    return pd.DataFrame(records)


def _time_range(
    start: date, end: date, timezone: str, *, force_ortz: bool = False
) -> ReportTimeRange:
    """Build a DAILY v1 report time range."""
    utc = timezone.upper() == "UTC" and not force_ortz
    return ReportTimeRange(
        start=start,
        end=end,
        time_zone=ReportTimeZone.UTC if utc else ReportTimeZone.ORTZ,
        granularity=ReportGranularity.DAILY,
    )


def _campaign_filter(campaign_id: int) -> list[ReportFilter]:
    """Build a single-campaign sub-entity report filter."""
    return [
        ReportFilter(
            field="campaignId",
            operator=ReportFilterOperator.EQUALS,
            value=str(campaign_id),
        )
    ]


def _extract_app_campaign(
    campaign: Campaign,
) -> tuple[int | None, str | None, int, str | None] | None:
    """Extract ``(id, name, adam_id, currency)`` for an App Store campaign."""
    if campaign.promoted_object_type is not PromotedObjectType.APPSTORE_APP:
        return None
    try:
        adam_id = int(campaign.promoted_object_id or "")
    except ValueError:
        return None
    currency = (
        campaign.daily_budget.value.currency
        if campaign.daily_budget and campaign.daily_budget.value
        else None
    )
    return campaign.id, campaign.name, adam_id, currency


def _app_names(client: AppleAdsClient, adam_ids: list[int]) -> dict[int, str]:
    """Best-effort lookup of app names for the account's adam IDs."""
    names: dict[int, str] = {}
    try:
        for info in client.apps.search(
            query=None,
            return_owned_apps=True,
            limit=_APP_SEARCH_LIMIT,
        ):
            if info.adam_id is not None and info.app_name:
                names[int(info.adam_id)] = info.app_name
    except Exception:  # purely cosmetic lookup, never fatal
        names = {}
    return {adam: names.get(adam, f"App {adam}") for adam in adam_ids}


def resolve_scope(
    client: AppleAdsClient, app_ids: list[int] | None
) -> tuple[pd.DataFrame, str | None]:
    """List App Store campaigns once and build the campaign → app scope map.

    Apple Maps (``BUSINESS_BRAND``) campaigns are skipped because the
    App Store report endpoints do not return rows for them.

    Args:
        client: Configured v1 API client.
        app_ids: Adam IDs to scope to, or None for all apps in the account.

    Returns:
        Tuple of ``(meta_df, currency_code)``.

    Raises:
        ScopeError: If no App Store campaigns match the requested scope.
    """
    extracted = [
        item
        for raw in client.campaigns.iter_all()
        if (item := _extract_app_campaign(raw)) is not None
    ]
    if app_ids:
        wanted = set(app_ids)
        extracted = [c for c in extracted if c[2] in wanted]
    if not extracted:
        detail = f" for app(s) {sorted(set(app_ids))}" if app_ids else ""
        raise ScopeError(f"No campaigns found{detail}")

    currency = next((c[3] for c in extracted if c[3] is not None), None)
    adam_ids = sorted({c[2] for c in extracted})
    names = _app_names(client, adam_ids)
    meta = pd.DataFrame(
        [
            {
                "campaign_id": cid,
                "campaign_name": cname,
                "adam_id": adam_id,
                "app_name": names[adam_id],
            }
            for cid, cname, adam_id, _ in extracted
        ]
    )
    return meta, currency


def _merge_names(df: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Join campaign/app names onto a level frame by ``campaign_id``."""
    if df.empty or "campaign_id" not in df.columns:
        return df
    df = df.drop(columns=[c for c in ("campaign_name", "app_name", "adam_id") if c in df.columns])
    return df.merge(meta, on="campaign_id", how="left")


async def _collect_async(aiter: AsyncIterator[Any]) -> list[Any]:
    """Drain an async report iterator into a list."""
    return [row async for row in aiter]


async def _fetch_campaigns_frame(
    client: AppleAdsClient,
    start_date: date,
    end_date: date,
    *,
    campaign_ids: list[int] | None,
    timezone: str,
) -> pd.DataFrame:
    """Fetch and flatten a campaign-level daily report across all pages."""
    filters = (
        [
            ReportFilter(
                field="id",
                operator=ReportFilterOperator.IN,
                value=[str(cid) for cid in campaign_ids],
            )
        ]
        if campaign_ids
        else None
    )
    request = AppsReportingRequest(
        filters=filters,
        time_range=_time_range(start_date, end_date, timezone),
    )
    rows: list[AppsCampaignReportRow] = await _collect_async(
        client.reports.iter_campaigns_async(request, page_size=_REPORT_PAGE_SIZE)
    )
    return flatten_rows(rows, _campaign_metadata)


async def _fetch_ad_groups_frame(
    client: AppleAdsClient, campaign_id: int, start_date: date, end_date: date, *, timezone: str
) -> pd.DataFrame:
    """Fetch and flatten an ad-group-level daily report for one campaign."""
    request = AppsReportingRequest(
        filters=_campaign_filter(campaign_id),
        time_range=_time_range(start_date, end_date, timezone),
    )
    rows: list[AppsAdGroupReportRow] = await _collect_async(
        client.reports.iter_ad_groups_async(request, page_size=_REPORT_PAGE_SIZE)
    )
    return flatten_rows(rows, _ad_group_metadata)


async def _fetch_keywords_frame(
    client: AppleAdsClient, campaign_id: int, start_date: date, end_date: date, *, timezone: str
) -> pd.DataFrame:
    """Fetch and flatten a keyword-level daily report for one campaign."""
    request = AppsReportingRequest(
        filters=_campaign_filter(campaign_id),
        time_range=_time_range(start_date, end_date, timezone),
    )
    rows: list[AppsKeywordReportRow] = await _collect_async(
        client.reports.iter_keywords_async(request, page_size=_REPORT_PAGE_SIZE)
    )
    return flatten_rows(rows, _keyword_metadata)


async def _fetch_search_terms_frame(
    client: AppleAdsClient, campaign_id: int, start_date: date, end_date: date, *, timezone: str
) -> pd.DataFrame:
    """Fetch and flatten a search-term-level daily report (always ORTZ)."""
    request = AppsReportingRequest(
        filters=_campaign_filter(campaign_id),
        time_range=_time_range(start_date, end_date, timezone, force_ortz=True),
    )
    rows: list[AppsSearchTermReportRow] = await _collect_async(
        client.reports.iter_search_terms_async(request, page_size=_REPORT_PAGE_SIZE)
    )
    return flatten_rows(rows, _search_term_metadata)


async def _fetch_ads_frame(
    client: AppleAdsClient, campaign_id: int, start_date: date, end_date: date, *, timezone: str
) -> pd.DataFrame:
    """Fetch and flatten an ad-level daily report for one campaign."""
    request = AppsReportingRequest(
        filters=_campaign_filter(campaign_id),
        time_range=_time_range(start_date, end_date, timezone),
    )
    rows: list[AppsAdReportRow] = await _collect_async(
        client.reports.iter_ads_async(request, page_size=_REPORT_PAGE_SIZE)
    )
    return flatten_rows(rows, _ad_metadata)


async def fetch_all(
    client: AppleAdsClient,
    meta: pd.DataFrame,
    start: date,
    end: date,
    *,
    timezone: str = "UTC",
    today: date,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> FetchResult:
    """Fetch all five reporting levels plus the prior campaign period.

    Args:
        client: Configured v1 API client.
        meta: Scope frame from :func:`resolve_scope`.
        start: Range start (inclusive).
        end: Range end (inclusive).
        timezone: Reporting timezone (``"UTC"`` or ``"ORTZ"``).
        today: Current date (drives the 90-day search-term lookback clip).
        on_progress: Optional callback ``(level_key, completed, total)``.

    Returns:
        A :class:`FetchResult` with per-level daily frames (names merged
        on), the prior-period campaign frame, and accumulated warnings.

    Raises:
        LevelFetchError: If the current-period campaign window fails, or
            every chunk of any other level fails.
    """
    windows = chunk_windows(start, end)
    p_start, p_end = prior_window(start, end)
    prior_windows = chunk_windows(p_start, p_end)
    campaign_ids = [int(c) for c in meta["campaign_id"].tolist()]

    st_start = max(start, today - timedelta(days=SEARCH_TERM_LOOKBACK))
    st_out_of_range = st_start > end
    st_windows = [] if st_out_of_range else chunk_windows(st_start, end)
    st_clipped = st_start > start and not st_out_of_range

    per_campaign: dict[str, Callable[[int, date, date], Awaitable[pd.DataFrame]]] = {
        "ad_groups": lambda cid, s, e: _fetch_ad_groups_frame(client, cid, s, e, timezone=timezone),
        "keywords": lambda cid, s, e: _fetch_keywords_frame(client, cid, s, e, timezone=timezone),
        "search_terms": lambda cid, s, e: _fetch_search_terms_frame(
            client, cid, s, e, timezone=timezone
        ),
        "ads": lambda cid, s, e: _fetch_ads_frame(client, cid, s, e, timezone=timezone),
    }
    level_windows = {key: st_windows if key == "search_terms" else windows for key in per_campaign}

    totals: dict[str, int] = {"campaigns": len(windows) + len(prior_windows)}
    totals |= {key: len(level_windows[key]) * len(campaign_ids) for key in per_campaign}
    done = dict.fromkeys(totals, 0)

    if on_progress is not None:
        for level, total in totals.items():
            if total == 0:
                on_progress(level, 0, 0)

    semaphore = asyncio.Semaphore(CONCURRENCY)
    warnings: list[str] = []
    frames: dict[str, list[pd.DataFrame]] = {key: [] for key, _ in LEVELS}
    prior_frames: list[pd.DataFrame] = []
    notes: dict[str, list[str]] = {key: [] for key, _ in LEVELS}
    failures: dict[str, int] = dict.fromkeys(totals, 0)

    def _tick(level: str) -> None:
        done[level] += 1
        if on_progress is not None:
            on_progress(level, done[level], totals[level])

    async def _campaign_window(win: tuple[date, date], *, prior: bool) -> None:
        async with semaphore:
            try:
                frame = await _fetch_campaigns_frame(
                    client, win[0], win[1], campaign_ids=campaign_ids, timezone=timezone
                )
            except AppleAdsError as exc:
                if prior:
                    warnings.append(
                        f"Prior period: window {win[0]}-{win[1]} failed: {exc}; "
                        "prior-period deltas omitted"
                    )
                    return
                raise LevelFetchError(
                    f"Campaigns report failed for {win[0]}-{win[1]}: {exc}"
                ) from exc
            finally:
                _tick("campaigns")
            (prior_frames if prior else frames["campaigns"]).append(frame)

    async def _chunk(level: str, cid: int, win: tuple[date, date]) -> None:
        label = LEVEL_LABELS[level]
        async with semaphore:
            try:
                frame = await per_campaign[level](cid, win[0], win[1])
            except AppleAdsError as exc:
                failures[level] += 1
                message = f"{label}: campaign {cid} window {win[0]}-{win[1]} failed: {exc}"
                warnings.append(message)
                notes[level].append(message)
                return
            finally:
                _tick(level)
            frames[level].append(frame)

    tasks: list[Awaitable[None]] = []
    tasks += [_campaign_window(win, prior=False) for win in windows]
    tasks += [_campaign_window(win, prior=True) for win in prior_windows]
    for level in per_campaign:
        tasks += [_chunk(level, cid, win) for cid in campaign_ids for win in level_windows[level]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for outcome in results:
        if isinstance(outcome, BaseException):
            raise outcome

    if st_out_of_range:
        notes["search_terms"].insert(
            0,
            "Search terms are only available for the trailing 90 days; "
            "no search-term data is available for this range.",
        )
    elif st_clipped:
        notes["search_terms"].insert(
            0,
            "Search terms are only available for the trailing 90 days; "
            f"this sheet covers {st_start}-{end}.",
        )
    if not st_out_of_range and timezone.upper() == "UTC":
        notes["search_terms"].append(
            "Search-term rows use the org's reporting timezone; "
            "the API does not support UTC at this level."
        )

    levels: dict[str, LevelData] = {}
    for key, label in LEVELS:
        if key != "campaigns" and failures[key] and not frames[key]:
            raise LevelFetchError(f"{label}: every request failed; first error: {notes[key][0]}")
        daily = pd.concat(frames[key], ignore_index=True) if frames[key] else pd.DataFrame()
        levels[key] = LevelData(label=label, daily=_merge_names(daily, meta), notes=notes[key])

    prior = pd.concat(prior_frames, ignore_index=True) if prior_frames else pd.DataFrame()
    return FetchResult(levels=levels, prior_campaigns=prior, warnings=warnings)
