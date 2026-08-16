"""Apps resource for the Apple Ads Platform API v1.

Covers App Store app search, per-app details, ad-supported language
metadata, app eligibility checks, and creative rejection reasons.
"""

from typing import Any, TypeVar

from asa_api_client.v1.models.apps import (
    AppDetails,
    AppInfo,
    AppSupportedLanguages,
    CreativeRejectionReason,
    EligibilityResponse,
)
from asa_api_client.v1.models.base import V1Model, V1Page, V1Pagination
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.base import V1Resource

M = TypeVar("M", bound=V1Model)

_SEARCH_PATH = "search/apps"
_DETAILS_PATH = "apps"
_SUPPORTED_LANGUAGES_PATH = "metadata/apps/supported-languages/query"
_ELIGIBILITIES_PATH = "eligibilities/apps/query"
_REJECTION_REASONS_PATH = "rejection-reasons/apps"


class AppResource(V1Resource[AppDetails, AppDetails, AppDetails]):
    """App search, details, languages, eligibility, and rejection reasons.

    The endpoints in this group live under several unrelated URL
    prefixes (``search/apps``, ``apps``, ``metadata/apps``,
    ``eligibilities/apps``, ``rejection-reasons/apps``), so the class
    uses an empty ``base_path`` with explicit per-endpoint methods
    instead of the CRUD/query mixins.
    """

    base_path = ""
    model_class = AppDetails
    requires_account_context = True

    @staticmethod
    def _search_params(
        query: str | None,
        return_owned_apps: bool | None,
        cpids: str | list[str] | None,
        store_fronts: list[str] | None,
        offset: int | None,
        limit: int | None,
    ) -> dict[str, Any]:
        """Build the query-parameter dict for app search.

        Args:
            query: Free-text match against app and developer names.
            return_owned_apps: When True, return apps owned by the
                caller's organization.
            cpids: iTunes content provider ID(s); lists are joined into
                the documented comma-separated form.
            store_fronts: App Store country/region codes; each value is
                sent as a repeated ``storeFronts`` parameter.
            offset: Pagination offset.
            limit: Maximum number of results.

        Returns:
            The parameter dict with unset values omitted.
        """
        params: dict[str, Any] = {}
        if query is not None:
            params["query"] = query
        if return_owned_apps is not None:
            params["returnOwnedApps"] = return_owned_apps
        if cpids is not None:
            params["cpids"] = ",".join(cpids) if isinstance(cpids, list) else cpids
        if store_fronts is not None:
            params["storeFronts"] = store_fronts
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        return params

    def _page_of(self, model: type[M], data: dict[str, Any]) -> V1Page[M]:
        """Parse a list envelope into a typed page of ``model``.

        Args:
            model: The item model to validate each result entry with.
            data: The API response body.

        Returns:
            A V1Page of parsed items with pagination metadata.
        """
        items = [model.model_validate(item) for item in data.get("result") or []]
        pagination_data = data.get("pagination")
        pagination = V1Pagination.model_validate(pagination_data) if pagination_data else None
        return V1Page[M](result=items, pagination=pagination)

    def search(
        self,
        query: str | None = None,
        *,
        return_owned_apps: bool | None = None,
        cpids: str | list[str] | None = None,
        store_fronts: list[str] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> V1Page[AppInfo]:
        """Search the App Store for apps (``GET /v1/search/apps``).

        At least one of ``query``, ``cpids``, or
        ``return_owned_apps=True`` must be supplied, or the API rejects
        the request with ``INVALID_INPUT``.

        Args:
            query: Free-text match against app name and developer name
                (min 3 characters; 2 for CJK).
            return_owned_apps: When True, return apps owned by the
                caller's organization.
            cpids: iTunes content provider ID(s) to scope the search to.
            store_fronts: App Store country/region codes (ISO 3166-1
                alpha-2) to search within.
            offset: Pagination offset (default 0 server-side).
            limit: Maximum results per page (default 20 server-side).

        Returns:
            A page of matching apps.
        """
        params = self._search_params(query, return_owned_apps, cpids, store_fronts, offset, limit)
        data = self._request("GET", _SEARCH_PATH, params=params)
        return self._page_of(AppInfo, data)

    async def search_async(
        self,
        query: str | None = None,
        *,
        return_owned_apps: bool | None = None,
        cpids: str | list[str] | None = None,
        store_fronts: list[str] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> V1Page[AppInfo]:
        """Search the App Store for apps asynchronously.

        Args:
            query: Free-text match against app name and developer name.
            return_owned_apps: When True, return apps owned by the
                caller's organization.
            cpids: iTunes content provider ID(s) to scope the search to.
            store_fronts: App Store country/region codes to search within.
            offset: Pagination offset.
            limit: Maximum results per page.

        Returns:
            A page of matching apps.
        """
        params = self._search_params(query, return_owned_apps, cpids, store_fronts, offset, limit)
        data = await self._request_async("GET", _SEARCH_PATH, params=params)
        return self._page_of(AppInfo, data)

    def get(self, adam_id: int | str) -> AppDetails:
        """Get App Store details for one app (``GET /v1/apps/{adamId}``).

        Args:
            adam_id: The app's Adam ID.

        Returns:
            The app's App Store details.

        Raises:
            NotFoundError: If no app exists for the Adam ID.
        """
        data = self._request("GET", f"{_DETAILS_PATH}/{adam_id}")
        return self._parse_item(data)

    async def get_async(self, adam_id: int | str) -> AppDetails:
        """Get App Store details for one app asynchronously.

        Args:
            adam_id: The app's Adam ID.

        Returns:
            The app's App Store details.

        Raises:
            NotFoundError: If no app exists for the Adam ID.
        """
        data = await self._request_async("GET", f"{_DETAILS_PATH}/{adam_id}")
        return self._parse_item(data)

    def query_supported_languages(
        self, query: Query | None = None
    ) -> V1Page[AppSupportedLanguages]:
        """Query ad-supported languages per country/region.

        Calls ``POST /v1/metadata/apps/supported-languages/query``. An
        empty query returns all supported countries/regions.

        Args:
            query: Filters (``countryCode``, ``name``), sorting, and
                pagination.

        Returns:
            A page of per-market language metadata.
        """
        payload = query.to_payload() if query is not None else {}
        data = self._request("POST", _SUPPORTED_LANGUAGES_PATH, json=payload)
        return self._page_of(AppSupportedLanguages, data)

    async def query_supported_languages_async(
        self, query: Query | None = None
    ) -> V1Page[AppSupportedLanguages]:
        """Query ad-supported languages per country/region asynchronously.

        Args:
            query: Filters (``countryCode``, ``name``), sorting, and
                pagination.

        Returns:
            A page of per-market language metadata.
        """
        payload = query.to_payload() if query is not None else {}
        data = await self._request_async("POST", _SUPPORTED_LANGUAGES_PATH, json=payload)
        return self._page_of(AppSupportedLanguages, data)

    def query_eligibilities(self, query: Query | None = None) -> V1Page[EligibilityResponse]:
        """Check app eligibility (``POST /v1/eligibilities/apps/query``).

        Filterable fields: ``adamId``, ``supplyPlacement``,
        ``supplySource``, ``countryOrRegion``, ``deviceClass``,
        ``state``. Batch-check multiple apps by filtering on multiple
        ``adamId`` values in one request.

        Args:
            query: Filters, sorting, and pagination.

        Returns:
            A page of eligibility rows, one per app x placement x
            source x country x device class combination.
        """
        payload = query.to_payload() if query is not None else {}
        data = self._request("POST", _ELIGIBILITIES_PATH, json=payload)
        return self._page_of(EligibilityResponse, data)

    async def query_eligibilities_async(
        self, query: Query | None = None
    ) -> V1Page[EligibilityResponse]:
        """Check app eligibility asynchronously.

        Args:
            query: Filters, sorting, and pagination.

        Returns:
            A page of eligibility rows.
        """
        payload = query.to_payload() if query is not None else {}
        data = await self._request_async("POST", _ELIGIBILITIES_PATH, json=payload)
        return self._page_of(EligibilityResponse, data)

    def query_rejection_reasons(
        self, query: Query | None = None
    ) -> V1Page[CreativeRejectionReason]:
        """Query creative rejection reasons.

        Calls ``POST /v1/rejection-reasons/apps/query`` to explain why
        creatives failed Apple review.

        Args:
            query: Filters (e.g. ``adamId``), sorting (e.g.
                ``creationTime`` descending), and pagination.

        Returns:
            A page of rejection reason records.
        """
        payload = query.to_payload() if query is not None else {}
        data = self._request("POST", f"{_REJECTION_REASONS_PATH}/query", json=payload)
        return self._page_of(CreativeRejectionReason, data)

    async def query_rejection_reasons_async(
        self, query: Query | None = None
    ) -> V1Page[CreativeRejectionReason]:
        """Query creative rejection reasons asynchronously.

        Args:
            query: Filters, sorting, and pagination.

        Returns:
            A page of rejection reason records.
        """
        payload = query.to_payload() if query is not None else {}
        data = await self._request_async("POST", f"{_REJECTION_REASONS_PATH}/query", json=payload)
        return self._page_of(CreativeRejectionReason, data)

    def get_rejection_reason(self, rejection_reason_id: int | str) -> CreativeRejectionReason:
        """Get one creative rejection reason by ID.

        Calls ``GET /v1/rejection-reasons/apps/{rejectionReasonId}``.

        Args:
            rejection_reason_id: The rejection reason record ID.

        Returns:
            The rejection reason record.

        Raises:
            NotFoundError: If no record exists for the ID.
        """
        data = self._request("GET", f"{_REJECTION_REASONS_PATH}/{rejection_reason_id}")
        return CreativeRejectionReason.model_validate(data.get("result", data))

    async def get_rejection_reason_async(
        self, rejection_reason_id: int | str
    ) -> CreativeRejectionReason:
        """Get one creative rejection reason by ID asynchronously.

        Args:
            rejection_reason_id: The rejection reason record ID.

        Returns:
            The rejection reason record.

        Raises:
            NotFoundError: If no record exists for the ID.
        """
        data = await self._request_async("GET", f"{_REJECTION_REASONS_PATH}/{rejection_reason_id}")
        return CreativeRejectionReason.model_validate(data.get("result", data))
