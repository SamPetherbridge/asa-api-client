"""Async data fetching for the analyze command.

Owns everything network-shaped: scope resolution, chunked report
fetching with bounded concurrency, the prior-period comparison fetch,
and flattening API responses into daily DataFrames.
"""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

import pandas as pd

from asa_api_client.cli.dates import SEARCH_TERM_LOOKBACK, chunk_windows, prior_window
from asa_api_client.exceptions import AppleSearchAdsError
from asa_api_client.models.reports import ReportingResponse


class MoneyLike(Protocol):
    """Anything money-shaped with a currency code."""

    @property
    def currency(self) -> str:
        """ISO currency code."""
        ...


class AppListing(Protocol):
    """One app search result."""

    @property
    def adam_id(self) -> int | None:
        """The App Store app ID."""
        ...

    @property
    def app_name(self) -> str | None:
        """The app display name."""
        ...


class CampaignListing(Protocol):
    """One campaign from the scope listing."""

    @property
    def id(self) -> int | None:
        """The campaign ID."""
        ...

    @property
    def name(self) -> str | None:
        """The campaign name."""
        ...

    @property
    def adam_id(self) -> int:
        """The promoted app's adam ID."""
        ...

    @property
    def daily_budget_amount(self) -> MoneyLike | None:
        """The daily budget, if set."""
        ...

    @property
    def budget_amount(self) -> MoneyLike | None:
        """The lifetime budget, if set."""
        ...


class FetchApps(Protocol):
    """The app-search surface the fetch pipeline uses."""

    def search(self, *, query: str, return_own_apps: bool) -> Iterable[AppListing]:
        """Search apps eligible for (or owned by) the organization."""
        ...


class FetchCampaigns(Protocol):
    """The campaign-listing surface the fetch pipeline uses."""

    def list(self) -> Iterable[CampaignListing]:
        """List the organization's campaigns."""
        ...


class FetchReports(Protocol):
    """The async report surface the fetch pipeline uses."""

    async def campaigns_async(
        self,
        start_date: date,
        end_date: date,
        /,
        *,
        campaign_ids: list[int] | None,
        timezone: str,
    ) -> ReportingResponse:
        """Campaign-level daily report."""
        ...

    async def ad_groups_async(
        self, campaign_id: int, start_date: date, end_date: date, /, *, timezone: str
    ) -> ReportingResponse:
        """Ad-group-level daily report for one campaign."""
        ...

    async def keywords_async(
        self, campaign_id: int, start_date: date, end_date: date, /, *, timezone: str
    ) -> ReportingResponse:
        """Keyword-level daily report for one campaign."""
        ...

    async def search_terms_async(
        self, campaign_id: int, start_date: date, end_date: date, /, *, timezone: str
    ) -> ReportingResponse:
        """Search-term-level daily report for one campaign."""
        ...

    async def ads_async(
        self, campaign_id: int, start_date: date, end_date: date, /, *, timezone: str
    ) -> ReportingResponse:
        """Ad-level daily report for one campaign."""
        ...


class FetchClient(Protocol):
    """The narrow client surface the fetch pipeline needs.

    Satisfied structurally by the v5 ``AppleSearchAdsClient`` and by
    ``cli.v1_adapter.V1FetchAdapter``.
    """

    @property
    def apps(self) -> FetchApps:
        """App search resource."""
        ...

    @property
    def campaigns(self) -> FetchCampaigns:
        """Campaigns resource."""
        ...

    @property
    def reports(self) -> FetchReports:
        """Reports resource."""
        ...

    async def aclose(self) -> None:
        """Close async HTTP resources."""
        ...


LEVELS: list[tuple[str, str]] = [
    ("campaigns", "Campaigns"),
    ("ad_groups", "Ad Groups"),
    ("keywords", "Keywords"),
    ("search_terms", "Search Terms"),
    ("ads", "Ads"),
]
LEVEL_LABELS = dict(LEVELS)
CONCURRENCY = 5

_SPEND_FIELDS = ("tap_install_cpi", "total_avg_cpi", "avg_cpt", "avg_cpm", "local_spend")
_META_SPEND_FIELDS = ("bid_amount", "suggested_bid_amount")


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


def flatten_daily(resp: ReportingResponse) -> pd.DataFrame:
    """Flatten a reporting response into one row per entity per day.

    Uses each row's ``granularity`` breakdown (falling back to ``total``
    when absent) so DAILY reports keep their per-day resolution —
    ``ReportingResponse.to_dataframe`` drops it.

    Args:
        resp: A parsed reporting response.

    Returns:
        A DataFrame with snake_case metadata columns plus per-day metric
        columns; spend fields flattened to their string amounts.
    """
    records: list[dict[str, object]] = []
    for row in resp.row:
        meta = row.metadata.model_dump(by_alias=False, exclude_none=True)
        for spend_field in _META_SPEND_FIELDS:
            value = meta.get(spend_field)
            if isinstance(value, dict):
                meta[spend_field] = value.get("amount")
        entries = row.granularity or ([row.total] if row.total is not None else [])
        for entry in entries:
            metric = entry.model_dump(by_alias=False, exclude_none=True)
            for spend_field in _SPEND_FIELDS:
                value = metric.get(spend_field)
                if isinstance(value, dict):
                    metric[spend_field] = value.get("amount")
            records.append({**meta, **metric})
    return pd.DataFrame(records)


def _app_names(client: FetchClient, adam_ids: list[int]) -> dict[int, str]:
    """Best-effort lookup of app names for the org's adam IDs.

    Falls back to ``App <adam_id>`` labels when the search endpoint
    yields nothing (it requires a query and may not match).

    Args:
        client: The API client.
        adam_ids: Adam IDs present in the campaign scope.

    Returns:
        Mapping of adam ID to display name.
    """
    names: dict[int, str] = {}
    try:
        for info in client.apps.search(query="", return_own_apps=True):
            if info.adam_id is not None and info.app_name:
                names[int(info.adam_id)] = info.app_name
    except Exception:  # purely cosmetic lookup, never fatal
        names = {}
    return {adam: names.get(adam, f"App {adam}") for adam in adam_ids}


def resolve_scope(
    client: FetchClient, app_ids: list[int] | None
) -> tuple[pd.DataFrame, str | None]:
    """List campaigns once and build the campaign → app scope map.

    Args:
        client: The API client.
        app_ids: Adam IDs to scope to, or None for the whole org.

    Returns:
        Tuple of (meta frame with ``campaign_id``, ``campaign_name``,
        ``adam_id``, ``app_name`` columns; org currency code or None).

    Raises:
        ScopeError: If no campaigns match the requested apps.
    """
    campaigns = list(client.campaigns.list())
    if app_ids:
        campaigns = [c for c in campaigns if c.adam_id in set(app_ids)]
    if not campaigns:
        detail = f" for app(s) {sorted(set(app_ids))}" if app_ids else ""
        raise ScopeError(f"No campaigns found{detail}")

    currency: str | None = None
    for campaign in campaigns:
        money = campaign.daily_budget_amount or campaign.budget_amount
        if money is not None:
            currency = money.currency
            break

    adam_ids = sorted({c.adam_id for c in campaigns})
    names = _app_names(client, adam_ids)
    meta = pd.DataFrame(
        [
            {
                "campaign_id": c.id,
                "campaign_name": c.name,
                "adam_id": c.adam_id,
                "app_name": names[c.adam_id],
            }
            for c in campaigns
        ]
    )
    return meta, currency


def _merge_names(df: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Join campaign/app names onto a level frame by campaign_id."""
    if df.empty or "campaign_id" not in df.columns:
        return df
    df = df.drop(columns=[c for c in ("campaign_name", "app_name", "adam_id") if c in df.columns])
    return df.merge(meta, on="campaign_id", how="left")


async def fetch_all(
    client: FetchClient,
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
        client: The API client.
        meta: Scope frame from :func:`resolve_scope`.
        start: Range start (inclusive).
        end: Range end (inclusive).
        timezone: Reporting timezone passed to the API.
        today: Current date (drives the search-term lookback clip).
        on_progress: Optional callback ``(level_key, completed, total)``.
            Fires once with ``(level, 0, 0)`` for any level with zero
            chunks to fetch (e.g. search terms when the whole requested
            range is older than the trailing 90-day lookback), so callers
            can treat that level as immediately complete rather than
            waiting for a tick that will never come.

    Returns:
        A :class:`FetchResult` with per-level daily frames (names merged
        on), the prior-period campaign frame, and accumulated warnings.

    Raises:
        LevelFetchError: If the current-period campaign window fails, or
            every chunk of any other level fails. Prior-period campaign
            window failures do not raise: the prior period only feeds
            Summary-sheet KPI deltas, so a failure there (e.g. an
            explicit range whose prior window predates the 730-day API
            lookback) degrades to a warning and an empty/partial
            ``prior_campaigns`` frame instead of aborting the run.
    """
    windows = chunk_windows(start, end)
    p_start, p_end = prior_window(start, end)
    prior_windows = chunk_windows(p_start, p_end)
    campaign_ids = [int(c) for c in meta["campaign_id"].tolist()]

    st_start = max(start, today - timedelta(days=SEARCH_TERM_LOOKBACK))
    # The whole requested range can be older than the lookback (legal: the
    # overall API lookback is 730 days). That's not "clipped to a smaller
    # window" — it's "no search-term data available at all" — so it needs
    # its own note and must not compute a reversed (st_start > end) range.
    st_out_of_range = st_start > end
    st_windows = [] if st_out_of_range else chunk_windows(st_start, end)
    st_clipped = st_start > start and not st_out_of_range

    reports = client.reports
    per_campaign: dict[str, Callable[[int, date, date], Awaitable[ReportingResponse]]] = {
        "ad_groups": lambda cid, s, e: reports.ad_groups_async(cid, s, e, timezone=timezone),
        "keywords": lambda cid, s, e: reports.keywords_async(cid, s, e, timezone=timezone),
        "search_terms": lambda cid, s, e: reports.search_terms_async(cid, s, e, timezone=timezone),
        "ads": lambda cid, s, e: reports.ads_async(cid, s, e, timezone=timezone),
    }
    level_windows = {key: st_windows if key == "search_terms" else windows for key in per_campaign}

    totals: dict[str, int] = {"campaigns": len(windows) + len(prior_windows)}
    totals |= {key: len(level_windows[key]) * len(campaign_ids) for key in per_campaign}
    done = dict.fromkeys(totals, 0)

    # A level with zero chunks (e.g. search terms entirely outside the
    # 90-day lookback) never has a chunk task to fire _tick from, so it
    # would otherwise never report progress at all.
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
                resp = await reports.campaigns_async(
                    win[0], win[1], campaign_ids=campaign_ids, timezone=timezone
                )
            except AppleSearchAdsError as exc:
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
            (prior_frames if prior else frames["campaigns"]).append(flatten_daily(resp))

    async def _chunk(level: str, cid: int, win: tuple[date, date]) -> None:
        label = LEVEL_LABELS[level]
        async with semaphore:
            try:
                resp = await per_campaign[level](cid, win[0], win[1])
            except AppleSearchAdsError as exc:
                failures[level] += 1
                message = f"{label}: campaign {cid} window {win[0]}-{win[1]} failed: {exc}"
                warnings.append(message)
                notes[level].append(message)
                return
            finally:
                _tick(level)
            frames[level].append(flatten_daily(resp))

    tasks: list[Awaitable[None]] = []
    tasks += [_campaign_window(win, prior=False) for win in windows]
    tasks += [_campaign_window(win, prior=True) for win in prior_windows]
    for level in per_campaign:
        tasks += [_chunk(level, cid, win) for cid in campaign_ids for win in level_windows[level]]
    # return_exceptions=True lets every in-flight request finish before we
    # re-raise, so an aborting run doesn't leave tasks using a closing client.
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
