"""Countries or Regions resource for the Apple Search Ads API.

Provides access to supported countries and regions for advertising.
"""

import builtins
from typing import TYPE_CHECKING

from asa_api_client.models.countries import CountryOrRegion
from asa_api_client.resources.base import BaseResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class CountryOrRegionResource(BaseResource[CountryOrRegion, CountryOrRegion, CountryOrRegion]):
    """Resource for retrieving supported countries and regions.

    Returns countries/regions where Apple Ads is available,
    along with their supported languages.

    Example:
        List all supported countries::

            countries = client.countries_or_regions.list()
            for country in countries:
                print(f"{country.country_or_region}: {country.default_language}")
    """

    base_path = "countries-or-regions"
    model_class = CountryOrRegion

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the countries/regions resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        super().__init__(client)

    def list(
        self,
        *,
        countries_or_regions: builtins.list[str] | None = None,
    ) -> builtins.list[CountryOrRegion]:
        """List supported countries and regions.

        Args:
            countries_or_regions: Optional list of ISO alpha-2 codes to filter by.

        Returns:
            List of supported countries/regions.
        """
        params = {}
        if countries_or_regions:
            params["countriesOrRegions"] = ",".join(countries_or_regions)

        data = self._request("GET", params=params)
        items = data.get("data", [])
        return [CountryOrRegion.model_validate(item) for item in items]

    async def list_async(
        self,
        *,
        countries_or_regions: builtins.list[str] | None = None,
    ) -> builtins.list[CountryOrRegion]:
        """List supported countries and regions asynchronously.

        Args:
            countries_or_regions: Optional list of ISO alpha-2 codes to filter by.

        Returns:
            List of supported countries/regions.
        """
        params = {}
        if countries_or_regions:
            params["countriesOrRegions"] = ",".join(countries_or_regions)

        data = await self._request_async("GET", params=params)
        items = data.get("data", [])
        return [CountryOrRegion.model_validate(item) for item in items]
