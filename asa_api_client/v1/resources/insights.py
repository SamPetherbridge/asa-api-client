"""Insights resource for the Apple Ads Platform API v1.

Covers the two synchronous insights query endpoints under
``/v1/insights/apps``: impression share and search term popularity.
Both are POST query endpoints whose ``result`` is a container object
holding a ``rows`` array (not a bare list), so this resource parses
pages itself instead of using the query mixin.
"""

from typing import Any, TypeVar

from asa_api_client.v1.models.base import V1Model, V1Page, V1Pagination
from asa_api_client.v1.models.insights import (
    ImpressionShareQueryRequest,
    ImpressionShareRow,
    SearchTermPopularityQueryRequest,
    SearchTermPopularityRow,
)
from asa_api_client.v1.resources.base import V1Resource

M = TypeVar("M", bound=V1Model)

_IMPRESSION_SHARE_PATH = "impression-share/query"
_SEARCH_TERM_POPULARITY_PATH = "search-term-popularity/query"


class InsightResource(
    V1Resource[SearchTermPopularityRow, SearchTermPopularityRow, SearchTermPopularityRow]
):
    """Impression share and search term popularity insights.

    Both endpoints take a bare (unwrapped) JSON request body and return
    ``{result: {rows: [...]}, pagination, error}``; an ``error`` block
    raises even on HTTP 2xx.
    """

    base_path = "insights/apps"
    model_class = SearchTermPopularityRow
    requires_account_context = True

    def _rows_page(self, model: type[M], data: dict[str, Any]) -> V1Page[M]:
        """Parse a ``{result: {rows: [...]}}`` envelope into a typed page.

        Args:
            model: The row model to validate each entry with.
            data: The API response body.

        Returns:
            A V1Page of parsed rows with pagination metadata.
        """
        container = data.get("result") or {}
        rows = [model.model_validate(row) for row in container.get("rows") or []]
        pagination_data = data.get("pagination")
        pagination = V1Pagination.model_validate(pagination_data) if pagination_data else None
        return V1Page[M](result=rows, pagination=pagination)

    def query_impression_share(
        self, request: ImpressionShareQueryRequest
    ) -> V1Page[ImpressionShareRow]:
        """Query impression share insights.

        Calls ``POST /v1/insights/apps/impression-share/query``. The
        request must include a ``promotedObjectId`` filter or the API
        rejects it with 400. ``searchTerm`` is suppressed for terms
        with fewer than 10 impressions in the aggregation period.

        Args:
            request: The impression share query (filters, sorting,
                time range, pagination, options).

        Returns:
            A page of impression share rows, one per date x search
            term x country combination.
        """
        data = self._request("POST", _IMPRESSION_SHARE_PATH, json=self._dump(request))
        return self._rows_page(ImpressionShareRow, data)

    async def query_impression_share_async(
        self, request: ImpressionShareQueryRequest
    ) -> V1Page[ImpressionShareRow]:
        """Query impression share insights asynchronously.

        Args:
            request: The impression share query (filters, sorting,
                time range, pagination, options).

        Returns:
            A page of impression share rows.
        """
        data = await self._request_async("POST", _IMPRESSION_SHARE_PATH, json=self._dump(request))
        return self._rows_page(ImpressionShareRow, data)

    def query_search_term_popularity(
        self, request: SearchTermPopularityQueryRequest
    ) -> V1Page[SearchTermPopularityRow]:
        """Query search term popularity insights.

        Calls ``POST /v1/insights/apps/search-term-popularity/query``
        for relative search-volume rankings per App Store genre and
        country/region.

        Note:
            Although the docs describe ``filters`` support, the live API
            has been observed (2026-08-16) to return zero rows whenever
            any filter is present — query unfiltered and filter
            client-side on ``country_or_region``/``genre``. Data for a
            week is published with a lag: the most recently completed
            Sun-Sat week may be empty until later in the following week.

        Metric columns (``rankInGenre``,
        ``searchPopularityInGenre``, ``searchPopularity1to100``,
        ``searchPopularity1to5``) are returned only when named in the
        request's ``fields`` list.

        Args:
            request: The popularity query (fields, filters, sorting,
                time range, pagination).

        Returns:
            A page of popularity rows, one per term x genre x country
            combination.
        """
        data = self._request("POST", _SEARCH_TERM_POPULARITY_PATH, json=self._dump(request))
        return self._rows_page(SearchTermPopularityRow, data)

    async def query_search_term_popularity_async(
        self, request: SearchTermPopularityQueryRequest
    ) -> V1Page[SearchTermPopularityRow]:
        """Query search term popularity insights asynchronously.

        Args:
            request: The popularity query (fields, filters, sorting,
                time range, pagination).

        Returns:
            A page of popularity rows.
        """
        data = await self._request_async(
            "POST", _SEARCH_TERM_POPULARITY_PATH, json=self._dump(request)
        )
        return self._rows_page(SearchTermPopularityRow, data)
