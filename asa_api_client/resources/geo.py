"""Geo search resource for the Apple Search Ads API.

Provides methods for searching geographic locations used
in audience targeting.
"""

import builtins
from typing import TYPE_CHECKING, Any

from asa_api_client.models.geo import GeoLocation
from asa_api_client.resources.base import BaseResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class GeoResource(BaseResource[GeoLocation, GeoLocation, GeoLocation]):
    """Resource for searching geographic locations.

    Used to find admin areas and localities for geo-targeting
    in ad groups.

    Example:
        Search for locations::

            locations = client.geo.search(query="California", country_code="US")
            for loc in locations:
                print(f"{loc.display_name} ({loc.entity})")

        Search with entity type filter::

            cities = client.geo.search(
                query="San",
                country_code="US",
                entity="Locality",
            )
    """

    base_path = "search/geo"
    model_class = GeoLocation

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the geo search resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        super().__init__(client)

    def search(
        self,
        *,
        query: str,
        country_code: str,
        entity: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> builtins.list[GeoLocation]:
        """Search for geographic locations.

        Args:
            query: The search query string.
            country_code: The country code to search within.
            entity: Optional entity type filter (Country, AdminArea, Locality).
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            List of matching geographic locations.
        """
        params: dict[str, Any] = {
            "query": query,
            "countrycode": country_code,
            "limit": limit,
            "offset": offset,
        }
        if entity:
            params["entity"] = entity

        data = self._request("GET", params=params)
        items = data.get("data", [])
        return [GeoLocation.model_validate(item) for item in items]

    async def search_async(
        self,
        *,
        query: str,
        country_code: str,
        entity: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> builtins.list[GeoLocation]:
        """Search for geographic locations asynchronously.

        Args:
            query: The search query string.
            country_code: The country code to search within.
            entity: Optional entity type filter.
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            List of matching geographic locations.
        """
        params: dict[str, Any] = {
            "query": query,
            "countrycode": country_code,
            "limit": limit,
            "offset": offset,
        }
        if entity:
            params["entity"] = entity

        data = await self._request_async("GET", params=params)
        items = data.get("data", [])
        return [GeoLocation.model_validate(item) for item in items]
