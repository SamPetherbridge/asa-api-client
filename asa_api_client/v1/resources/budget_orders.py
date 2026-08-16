"""Budget order (shared budget) resource for Apple Ads Platform API v1.

Budget orders cap total spend across a group of campaigns within an ad
account. The REST resource is ``shared-budgets``; write bodies are sent
bare (no payload wrapper). Budget orders require the Line of Credit
(LOC) payment model.
"""

from typing import Any

from pydantic import BaseModel

from asa_api_client.v1.models.budget_orders import (
    SharedBudget,
    SharedBudgetCreate,
    SharedBudgetUpdate,
)
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)


class BudgetOrderResource(
    GettableMixin[SharedBudget, SharedBudgetCreate, SharedBudgetUpdate],
    QueryableMixin[SharedBudget, SharedBudgetCreate, SharedBudgetUpdate],
    CreatableMixin[SharedBudget, SharedBudgetCreate, SharedBudgetUpdate],
    UpdatableMixin[SharedBudget, SharedBudgetCreate, SharedBudgetUpdate],
    DeletableMixin[SharedBudget, SharedBudgetCreate, SharedBudgetUpdate],
    V1Resource[SharedBudget, SharedBudgetCreate, SharedBudgetUpdate],
):
    """Budget orders (``/v1/shared-budgets``).

    Supports get, query, create, update, and delete. Deletion is a
    soft-delete: all campaign assignments must be removed first, and
    deleted budget orders can only be queried back with the filter
    ``deleted EQUALS true``.

    Example:
        Query active budget orders::

            page = client.budget_orders.query(
                Query().where("systemStatus", "EQUALS", "ACTIVE")
            )
    """

    base_path = "shared-budgets"
    model_class = SharedBudget

    def _dump(self, data: BaseModel) -> dict[str, Any]:
        """Serialize a write model, keeping explicit nulls.

        Budget order updates use ``endTime: null`` to remove an end
        date (making the budget open-ended), so write bodies must
        distinguish "field omitted" from "field explicitly null".
        This serializes with ``exclude_unset`` instead of the base
        class's ``exclude_none``.

        Args:
            data: The model to serialize.

        Returns:
            The aliased JSON dict containing only explicitly set
            fields, with explicit None values preserved as null.
        """
        dumped: dict[str, Any] = data.model_dump(by_alias=True, exclude_unset=True, mode="json")
        return dumped
