"""Geo targeting search resource for the Apple Ads Platform API v1.

Both endpoints share the path ``/v1/search/geo``: GET searches
geographic locations by name, POST batch-resolves known IDs. Neither
fits the standard get/query mixins, so both are explicit methods.
"""

from typing import Any

from asa_api_client.v1.models.base import V1Page
from asa_api_client.v1.models.geo import (
    GeoEntityType,
    GeoSearchPostRequest,
    SearchEntity,
    SearchSupplySourceType,
)
from asa_api_client.v1.resources.base import V1Resource


class GeoResource(V1Resource[SearchEntity, GeoSearchPostRequest, GeoSearchPostRequest]):
    """Geo targeting location search (``/v1/search/geo``).

    Look up geographic locations (country, admin area, locality,
    postal code) whose numeric IDs are used as ad group geo targeting
    values.

    Example:
        Search localities on the App Store supply source::

            page = client.geo.search(
                supply_source="APPSTORE",
                query="san francisco",
                entity="Locality",
            )
    """

    base_path = "search/geo"
    model_class = SearchEntity

    def _search_params(
        self,
        supply_source: SearchSupplySourceType | str,
        query: str | None,
        entity: GeoEntityType | str | None,
        country_code: str | None,
        eligible: bool | None,
        offset: int | None,
        page_size: int | None,
    ) -> dict[str, Any]:
        """Build the GET query parameters, omitting unset options.

        Args:
            supply_source: The supply source scope (required).
            query: Search string (min 2 characters).
            entity: Geo entity type filter.
            country_code: ISO 3166-1 alpha-2 country scope.
            eligible: When True, exclude soft-blocked geos.
            offset: Zero-based index of the first result.
            page_size: Maximum results per page.

        Returns:
            The query parameter dict with documented parameter names.
        """
        params: dict[str, Any] = {
            "supplySource": SearchSupplySourceType(supply_source).value,
        }
        if query is not None:
            params["query"] = query
        if entity is not None:
            params["entity"] = GeoEntityType(entity).value
        if country_code is not None:
            # The API spells this query parameter all-lowercase.
            params["countrycode"] = country_code
        if eligible is not None:
            params["eligible"] = eligible
        if offset is not None:
            params["offset"] = offset
        if page_size is not None:
            params["pageSize"] = page_size
        return params

    def search(
        self,
        *,
        supply_source: SearchSupplySourceType | str,
        query: str | None = None,
        entity: GeoEntityType | str | None = None,
        country_code: str | None = None,
        eligible: bool | None = None,
        offset: int | None = None,
        page_size: int | None = None,
    ) -> V1Page[SearchEntity]:
        """Search geographic locations by name.

        Args:
            supply_source: The supply source scope: ``APPSTORE``
                (excludes postal codes) or ``MAPS`` (US/Canada only,
                excludes countries).
            query: Search string, minimum 2 characters; omit or use
                ``*`` to match all geos.
            entity: Filter results to one geo entity type.
            country_code: ISO 3166-1 alpha-2 country scope (sent as
                the ``countrycode`` parameter).
            eligible: When True, exclude soft-blocked geos; when False
                or omitted, include them with their eligibility data.
            offset: Zero-based index of the first result (default 0).
            page_size: Maximum results per page (default 20).

        Returns:
            A page of matching locations sorted by display name.

        Raises:
            ValidationError: If the query is too short or the supply
                source is unknown.
        """
        params = self._search_params(
            supply_source, query, entity, country_code, eligible, offset, page_size
        )
        data = self._request("GET", params=params)
        return self._parse_page(data)

    async def search_async(
        self,
        *,
        supply_source: SearchSupplySourceType | str,
        query: str | None = None,
        entity: GeoEntityType | str | None = None,
        country_code: str | None = None,
        eligible: bool | None = None,
        offset: int | None = None,
        page_size: int | None = None,
    ) -> V1Page[SearchEntity]:
        """Search geographic locations by name asynchronously.

        Args:
            supply_source: The supply source scope: ``APPSTORE``
                (excludes postal codes) or ``MAPS`` (US/Canada only,
                excludes countries).
            query: Search string, minimum 2 characters; omit or use
                ``*`` to match all geos.
            entity: Filter results to one geo entity type.
            country_code: ISO 3166-1 alpha-2 country scope (sent as
                the ``countrycode`` parameter).
            eligible: When True, exclude soft-blocked geos; when False
                or omitted, include them with their eligibility data.
            offset: Zero-based index of the first result (default 0).
            page_size: Maximum results per page (default 20).

        Returns:
            A page of matching locations sorted by display name.

        Raises:
            ValidationError: If the query is too short or the supply
                source is unknown.
        """
        params = self._search_params(
            supply_source, query, entity, country_code, eligible, offset, page_size
        )
        data = await self._request_async("GET", params=params)
        return self._parse_page(data)

    def lookup(self, request: GeoSearchPostRequest) -> V1Page[SearchEntity]:
        """Batch-resolve geographic locations by ID or legacy ID.

        Unlike :meth:`search`, this endpoint never filters by
        eligibility — soft-blocked geos are always returned with their
        eligibility data.

        Args:
            request: The batch of lookups with supply source and
                optional pagination.

        Returns:
            A deduplicated page of resolved locations.

        Raises:
            ValidationError: If the request body is invalid.
        """
        data = self._request("POST", json=self._dump(request))
        return self._parse_page(data)

    async def lookup_async(self, request: GeoSearchPostRequest) -> V1Page[SearchEntity]:
        """Batch-resolve geographic locations by ID asynchronously.

        Args:
            request: The batch of lookups with supply source and
                optional pagination.

        Returns:
            A deduplicated page of resolved locations.

        Raises:
            ValidationError: If the request body is invalid.
        """
        data = await self._request_async("POST", json=self._dump(request))
        return self._parse_page(data)
