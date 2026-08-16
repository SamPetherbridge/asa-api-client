"""Suggestions resource for the Apple Ads Platform API v1.

Covers keyword, phrase, and category suggestion queries plus the
Target CPA suggestion for new Maximize Conversions campaigns.
"""

from typing import Any, TypeVar

from asa_api_client.v1.models.base import V1Model, V1Page, V1Pagination
from asa_api_client.v1.models.suggestions import (
    CategorySuggestion,
    KeywordSuggestion,
    PhraseSuggestion,
    TargetCpaSuggestion,
)
from asa_api_client.v1.query import Query
from asa_api_client.v1.resources.base import V1Resource

M = TypeVar("M", bound=V1Model)

_KEYWORDS_PATH = "keywords/query"
_PHRASES_PATH = "phrases/query"
_CATEGORIES_PATH = "categories/query"
_TARGET_CPAS_PATH = "target-cpas/query"


class SuggestionResource(V1Resource[KeywordSuggestion, KeywordSuggestion, KeywordSuggestion]):
    """Keyword, phrase, category, and Target CPA suggestion queries.

    All four endpoints are ``POST /v1/suggestions/<kind>/query`` with
    the shared ``{filters, sorting, pagination}`` body. Every request
    must identify the promoted object via two mandatory filters —
    ``promotedObjectId`` (``EQUALS``) and ``promotedObjectType``
    (``EQUALS``) — except the category ``SEARCH`` route. Filter values
    are always arrays of strings, and the results sort naturally by
    ``popularity`` descending.
    """

    base_path = "suggestions"
    model_class = KeywordSuggestion
    requires_account_context = True

    @staticmethod
    def _payload(query: Query | None) -> dict[str, Any]:
        """Serialize an optional query to its request body.

        Args:
            query: The caller's query, or None for an empty body.

        Returns:
            The ``{filters, sorting, pagination}`` dict.
        """
        return query.to_payload() if query is not None else {}

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

    def query_keywords(self, query: Query | None = None) -> V1Page[KeywordSuggestion]:
        """Query keyword suggestions.

        Calls ``POST /v1/suggestions/keywords/query`` to discover
        keywords relevant to an app that may not already be in the ad
        group. Seed the search with ``terms`` (``IN``) and scope
        markets with ``countriesOrRegions`` (``IN``) filters.

        Args:
            query: Filters (mandatory ``promotedObjectId`` and
                ``promotedObjectType``; optional ``terms``,
                ``countriesOrRegions``), sorting, and pagination.

        Returns:
            A page of keyword suggestions.
        """
        data = self._request("POST", _KEYWORDS_PATH, json=self._payload(query))
        return self._page_of(KeywordSuggestion, data)

    async def query_keywords_async(self, query: Query | None = None) -> V1Page[KeywordSuggestion]:
        """Query keyword suggestions asynchronously.

        Args:
            query: Filters, sorting, and pagination.

        Returns:
            A page of keyword suggestions.
        """
        data = await self._request_async("POST", _KEYWORDS_PATH, json=self._payload(query))
        return self._page_of(KeywordSuggestion, data)

    def query_phrases(self, query: Query | None = None) -> V1Page[PhraseSuggestion]:
        """Query phrase suggestions.

        Calls ``POST /v1/suggestions/phrases/query``. Select the route
        with a ``queryType`` filter: ``SUGGESTION`` discovers phrases
        for an app or brand, ``SEARCH`` looks up specific phrases.

        Args:
            query: Filters (mandatory ``promotedObjectId`` and
                ``promotedObjectType``; ``queryType`` route selector),
                sorting, and pagination.

        Returns:
            A page of phrase suggestions.
        """
        data = self._request("POST", _PHRASES_PATH, json=self._payload(query))
        return self._page_of(PhraseSuggestion, data)

    async def query_phrases_async(self, query: Query | None = None) -> V1Page[PhraseSuggestion]:
        """Query phrase suggestions asynchronously.

        Args:
            query: Filters, sorting, and pagination.

        Returns:
            A page of phrase suggestions.
        """
        data = await self._request_async("POST", _PHRASES_PATH, json=self._payload(query))
        return self._page_of(PhraseSuggestion, data)

    def query_categories(self, query: Query | None = None) -> V1Page[CategorySuggestion]:
        """Query category suggestions.

        Calls ``POST /v1/suggestions/categories/query``. Select the
        route with a ``queryType`` filter: ``SUGGESTION`` discovers
        categories for a specific app/brand (requires the promoted
        object filters), ``SEARCH`` looks up categories by name via a
        ``category`` filter (``IN`` for exact names, ``LIKE`` for
        pattern match) and may omit the promoted-object filters.

        Args:
            query: Filters, sorting, and pagination.

        Returns:
            A page of category suggestions.
        """
        data = self._request("POST", _CATEGORIES_PATH, json=self._payload(query))
        return self._page_of(CategorySuggestion, data)

    async def query_categories_async(
        self, query: Query | None = None
    ) -> V1Page[CategorySuggestion]:
        """Query category suggestions asynchronously.

        Args:
            query: Filters, sorting, and pagination.

        Returns:
            A page of category suggestions.
        """
        data = await self._request_async("POST", _CATEGORIES_PATH, json=self._payload(query))
        return self._page_of(CategorySuggestion, data)

    def query_target_cpa(self, query: Query | None = None) -> TargetCpaSuggestion:
        """Get the suggested Target CPA for a Maximize Conversions campaign.

        Calls ``POST /v1/suggestions/target-cpas/query``. The result is
        a single suggestion (not a list): the maximum tap-install CPI
        across the app's eligible markets over the last 28 days.
        Optionally scope markets with a ``countryOrRegion`` (``IN``)
        filter — note the singular field name on this endpoint.

        Args:
            query: Filters (mandatory ``promotedObjectId`` and
                ``promotedObjectType``; optional ``countryOrRegion``).

        Returns:
            The Target CPA suggestion.
        """
        data = self._request("POST", _TARGET_CPAS_PATH, json=self._payload(query))
        return TargetCpaSuggestion.model_validate(data.get("result") or {})

    async def query_target_cpa_async(self, query: Query | None = None) -> TargetCpaSuggestion:
        """Get the suggested Target CPA asynchronously.

        Args:
            query: Filters identifying the promoted object and
                optionally scoping markets.

        Returns:
            The Target CPA suggestion.
        """
        data = await self._request_async("POST", _TARGET_CPAS_PATH, json=self._payload(query))
        return TargetCpaSuggestion.model_validate(data.get("result") or {})
