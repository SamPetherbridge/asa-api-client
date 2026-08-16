"""Product pages resource for the Apple Ads Platform API v1.

All product-pages endpoints are read-only: pages are created and
managed in App Store Connect and surface here after a short
propagation delay.
"""

from typing import Any, TypeVar

from pydantic import BaseModel

from asa_api_client.v1.models.base import V1Page, V1Pagination
from asa_api_client.v1.models.product_pages import (
    AppLocaleDetails,
    ProductPageDetails,
    ProductPageLocaleDetails,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.base import GettableMixin, QueryableMixin, V1Resource

M = TypeVar("M", bound=BaseModel)


class ProductPageResource(
    GettableMixin[ProductPageDetails, ProductPageDetails, ProductPageDetails],
    QueryableMixin[ProductPageDetails, ProductPageDetails, ProductPageDetails],
    V1Resource[ProductPageDetails, ProductPageDetails, ProductPageDetails],
):
    """App Store product pages (DPPs, CPPs, and PPO variants).

    Read-only: product pages are managed in App Store Connect. Use
    :meth:`query` (filter by ``adamId``) to discover ``productPageId``
    values, then :meth:`query_locale_details` for localized content, or
    pass the ID to a ``CUSTOM_PRODUCT_PAGE`` creative.
    """

    base_path = "product-pages"
    model_class = ProductPageDetails

    def _build_url(self, path: str = "") -> str:
        """Build the full API URL, supporting base-rooted paths.

        Args:
            path: Path to append to ``base_path``; a leading ``/``
                roots the path at the API base URL instead (used for
                the ``/apps/{adamId}/locale-details/query`` endpoint).

        Returns:
            The full API URL.
        """
        if path.startswith("/"):
            base = self._client._base_url.rstrip("/")
            return f"{base}/{path.strip('/')}"
        return super()._build_url(path)

    def _parse_typed_page(self, data: dict[str, Any], model: type[M]) -> V1Page[M]:
        """Parse a list response into a page of an arbitrary model.

        Args:
            data: The API response body.
            model: The model class to validate each item against.

        Returns:
            A V1Page of parsed items with pagination metadata.
        """
        items = [model.model_validate(item) for item in data.get("result") or []]
        pagination_data = data.get("pagination")
        pagination = V1Pagination.model_validate(pagination_data) if pagination_data else None
        return V1Page[M](result=items, pagination=pagination)

    def query_locale_details(self, query: Query) -> V1Page[ProductPageLocaleDetails]:
        """Query localized content for a product page.

        The API requires a ``productPageId`` EQUALS filter; ``language``
        and ``languageCode`` EQUALS filters optionally narrow locales.

        Args:
            query: Query with at least a ``productPageId`` filter.

        Returns:
            A page of locale details, one per page + locale combination.

        Example:
            Fetch all locales of a product page::

                page = client.product_pages.query_locale_details(
                    Query().where("productPageId", "EQUALS", page_id)
                )
        """
        data = self._request("POST", "locale-details/query", json=query.to_payload())
        return self._parse_typed_page(data, ProductPageLocaleDetails)

    async def query_locale_details_async(self, query: Query) -> V1Page[ProductPageLocaleDetails]:
        """Query localized content for a product page asynchronously.

        Args:
            query: Query with at least a ``productPageId`` filter.

        Returns:
            A page of locale details, one per page + locale combination.
        """
        data = await self._request_async("POST", "locale-details/query", json=query.to_payload())
        return self._parse_typed_page(data, ProductPageLocaleDetails)

    def query_app_locale_details(
        self, adam_id: int, query: Query | None = None
    ) -> V1Page[AppLocaleDetails]:
        """Query an app's Default Product Page locale details.

        Covers the default page only; Custom Product Pages require
        :meth:`query_locale_details`. Returns all configured locales by
        default; filter on ``languageCode`` for a specific locale.

        Args:
            adam_id: The App Store app identifier (Adam ID).
            query: Optional query (e.g. a ``languageCode`` filter).

        Returns:
            A page of locale details, one per supported locale.
        """
        payload = query.to_payload() if query is not None else {}
        data = self._request("POST", f"/apps/{adam_id}/locale-details/query", json=payload)
        return self._parse_typed_page(data, AppLocaleDetails)

    async def query_app_locale_details_async(
        self, adam_id: int, query: Query | None = None
    ) -> V1Page[AppLocaleDetails]:
        """Query an app's Default Product Page locale details asynchronously.

        Args:
            adam_id: The App Store app identifier (Adam ID).
            query: Optional query (e.g. a ``languageCode`` filter).

        Returns:
            A page of locale details, one per supported locale.
        """
        payload = query.to_payload() if query is not None else {}
        data = await self._request_async(
            "POST", f"/apps/{adam_id}/locale-details/query", json=payload
        )
        return self._parse_typed_page(data, AppLocaleDetails)
