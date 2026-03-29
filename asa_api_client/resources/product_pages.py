"""Product Page resource for the Apple Search Ads API.

Provides methods for retrieving custom product pages and their locale details.
"""

import builtins
from typing import TYPE_CHECKING

from asa_api_client.models.base import PaginatedResponse
from asa_api_client.models.product_pages import ProductPage, ProductPageLocaleDetail
from asa_api_client.resources.base import BaseResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class ProductPageResource(BaseResource[ProductPage, ProductPage, ProductPage]):
    """Resource for retrieving custom product pages for an app.

    Product pages represent custom App Store product pages that
    can be used as ad variations.

    Example:
        List product pages for an app::

            pages = client.product_pages(adam_id=123456789).list()
            for page in pages:
                print(f"{page.name}: {page.id}")

        Get locale details for a product page::

            details = client.product_pages(adam_id=123456789).get_locale_details("page-id")
    """

    model_class = ProductPage

    def __init__(self, client: "AppleSearchAdsClient", adam_id: int) -> None:
        """Initialize the product page resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
            adam_id: The App Store app ID.
        """
        super().__init__(client)
        self.adam_id = adam_id
        self.base_path = f"apps/{adam_id}/product-pages"

    def list(self, *, limit: int = 1000, offset: int = 0) -> PaginatedResponse[ProductPage]:
        """List all product pages for the app.

        Args:
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            A paginated response containing product pages.
        """
        params = {"limit": limit, "offset": offset}
        data = self._request("GET", params=params)
        return self._parse_list_response(data)

    async def list_async(
        self, *, limit: int = 1000, offset: int = 0
    ) -> PaginatedResponse[ProductPage]:
        """List all product pages for the app asynchronously.

        Args:
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            A paginated response containing product pages.
        """
        params = {"limit": limit, "offset": offset}
        data = await self._request_async("GET", params=params)
        return self._parse_list_response(data)

    def get(self, product_page_id: str) -> ProductPage:
        """Get a specific product page by ID.

        Args:
            product_page_id: The product page ID.

        Returns:
            The product page.
        """
        data = self._request("GET", product_page_id)
        return self._parse_response(data)

    async def get_async(self, product_page_id: str) -> ProductPage:
        """Get a specific product page by ID asynchronously.

        Args:
            product_page_id: The product page ID.

        Returns:
            The product page.
        """
        data = await self._request_async("GET", product_page_id)
        return self._parse_response(data)

    def get_locale_details(
        self, product_page_id: str
    ) -> builtins.list[ProductPageLocaleDetail]:
        """Get locale details for a product page.

        Args:
            product_page_id: The product page ID.

        Returns:
            List of locale-specific details.
        """
        data = self._request("GET", f"{product_page_id}/locale-details")
        items = data.get("data", [])
        return [ProductPageLocaleDetail.model_validate(item) for item in items]

    async def get_locale_details_async(
        self, product_page_id: str
    ) -> builtins.list[ProductPageLocaleDetail]:
        """Get locale details for a product page asynchronously.

        Args:
            product_page_id: The product page ID.

        Returns:
            List of locale-specific details.
        """
        data = await self._request_async("GET", f"{product_page_id}/locale-details")
        items = data.get("data", [])
        return [ProductPageLocaleDetail.model_validate(item) for item in items]
