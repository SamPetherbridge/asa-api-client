"""Search Popularity enrichment for the analyze command.

Matches the organization's keywords and search terms against Apple's
search-term-popularity insights (Apple Ads Platform API v1) to show how
much App Store search volume each term actually carries.

Live-API behavior this module works around (documented in
:mod:`asa_api_client.v1.resources.insights`):

- Any ``filters`` in the request make the API return zero rows, so the
  query is always unfiltered and matching happens client-side.
- Weekly windows must start on a Sunday, so the query targets the most
  recent complete Sun-Sat week.
- Data is published with roughly a week's lag, so an empty latest week
  falls back exactly one week and retries once.

Failures never propagate: any API or configuration problem degrades to
an empty frame plus an explanatory note.
"""

import os
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from asa_api_client.cli import fetch
from asa_api_client.exceptions import AppleSearchAdsError
from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.models.insights import (
    SearchTermPopularityGranularity,
    SearchTermPopularityQueryRequest,
    SearchTermPopularityRow,
    SearchTermPopularityTimeRange,
)

POPULARITY_COLUMNS: list[str] = [
    "search_term",
    "source",
    "country_or_region",
    "genre",
    "rank_in_genre",
    "search_popularity_1_to_100",
    "search_popularity_1_to_5",
]

_FIELDS = (
    "rankInGenre",
    "searchPopularityInGenre",
    "searchPopularity1to100",
    "searchPopularity1to5",
)

_NO_MATCH_NOTE = (
    "No account keywords or search terms meet Apple's ≥500 searches/week popularity floor."
)


class _SkipPopularity(Exception):
    """The sheet cannot be built; the message is the explanatory note."""


def latest_complete_week(today: date) -> tuple[date, date]:
    """Find the most recent complete Sun-Sat week ending before today.

    Args:
        today: The current date.

    Returns:
        The inclusive ``(sunday, saturday)`` pair of the latest Sun-Sat
        week whose Saturday is at least one day in the past.
    """
    reference = today - timedelta(days=1)
    saturday = reference - timedelta(days=(reference.weekday() - 5) % 7)
    return saturday - timedelta(days=6), saturday


def _level_terms(result: fetch.FetchResult, level: str, column: str) -> set[str]:
    """Collect lowercased distinct term texts from one level frame.

    Args:
        result: The fetched analyze data.
        level: The level key (e.g. ``"keywords"``).
        column: The term column on that level's daily frame.

    Returns:
        The distinct non-empty terms, lowercased. Empty when the level,
        its frame, or the column is missing.
    """
    data = result.levels.get(level)
    if data is None or data.daily.empty or column not in data.daily.columns:
        return set()
    return {str(value).lower() for value in data.daily[column].dropna() if str(value)}


def _resolve_account(client: AppleAdsClient) -> str | None:
    """Ensure the client has an ad account, auto-selecting from ACLs.

    Prefers the ACL ad account whose ID equals ``ASA_ORG_ID`` (orgs and
    their primary ad accounts commonly share an ID); otherwise a single
    accessible account is used.

    Args:
        client: The v1 API client.

    Returns:
        A note describing the auto-selection, or None when the client
        already had an account configured.

    Raises:
        _SkipPopularity: When no account can be selected unambiguously.
    """
    if client.ad_account_id is not None:
        return None
    accounts = [
        acl.ad_account
        for acl in client.acls.list()
        if acl.ad_account is not None and acl.ad_account.id is not None
    ]
    org_id = os.environ.get("ASA_ORG_ID")
    selected = next((a for a in accounts if str(a.id) == org_id), None) if org_id else None
    if selected is None and len(accounts) == 1:
        selected = accounts[0]
    if selected is None:
        raise _SkipPopularity(
            "Search Popularity skipped: ASA_AD_ACCOUNT_ID is not set and the "
            f"ad account could not be auto-selected from {len(accounts)} ACL entries."
        )
    client.ad_account_id = str(selected.id)
    return f"Ad account {selected.id} ({selected.name}) auto-selected for popularity data."


def _week_rows(
    client: AppleAdsClient, sunday: date, saturday: date
) -> list[SearchTermPopularityRow]:
    """Query one Sun-Sat week of popularity data, unfiltered.

    Args:
        client: The v1 API client.
        sunday: The week's start (must be a Sunday).
        saturday: The week's end.

    Returns:
        Every popularity row for the week across all storefronts.
    """
    request = SearchTermPopularityQueryRequest(
        fields=list(_FIELDS),
        time_range=SearchTermPopularityTimeRange(
            start=sunday,
            end=saturday,
            granularity=SearchTermPopularityGranularity.WEEKLY_SUN_SAT,
        ),
    )
    return list(client.insights.query_search_term_popularity(request))


def _match(
    rows: list[SearchTermPopularityRow], keyword_terms: set[str], search_terms: set[str]
) -> pd.DataFrame:
    """Keep the popularity rows whose term the org bids on or matched.

    Args:
        rows: All popularity rows for the queried week.
        keyword_terms: Lowercased keyword texts from the keywords level.
        search_terms: Lowercased texts from the search-terms level.

    Returns:
        The matched rows with :data:`POPULARITY_COLUMNS`, sorted by
        overall popularity (desc) then in-genre rank (asc).
    """
    records: list[dict[str, object]] = []
    for row in rows:
        term = (row.search_term or "").lower()
        in_keywords = term in keyword_terms
        in_search_terms = term in search_terms
        if not term or not (in_keywords or in_search_terms):
            continue
        if in_keywords and in_search_terms:
            source = "Both"
        else:
            source = "Keywords" if in_keywords else "Search Terms"
        records.append(
            {
                "search_term": row.search_term,
                "source": source,
                "country_or_region": row.country_or_region,
                "genre": row.genre,
                "rank_in_genre": row.rank_in_genre,
                "search_popularity_1_to_100": row.search_popularity_1_to_100,
                "search_popularity_1_to_5": row.search_popularity_1_to_5,
            }
        )
    frame = pd.DataFrame(records, columns=POPULARITY_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(
        by=["search_popularity_1_to_100", "rank_in_genre"],
        ascending=[False, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)


def build_popularity(
    result: fetch.FetchResult,
    *,
    client_factory: Callable[[], AppleAdsClient] | None = None,
    today: date | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Build the Search Popularity frame for an analyze run.

    Collects the org's keyword and search-term texts from ``result``,
    queries one week of search-term popularity via the v1 API (falling
    back one week when the latest week has no data yet), and keeps the
    rows matching the org's terms across all storefronts.

    Args:
        result: The fetched analyze data (term sources).
        client_factory: Zero-argument v1 client factory; defaults to
            :meth:`AppleAdsClient.from_env`. The client is closed before
            returning.
        today: The current date; defaults to today (UTC).

    Returns:
        Tuple of (popularity frame with :data:`POPULARITY_COLUMNS`,
        notes for the sheet). On any API or configuration failure the
        frame is empty and the notes explain why — this function never
        raises for those errors.
    """
    keyword_terms = _level_terms(result, "keywords", "keyword")
    search_terms = _level_terms(result, "search_terms", "search_term_text")
    if not (keyword_terms or search_terms):
        return pd.DataFrame(columns=POPULARITY_COLUMNS), [
            "No keywords or search terms in scope; popularity lookup skipped."
        ]

    factory = client_factory or AppleAdsClient.from_env
    try:
        with factory() as client:
            account_note = _resolve_account(client)
            sunday, saturday = latest_complete_week(today or datetime.now(tz=UTC).date())
            rows = _week_rows(client, sunday, saturday)
            if not rows:
                sunday -= timedelta(days=7)
                saturday -= timedelta(days=7)
                rows = _week_rows(client, sunday, saturday)
    except _SkipPopularity as exc:
        return pd.DataFrame(columns=POPULARITY_COLUMNS), [str(exc)]
    except AppleSearchAdsError as exc:
        return pd.DataFrame(columns=POPULARITY_COLUMNS), [f"Search Popularity unavailable: {exc}"]

    notes = [f"Popularity week: {sunday} – {saturday}"]  # noqa: RUF001
    if account_note is not None:
        notes.append(account_note)
    frame = _match(rows, keyword_terms, search_terms)
    if frame.empty:
        notes.append(_NO_MATCH_NOTE)
    return frame, notes
