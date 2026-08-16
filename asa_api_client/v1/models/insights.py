"""Models for the Apple Ads Platform API v1 insights endpoints.

The Insights API exposes two synchronous, paginated POST query
endpoints under ``/v1/insights/apps/...``: impression share (the
fraction of eligible impressions your app captures per search term and
country) and search term popularity (relative search-volume rankings
per App Store genre and country). Both take a bare JSON body of
``{fields?, filters, sorting?, timeRange, pagination?, options?}`` and
return the standard ``{result, pagination, error}`` envelope where
``result`` is a container object holding a ``rows`` array.

Also defined here: :class:`KeywordInsights`, the insights payload
attached to keyword *reporting* rows (not returned by the two insights
query endpoints).
"""

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class ImpressionShareGranularity(StrEnum):
    """Time granularity for impression share queries.

    ``DAILY`` allows a window of at most 30 days (inclusive) and
    populates ``day`` on each row. ``WEEKLY_SUN_SAT`` uses fixed
    Sunday-Saturday weeks, allows at most 4 weeks, requires the range
    to start on a Sunday, and populates ``week``.
    """

    DAILY = "DAILY"
    WEEKLY_SUN_SAT = "WEEKLY_SUN_SAT"


class SearchTermPopularityGranularity(StrEnum):
    """Time granularity for search term popularity queries.

    ``WEEKLY_SUN_SAT`` uses fixed Sunday-Saturday weeks (65-week
    retention) and populates ``week``. ``MONTHLY`` uses calendar months
    (15-month retention) and populates ``month`` as ``YYYY-MM``.
    """

    WEEKLY_SUN_SAT = "WEEKLY_SUN_SAT"
    MONTHLY = "MONTHLY"


class ImpressionShareReportType(StrEnum):
    """Which ad positions an impression share report aggregates.

    ``FIRST_SLOT`` (the default) counts only the first ad position;
    ``ALL_SLOTS`` aggregates across all ad positions.
    """

    FIRST_SLOT = "FIRST_SLOT"
    ALL_SLOTS = "ALL_SLOTS"


class InsightsFilter(V1Model):
    """One filter condition in an insights query request.

    Unlike some other v1 query endpoints, insights filter values are
    scalars (e.g. ``"123456789"``), not arrays.

    Attributes:
        field: The field to filter on (e.g. ``"promotedObjectId"``).
        operator: The comparison operator (e.g. ``"EQUALS"``).
        value: The scalar comparison value.
    """

    field: str
    operator: str
    value: Any | None = None


class InsightsSorting(V1Model):
    """One sort entry in an insights query request.

    Both insights endpoints allow at most 2 sort fields per request.

    Attributes:
        field: The field to sort by (e.g. ``"highImpressionShare"``).
        order: The sort direction, ``"ASC"`` or ``"DESC"``.
    """

    field: str
    order: str = "ASC"


class InsightsPagination(V1Model):
    """Request pagination for insights queries.

    Attributes:
        offset: Zero-based starting position.
        page_size: Items per page. Impression share defaults to 100
            server-side; both endpoints cap ``pageSize`` at 5000.
    """

    offset: int | None = None
    page_size: int | None = Field(default=None, alias="pageSize")


class ImpressionShareTimeRange(V1Model):
    """Date window and granularity for an impression share query.

    Attributes:
        start: First date of the window (``YYYY-MM-DD``). Must be a
            Sunday when granularity is ``WEEKLY_SUN_SAT``.
        end: Last date of the window (``YYYY-MM-DD``).
        time_zone: Fixed to ``"UTC"``; not user-configurable.
        granularity: ``DAILY`` (max 30 days) or ``WEEKLY_SUN_SAT``
            (max 4 weeks).
    """

    start: date
    end: date
    time_zone: str | None = Field(default=None, alias="timeZone")
    granularity: ImpressionShareGranularity


class SearchTermPopularityTimeRange(V1Model):
    """Date window and granularity for a search term popularity query.

    Attributes:
        start: First date of the window (``YYYY-MM-DD``).
        end: Last date of the window (``YYYY-MM-DD``).
        time_zone: Fixed to ``"UTC"``; not user-configurable.
        granularity: ``WEEKLY_SUN_SAT`` or ``MONTHLY``.
    """

    start: date
    end: date
    time_zone: str | None = Field(default=None, alias="timeZone")
    granularity: SearchTermPopularityGranularity


class ImpressionShareOptions(V1Model):
    """Report-type options for an impression share query.

    Attributes:
        impression_share_report_type: Which ad positions to aggregate;
            defaults to ``FIRST_SLOT`` server-side.
    """

    impression_share_report_type: ImpressionShareReportType | None = Field(
        default=None, alias="impressionShareReportType"
    )


class ImpressionShareQueryRequest(V1Model):
    """Request body for ``POST /v1/insights/apps/impression-share/query``.

    A filter on ``promotedObjectId`` is required — the API rejects the
    request with 400 when it is omitted.

    Attributes:
        fields: Optional field-selection list (the documented example
            body includes ``"fields": []``).
        filters: Filter conditions; must include a ``promotedObjectId``
            filter.
        sorting: Sort criteria; maximum 2 sort fields.
        time_range: Date window and granularity.
        pagination: Offset/pageSize controls (default ``pageSize`` 100,
            max 5000).
        options: Report-type option (``FIRST_SLOT``/``ALL_SLOTS``).
    """

    fields: list[str] | None = None
    filters: list[InsightsFilter]
    sorting: list[InsightsSorting] | None = None
    time_range: ImpressionShareTimeRange = Field(alias="timeRange")
    pagination: InsightsPagination | None = None
    options: ImpressionShareOptions | None = None


class SearchTermPopularityQueryRequest(V1Model):
    """Request body for ``POST /v1/insights/apps/search-term-popularity/query``.

    Attributes:
        fields: Optional metric columns to include (``rankInGenre``,
            ``searchPopularityInGenre``, ``searchPopularity1to100``,
            ``searchPopularity1to5``); metric fields are returned only
            when requested here.
        filters: Filter conditions (e.g. ``countryOrRegion``,
            ``genre``). Genre values are free-text App Store genre
            names.
        sorting: Sort criteria; maximum 2 sort fields. Server default
            is ``genre ASC, rankInGenre ASC``.
        time_range: Date window and granularity.
        pagination: Offset/pageSize controls (``pageSize`` capped at
            5000).
    """

    fields: list[str] | None = None
    filters: list[InsightsFilter] | None = None
    sorting: list[InsightsSorting] | None = None
    time_range: SearchTermPopularityTimeRange = Field(alias="timeRange")
    pagination: InsightsPagination | None = None


class ImpressionShareRow(V1Model):
    """One impression share result row (date x search term x country).

    ``lowImpressionShare``/``highImpressionShare`` use a tiered
    encoding: 0% share is ``0``/``0``; 1-90% puts the same value in
    both fields; 91-100% is ``0.91``/``1`` (``1`` means >90% share).

    Attributes:
        day: The day (``YYYY-MM-DD``), when granularity is ``DAILY``.
        week: The week start Sunday, when granularity is
            ``WEEKLY_SUN_SAT``.
        app_name: Display name of the promoted app.
        promoted_object_id: Adam ID of the promoted app, serialized by
            the API as a string.
        country_or_region: ISO 3166-1 alpha-2 country/region code.
        search_term: The search term; suppressed for terms with fewer
            than 10 impressions in the aggregation period.
        low_impression_share: Lower bound of impression share (0-1).
        high_impression_share: Upper bound of impression share (0-1).
        rank: Stack-ranked position by impression share for the
            term+country; ``1`` is the highest share.
        search_popularity_1_to_5: Relative search volume on a 1-5
            scale; ``5`` is most popular.
    """

    day: date | None = None
    week: date | None = None
    app_name: str | None = Field(default=None, alias="appName")
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    search_term: str | None = Field(default=None, alias="searchTerm")
    low_impression_share: float | None = Field(default=None, alias="lowImpressionShare")
    high_impression_share: float | None = Field(default=None, alias="highImpressionShare")
    rank: int | None = None
    search_popularity_1_to_5: int | None = Field(default=None, alias="searchPopularity1to5")


class SearchTermPopularityRow(V1Model):
    """One search term popularity result row (term x genre x country).

    Only terms with at least 500 searches are included, with up to 500
    ranked terms per country/genre combination. The metric fields are
    present only when requested via the request's ``fields`` list.

    Attributes:
        week: Start date of the completed weekly range, when
            granularity is ``WEEKLY_SUN_SAT``.
        month: Calendar month (``YYYY-MM``), when granularity is
            ``MONTHLY``.
        country_or_region: ISO 3166-1 alpha-2 country/region code.
        genre: App Store genre classification.
        search_term: The search term.
        rank_in_genre: Rank by search volume within country + genre;
            ``1`` is highest.
        search_popularity_in_genre: Popularity within country + genre,
            1-100; ``100`` is most popular in the genre.
        search_popularity_1_to_100: Popularity across all genres within
            the country, 1-100; ``100`` is most popular overall.
        search_popularity_1_to_5: Popularity across all genres on a
            1-5 scale; matches Campaign Management's Search Popularity.
    """

    week: date | None = None
    month: str | None = None
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    genre: str | None = None
    search_term: str | None = Field(default=None, alias="searchTerm")
    rank_in_genre: int | None = Field(default=None, alias="rankInGenre")
    search_popularity_in_genre: int | None = Field(default=None, alias="searchPopularityInGenre")
    search_popularity_1_to_100: int | None = Field(default=None, alias="searchPopularity1to100")
    search_popularity_1_to_5: int | None = Field(default=None, alias="searchPopularity1to5")


class ReportingKeywordBidRecommendation(V1Model):
    """Suggested bid information attached to a keyword reporting row.

    Attributes:
        suggested_bid_amount: The suggested bid amount as a bare number
            (the documented example is ``2.35``, not a Money object).
    """

    suggested_bid_amount: float | None = Field(default=None, alias="suggestedBidAmount")


class KeywordInsights(V1Model):
    """Insights attached to keyword reporting rows.

    Not returned by the two insights query endpoints; this object
    appears inside keyword *reporting* responses.

    Attributes:
        bid_recommendation: Suggested bid information for the keyword.
    """

    bid_recommendation: ReportingKeywordBidRecommendation | None = Field(
        default=None, alias="bidRecommendation"
    )
