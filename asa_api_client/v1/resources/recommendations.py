"""Recommendations resource for Apple Ads Platform API v1.

Surfaces system-generated optimization suggestions under
``/v1/recommendations``: daily budget recommendations
(``daily-budgets``) and Target CPA recommendations (``target-cpas``),
each with query, apply, and dismiss endpoints (all ``POST``). Query
bodies are unwrapped :class:`RecommendationQueryRequest` objects with
mandatory ``promotedObjectId`` / ``promotedObjectType`` filters; apply
and dismiss bodies are bare JSON arrays of request objects.
"""

from collections.abc import Sequence
from typing import Any

from asa_api_client.v1.models.base import V1Page, V1Pagination
from asa_api_client.v1.models.recommendations import (
    ApplyDailyCapRecommendation,
    ApplyTargetCpaRecommendation,
    DailyCapRecommendation,
    DailyCapRecommendationHistory,
    RecommendationQueryRequest,
    TargetCpaRecommendation,
    TargetCpaRecommendationHistory,
)
from asa_api_client.v1.resources.base import V1Resource


class RecommendationResource(
    V1Resource[TargetCpaRecommendation, ApplyTargetCpaRecommendation, ApplyTargetCpaRecommendation]
):
    """Recommendations (``/v1/recommendations``).

    All six endpoints are explicit methods rather than mixins because
    the group uses two result models (Target CPA and daily budget) and
    non-standard request bodies (bare arrays for apply/dismiss).
    Applying or dismissing moves a recommendation from ``AVAILABLE`` to
    a terminal state and returns immutable history records.

    Example:
        Query available Target CPA recommendations for an app::

            query = RecommendationQueryRequest.for_promoted_object(
                "123456789", "APPSTORE_APP"
            )
            page = client.recommendations.query_target_cpas(query)
    """

    base_path = "recommendations"
    model_class = TargetCpaRecommendation

    def _query_payload(self, query: RecommendationQueryRequest) -> dict[str, Any]:
        """Serialize a query request to its unwrapped JSON body.

        Args:
            query: The recommendation query request.

        Returns:
            The aliased, none-stripped JSON dict.
        """
        return self._dump(query)

    def _items_payload(
        self,
        items: Sequence[ApplyTargetCpaRecommendation] | Sequence[ApplyDailyCapRecommendation],
    ) -> list[dict[str, Any]]:
        """Serialize apply/dismiss items to the bare JSON array body.

        Args:
            items: The request objects, one per recommendation.

        Returns:
            The list of aliased, none-stripped JSON dicts.
        """
        return [self._dump(item) for item in items]

    def _parse_daily_budget_page(self, data: dict[str, Any]) -> V1Page[DailyCapRecommendation]:
        """Parse a daily budget query response into a typed page.

        Args:
            data: The API response body.

        Returns:
            A page of daily budget recommendations.
        """
        items = [DailyCapRecommendation.model_validate(item) for item in data.get("result") or []]
        pagination_data = data.get("pagination")
        pagination = V1Pagination.model_validate(pagination_data) if pagination_data else None
        return V1Page[DailyCapRecommendation](result=items, pagination=pagination)

    @staticmethod
    def _parse_tcpa_histories(data: dict[str, Any]) -> list[TargetCpaRecommendationHistory]:
        """Parse Target CPA history records from an apply/dismiss response.

        Args:
            data: The API response body (``pagination`` is null here).

        Returns:
            The history records, one per acted-on recommendation.
        """
        return [
            TargetCpaRecommendationHistory.model_validate(item) for item in data.get("result") or []
        ]

    @staticmethod
    def _parse_daily_cap_histories(data: dict[str, Any]) -> list[DailyCapRecommendationHistory]:
        """Parse daily budget history records from an apply/dismiss response.

        Args:
            data: The API response body (``pagination`` is null here).

        Returns:
            The history records, one per acted-on recommendation.
        """
        return [
            DailyCapRecommendationHistory.model_validate(item) for item in data.get("result") or []
        ]

    def query_target_cpas(
        self, query: RecommendationQueryRequest
    ) -> V1Page[TargetCpaRecommendation]:
        """Get Target CPA recommendations matching a query.

        Only campaigns using a Maximize Conversions bid strategy
        receive Target CPA recommendations.

        Args:
            query: The query request; must carry ``promotedObjectId``
                and ``promotedObjectType`` filters (use
                :meth:`RecommendationQueryRequest.for_promoted_object`).

        Returns:
            A page of Target CPA recommendations.
        """
        data = self._request("POST", "target-cpas/query", json=self._query_payload(query))
        return self._parse_page(data)

    async def query_target_cpas_async(
        self, query: RecommendationQueryRequest
    ) -> V1Page[TargetCpaRecommendation]:
        """Get Target CPA recommendations matching a query, asynchronously.

        Args:
            query: The query request with the mandatory
                promoted-object filters.

        Returns:
            A page of Target CPA recommendations.
        """
        data = await self._request_async(
            "POST", "target-cpas/query", json=self._query_payload(query)
        )
        return self._parse_page(data)

    def apply_target_cpas(
        self, recommendations: Sequence[ApplyTargetCpaRecommendation]
    ) -> list[TargetCpaRecommendationHistory]:
        """Apply one or more Target CPA recommendations.

        Applies each recommendation's ``recommendedTargetCPA`` (or the
        ``applied_target_cpa`` override) and moves it to ``APPLIED``.

        Args:
            recommendations: The recommendations to apply. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per applied recommendation.
        """
        data = self._request("POST", "target-cpas/apply", json=self._items_payload(recommendations))
        return self._parse_tcpa_histories(data)

    async def apply_target_cpas_async(
        self, recommendations: Sequence[ApplyTargetCpaRecommendation]
    ) -> list[TargetCpaRecommendationHistory]:
        """Apply one or more Target CPA recommendations, asynchronously.

        Args:
            recommendations: The recommendations to apply. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per applied recommendation.
        """
        data = await self._request_async(
            "POST", "target-cpas/apply", json=self._items_payload(recommendations)
        )
        return self._parse_tcpa_histories(data)

    def dismiss_target_cpas(
        self, recommendations: Sequence[ApplyTargetCpaRecommendation]
    ) -> list[TargetCpaRecommendationHistory]:
        """Dismiss one or more Target CPA recommendations.

        Moves each recommendation to ``DISMISSED`` without changing the
        campaign's bid strategy; ``applied_target_cpa`` is ignored.

        Args:
            recommendations: The recommendations to dismiss. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per dismissed
            recommendation.
        """
        data = self._request(
            "POST", "target-cpas/dismiss", json=self._items_payload(recommendations)
        )
        return self._parse_tcpa_histories(data)

    async def dismiss_target_cpas_async(
        self, recommendations: Sequence[ApplyTargetCpaRecommendation]
    ) -> list[TargetCpaRecommendationHistory]:
        """Dismiss one or more Target CPA recommendations, asynchronously.

        Args:
            recommendations: The recommendations to dismiss. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per dismissed
            recommendation.
        """
        data = await self._request_async(
            "POST", "target-cpas/dismiss", json=self._items_payload(recommendations)
        )
        return self._parse_tcpa_histories(data)

    def query_daily_budgets(
        self, query: RecommendationQueryRequest
    ) -> V1Page[DailyCapRecommendation]:
        """Get daily budget recommendations matching a query.

        Surfaced for campaigns that frequently exhaust their daily
        budget and may have more opportunities.

        Args:
            query: The query request; must carry ``promotedObjectId``
                and ``promotedObjectType`` filters (use
                :meth:`RecommendationQueryRequest.for_promoted_object`).

        Returns:
            A page of daily budget recommendations.
        """
        data = self._request("POST", "daily-budgets/query", json=self._query_payload(query))
        return self._parse_daily_budget_page(data)

    async def query_daily_budgets_async(
        self, query: RecommendationQueryRequest
    ) -> V1Page[DailyCapRecommendation]:
        """Get daily budget recommendations matching a query, asynchronously.

        Args:
            query: The query request with the mandatory
                promoted-object filters.

        Returns:
            A page of daily budget recommendations.
        """
        data = await self._request_async(
            "POST", "daily-budgets/query", json=self._query_payload(query)
        )
        return self._parse_daily_budget_page(data)

    def apply_daily_budgets(
        self, recommendations: Sequence[ApplyDailyCapRecommendation]
    ) -> list[DailyCapRecommendationHistory]:
        """Apply one or more daily budget recommendations.

        Updates each campaign's daily budget to the recommendation's
        ``suggestedDailyBudgetAmount`` (or the ``applied_daily_budget``
        override) and moves the recommendation to ``APPLIED``.

        Args:
            recommendations: The recommendations to apply. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per applied recommendation.
        """
        data = self._request(
            "POST", "daily-budgets/apply", json=self._items_payload(recommendations)
        )
        return self._parse_daily_cap_histories(data)

    async def apply_daily_budgets_async(
        self, recommendations: Sequence[ApplyDailyCapRecommendation]
    ) -> list[DailyCapRecommendationHistory]:
        """Apply one or more daily budget recommendations, asynchronously.

        Args:
            recommendations: The recommendations to apply. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per applied recommendation.
        """
        data = await self._request_async(
            "POST", "daily-budgets/apply", json=self._items_payload(recommendations)
        )
        return self._parse_daily_cap_histories(data)

    def dismiss_daily_budgets(
        self, recommendations: Sequence[ApplyDailyCapRecommendation]
    ) -> list[DailyCapRecommendationHistory]:
        """Dismiss one or more daily budget recommendations.

        Moves each recommendation to ``DISMISSED`` without changing the
        campaign's budget; ``applied_daily_budget`` is ignored.

        Args:
            recommendations: The recommendations to dismiss. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per dismissed
            recommendation.
        """
        data = self._request(
            "POST", "daily-budgets/dismiss", json=self._items_payload(recommendations)
        )
        return self._parse_daily_cap_histories(data)

    async def dismiss_daily_budgets_async(
        self, recommendations: Sequence[ApplyDailyCapRecommendation]
    ) -> list[DailyCapRecommendationHistory]:
        """Dismiss one or more daily budget recommendations, asynchronously.

        Args:
            recommendations: The recommendations to dismiss. All items
                must share the same ``promoted_object_id``.

        Returns:
            Immutable history records, one per dismissed
            recommendation.
        """
        data = await self._request_async(
            "POST", "daily-budgets/dismiss", json=self._items_payload(recommendations)
        )
        return self._parse_daily_cap_histories(data)
