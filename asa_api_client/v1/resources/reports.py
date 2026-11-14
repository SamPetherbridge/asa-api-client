"""Report resources for the Apple Ads Platform API v1.

Two resources cover the ten report endpoints:

- :class:`ReportResource` — App Store reports under ``reports/apps``.
- :class:`BrandReportResource` — Apple Maps (brands) reports under
  ``reports/business-brands``.

All report endpoints are ``POST <base>/<entity>/query`` calls that take
a reporting request body and return a ``{result, pagination, error}``
envelope whose ``result`` holds ``rows`` and an optional ``summary``.
An ``error`` block in a 2xx body raises
:class:`~asa_api_client.exceptions.PartialFailureError` in the
transport before parsing.
"""

from collections.abc import AsyncIterator, Iterator
from typing import Any, TypeVar

from asa_api_client.v1.models.base import V1Model, V1Pagination
from asa_api_client.v1.models.reports import (
    AppsAdGroupReportResponse,
    AppsAdGroupReportRow,
    AppsAdReportResponse,
    AppsAdReportRow,
    AppsCampaignReportResponse,
    AppsCampaignReportRow,
    AppsKeywordReportResponse,
    AppsKeywordReportRow,
    AppsReportingRequest,
    AppsSearchTermReportResponse,
    AppsSearchTermReportRow,
    BrandsAdGroupReportResponse,
    BrandsAdGroupReportRow,
    BrandsAdReportResponse,
    BrandsAdReportRow,
    BrandsCampaignReportResponse,
    BrandsCampaignReportRow,
    BrandsKeywordReportResponse,
    BrandsKeywordReportRow,
    BrandsReportingRequest,
    BrandsSearchTermReportResponse,
    BrandsSearchTermReportRow,
)
from asa_api_client.v1.resources.base import V1Resource

ResponseT = TypeVar("ResponseT", bound=V1Model)
RowT = TypeVar("RowT", bound=V1Model)


class _BaseReportResource(V1Resource[V1Model, V1Model, V1Model]):
    """Shared transport helpers for the report resources."""

    model_class = V1Model

    def _run_report(
        self,
        path: str,
        request: V1Model | None,
        response_class: type[ResponseT],
    ) -> ResponseT:
        """POST a reporting request and parse the typed response.

        Args:
            path: Entity query path relative to ``base_path``.
            request: The reporting request, or None for an empty body.
            response_class: The response envelope model to parse into.

        Returns:
            The parsed report response.
        """
        payload = self._dump(request) if request is not None else {}
        data = self._request("POST", path, json=payload)
        return response_class.model_validate(data)

    async def _run_report_async(
        self,
        path: str,
        request: V1Model | None,
        response_class: type[ResponseT],
    ) -> ResponseT:
        """POST a reporting request asynchronously and parse the response.

        Args:
            path: Entity query path relative to ``base_path``.
            request: The reporting request, or None for an empty body.
            response_class: The response envelope model to parse into.

        Returns:
            The parsed report response.
        """
        payload = self._dump(request) if request is not None else {}
        data = await self._request_async("POST", path, json=payload)
        return response_class.model_validate(data)

    @staticmethod
    def _has_more_rows(
        row_count: int,
        offset: int,
        page_size: int,
        pagination: V1Pagination | None,
    ) -> bool:
        """Determine whether additional report rows remain on the server."""
        if row_count == 0:
            return False
        if pagination is not None and pagination.total_count is not None:
            return offset + row_count < pagination.total_count
        return row_count >= page_size

    def _iter_report_rows(
        self,
        path: str,
        request: V1Model | None,
        response_class: type[ResponseT],
        _row_class: type[RowT],
        page_size: int,
    ) -> Iterator[RowT]:
        """Iterate across pages of a reporting endpoint synchronously."""
        base_payload = self._dump(request) if request is not None else {}
        offset = 0
        while True:
            payload = {**base_payload, "pagination": {"offset": offset, "pageSize": page_size}}
            data = self._request("POST", path, json=payload)
            response: Any = response_class.model_validate(data)
            rows: list[RowT] = (response.result.rows or []) if response.result is not None else []
            yield from rows
            if not self._has_more_rows(len(rows), offset, page_size, response.pagination):
                break
            offset += len(rows)

    async def _iter_report_rows_async(
        self,
        path: str,
        request: V1Model | None,
        response_class: type[ResponseT],
        _row_class: type[RowT],
        page_size: int,
    ) -> AsyncIterator[RowT]:
        """Iterate across pages of a reporting endpoint asynchronously."""
        base_payload = self._dump(request) if request is not None else {}
        offset = 0
        while True:
            payload = {**base_payload, "pagination": {"offset": offset, "pageSize": page_size}}
            data = await self._request_async("POST", path, json=payload)
            response: Any = response_class.model_validate(data)
            rows: list[RowT] = (response.result.rows or []) if response.result is not None else []
            for row in rows:
                yield row
            if not self._has_more_rows(len(rows), offset, page_size, response.pagination):
                break
            offset += len(rows)


class ReportResource(_BaseReportResource):
    """App Store (APPS) performance reports.

    Exposes one method per report level: campaigns, ad groups, ads,
    keywords, and search terms. Each POSTs an
    :class:`~asa_api_client.v1.models.reports.AppsReportingRequest`
    (or an empty body) to the level's ``/query`` endpoint.

    Example:
        Run a daily campaign report::

            from asa_api_client.v1.models.reports import (
                AppsReportingRequest,
                ReportGranularity,
                ReportTimeRange,
            )

            response = client.reports.campaigns(
                AppsReportingRequest(
                    time_range=ReportTimeRange(
                        start=date(2026, 8, 1),
                        end=date(2026, 8, 7),
                        granularity=ReportGranularity.DAILY,
                    )
                )
            )
            for row in response.result.rows:
                print(row.metadata.name, row.total_metrics.taps)
    """

    base_path = "reports/apps"

    def campaigns(self, request: AppsReportingRequest | None = None) -> AppsCampaignReportResponse:
        """Get performance metrics for campaigns.

        Args:
            request: Report parameters (time range, filters, groupBy,
                fields, options). None requests the default report.

        Returns:
            The campaign report response with rows and summary.
        """
        return self._run_report("campaigns/query", request, AppsCampaignReportResponse)

    async def campaigns_async(
        self, request: AppsReportingRequest | None = None
    ) -> AppsCampaignReportResponse:
        """Get performance metrics for campaigns asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The campaign report response with rows and summary.
        """
        return await self._run_report_async("campaigns/query", request, AppsCampaignReportResponse)

    def ad_groups(self, request: AppsReportingRequest | None = None) -> AppsAdGroupReportResponse:
        """Get performance metrics for ad groups.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The ad group report response with rows and summary.
        """
        return self._run_report("adgroups/query", request, AppsAdGroupReportResponse)

    async def ad_groups_async(
        self, request: AppsReportingRequest | None = None
    ) -> AppsAdGroupReportResponse:
        """Get performance metrics for ad groups asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The ad group report response with rows and summary.
        """
        return await self._run_report_async("adgroups/query", request, AppsAdGroupReportResponse)

    def ads(self, request: AppsReportingRequest | None = None) -> AppsAdReportResponse:
        """Get performance metrics for ads.

        ``HOURLY`` granularity is not available at the ad level.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The ad report response with rows and summary.
        """
        return self._run_report("ads/query", request, AppsAdReportResponse)

    async def ads_async(self, request: AppsReportingRequest | None = None) -> AppsAdReportResponse:
        """Get performance metrics for ads asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The ad report response with rows and summary.
        """
        return await self._run_report_async("ads/query", request, AppsAdReportResponse)

    def keywords(self, request: AppsReportingRequest | None = None) -> AppsKeywordReportResponse:
        """Get performance metrics for keywords.

        Always filter by ``adGroupId`` or ``campaignId`` to avoid
        retrieving every keyword in the account.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The keyword report response with rows, insights, and summary.
        """
        return self._run_report("keywords/query", request, AppsKeywordReportResponse)

    async def keywords_async(
        self, request: AppsReportingRequest | None = None
    ) -> AppsKeywordReportResponse:
        """Get performance metrics for keywords asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The keyword report response with rows, insights, and summary.
        """
        return await self._run_report_async("keywords/query", request, AppsKeywordReportResponse)

    def search_terms(
        self, request: AppsReportingRequest | None = None
    ) -> AppsSearchTermReportResponse:
        """Get performance metrics for search terms.

        Search term reports require the ``ORTZ`` timezone, don't support
        ``HOURLY`` granularity, and suppress low-volume terms.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The search term report response with rows and summary.
        """
        return self._run_report("searchterms/query", request, AppsSearchTermReportResponse)

    async def search_terms_async(
        self, request: AppsReportingRequest | None = None
    ) -> AppsSearchTermReportResponse:
        """Get performance metrics for search terms asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The search term report response with rows and summary.
        """
        return await self._run_report_async(
            "searchterms/query", request, AppsSearchTermReportResponse
        )

    def iter_campaigns(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[AppsCampaignReportRow]:
        """Iterate over all campaign report rows with automatic pagination.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsCampaignReportRow` across all pages.
        """
        return self._iter_report_rows(
            "campaigns/query",
            request,
            AppsCampaignReportResponse,
            AppsCampaignReportRow,
            page_size,
        )

    def iter_campaigns_async(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[AppsCampaignReportRow]:
        """Iterate over all campaign report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsCampaignReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "campaigns/query",
            request,
            AppsCampaignReportResponse,
            AppsCampaignReportRow,
            page_size,
        )

    def iter_ad_groups(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[AppsAdGroupReportRow]:
        """Iterate over all ad group report rows with automatic pagination.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsAdGroupReportRow` across all pages.
        """
        return self._iter_report_rows(
            "adgroups/query",
            request,
            AppsAdGroupReportResponse,
            AppsAdGroupReportRow,
            page_size,
        )

    def iter_ad_groups_async(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[AppsAdGroupReportRow]:
        """Iterate over all ad group report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsAdGroupReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "adgroups/query",
            request,
            AppsAdGroupReportResponse,
            AppsAdGroupReportRow,
            page_size,
        )

    def iter_ads(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[AppsAdReportRow]:
        """Iterate over all ad report rows with automatic pagination.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsAdReportRow` across all pages.
        """
        return self._iter_report_rows(
            "ads/query", request, AppsAdReportResponse, AppsAdReportRow, page_size
        )

    def iter_ads_async(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[AppsAdReportRow]:
        """Iterate over all ad report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsAdReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "ads/query", request, AppsAdReportResponse, AppsAdReportRow, page_size
        )

    def iter_keywords(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[AppsKeywordReportRow]:
        """Iterate over all keyword report rows with automatic pagination.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsKeywordReportRow` across all pages.
        """
        return self._iter_report_rows(
            "keywords/query",
            request,
            AppsKeywordReportResponse,
            AppsKeywordReportRow,
            page_size,
        )

    def iter_keywords_async(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[AppsKeywordReportRow]:
        """Iterate over all keyword report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsKeywordReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "keywords/query",
            request,
            AppsKeywordReportResponse,
            AppsKeywordReportRow,
            page_size,
        )

    def iter_search_terms(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[AppsSearchTermReportRow]:
        """Iterate over all search term report rows with automatic pagination.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsSearchTermReportRow` across all pages.
        """
        return self._iter_report_rows(
            "searchterms/query",
            request,
            AppsSearchTermReportResponse,
            AppsSearchTermReportRow,
            page_size,
        )

    def iter_search_terms_async(
        self,
        request: AppsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[AppsSearchTermReportRow]:
        """Iterate over all search term report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`AppsSearchTermReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "searchterms/query",
            request,
            AppsSearchTermReportResponse,
            AppsSearchTermReportRow,
            page_size,
        )


class BrandReportResource(_BaseReportResource):
    """Apple Maps (BRANDS) performance reports.

    Mirrors :class:`ReportResource` for campaigns promoting business
    brands on Apple Maps, using
    :class:`~asa_api_client.v1.models.reports.BrandsReportingRequest`
    bodies and brands-specific metrics (directions, calls, shares, and
    other Maps action types). ``EMPTY_METRICS`` is not supported for
    any brands entity.
    """

    base_path = "reports/business-brands"

    def campaigns(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsCampaignReportResponse:
        """Get performance metrics for Apple Maps campaigns.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands campaign report response with rows and summary.
        """
        return self._run_report("campaigns/query", request, BrandsCampaignReportResponse)

    async def campaigns_async(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsCampaignReportResponse:
        """Get performance metrics for Apple Maps campaigns asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands campaign report response with rows and summary.
        """
        return await self._run_report_async(
            "campaigns/query", request, BrandsCampaignReportResponse
        )

    def ad_groups(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsAdGroupReportResponse:
        """Get performance metrics for Apple Maps ad groups.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands ad group report response with rows and summary.
        """
        return self._run_report("adgroups/query", request, BrandsAdGroupReportResponse)

    async def ad_groups_async(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsAdGroupReportResponse:
        """Get performance metrics for Apple Maps ad groups asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands ad group report response with rows and summary.
        """
        return await self._run_report_async("adgroups/query", request, BrandsAdGroupReportResponse)

    def ads(self, request: BrandsReportingRequest | None = None) -> BrandsAdReportResponse:
        """Get performance metrics for Apple Maps ads.

        ``HOURLY`` granularity is not available at the ad level.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands ad report response with rows and summary.
        """
        return self._run_report("ads/query", request, BrandsAdReportResponse)

    async def ads_async(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsAdReportResponse:
        """Get performance metrics for Apple Maps ads asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands ad report response with rows and summary.
        """
        return await self._run_report_async("ads/query", request, BrandsAdReportResponse)

    def keywords(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsKeywordReportResponse:
        """Get performance metrics for Apple Maps keywords.

        Always filter by ``adGroupId`` or ``campaignId`` to keep
        responses manageable.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands keyword report response with rows and summary.
        """
        return self._run_report("keywords/query", request, BrandsKeywordReportResponse)

    async def keywords_async(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsKeywordReportResponse:
        """Get performance metrics for Apple Maps keywords asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands keyword report response with rows and summary.
        """
        return await self._run_report_async("keywords/query", request, BrandsKeywordReportResponse)

    def search_terms(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsSearchTermReportResponse:
        """Get performance metrics for Apple Maps search terms.

        Search term reports require the ``ORTZ`` timezone, support only
        the ``deviceClass`` groupBy dimension, don't support ``HOURLY``
        granularity, and suppress low-volume terms.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands search term report response with rows and summary.
        """
        return self._run_report("searchterms/query", request, BrandsSearchTermReportResponse)

    async def search_terms_async(
        self, request: BrandsReportingRequest | None = None
    ) -> BrandsSearchTermReportResponse:
        """Get performance metrics for Apple Maps search terms asynchronously.

        Args:
            request: Report parameters; None requests the default report.

        Returns:
            The brands search term report response with rows and summary.
        """
        return await self._run_report_async(
            "searchterms/query", request, BrandsSearchTermReportResponse
        )

    def iter_campaigns(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[BrandsCampaignReportRow]:
        """Iterate over all Apple Maps campaign report rows across pages.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsCampaignReportRow` across all pages.
        """
        return self._iter_report_rows(
            "campaigns/query",
            request,
            BrandsCampaignReportResponse,
            BrandsCampaignReportRow,
            page_size,
        )

    def iter_campaigns_async(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[BrandsCampaignReportRow]:
        """Iterate over all Apple Maps campaign report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsCampaignReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "campaigns/query",
            request,
            BrandsCampaignReportResponse,
            BrandsCampaignReportRow,
            page_size,
        )

    def iter_ad_groups(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[BrandsAdGroupReportRow]:
        """Iterate over all Apple Maps ad group report rows across pages.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsAdGroupReportRow` across all pages.
        """
        return self._iter_report_rows(
            "adgroups/query",
            request,
            BrandsAdGroupReportResponse,
            BrandsAdGroupReportRow,
            page_size,
        )

    def iter_ad_groups_async(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[BrandsAdGroupReportRow]:
        """Iterate over all Apple Maps ad group report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsAdGroupReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "adgroups/query",
            request,
            BrandsAdGroupReportResponse,
            BrandsAdGroupReportRow,
            page_size,
        )

    def iter_ads(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[BrandsAdReportRow]:
        """Iterate over all Apple Maps ad report rows across pages.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsAdReportRow` across all pages.
        """
        return self._iter_report_rows(
            "ads/query", request, BrandsAdReportResponse, BrandsAdReportRow, page_size
        )

    def iter_ads_async(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[BrandsAdReportRow]:
        """Iterate over all Apple Maps ad report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsAdReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "ads/query", request, BrandsAdReportResponse, BrandsAdReportRow, page_size
        )

    def iter_keywords(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[BrandsKeywordReportRow]:
        """Iterate over all Apple Maps keyword report rows across pages.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsKeywordReportRow` across all pages.
        """
        return self._iter_report_rows(
            "keywords/query",
            request,
            BrandsKeywordReportResponse,
            BrandsKeywordReportRow,
            page_size,
        )

    def iter_keywords_async(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[BrandsKeywordReportRow]:
        """Iterate over all Apple Maps keyword report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsKeywordReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "keywords/query",
            request,
            BrandsKeywordReportResponse,
            BrandsKeywordReportRow,
            page_size,
        )

    def iter_search_terms(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> Iterator[BrandsSearchTermReportRow]:
        """Iterate over all Apple Maps search term report rows across pages.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsSearchTermReportRow` across all pages.
        """
        return self._iter_report_rows(
            "searchterms/query",
            request,
            BrandsSearchTermReportResponse,
            BrandsSearchTermReportRow,
            page_size,
        )

    def iter_search_terms_async(
        self,
        request: BrandsReportingRequest | None = None,
        *,
        page_size: int = 5000,
    ) -> AsyncIterator[BrandsSearchTermReportRow]:
        """Iterate over all Apple Maps search term report rows asynchronously.

        Args:
            request: Report parameters; ``pagination`` is overridden.
            page_size: Rows per page (up to 5,000).

        Yields:
            Each :class:`BrandsSearchTermReportRow` across all pages.
        """
        return self._iter_report_rows_async(
            "searchterms/query",
            request,
            BrandsSearchTermReportResponse,
            BrandsSearchTermReportRow,
            page_size,
        )
