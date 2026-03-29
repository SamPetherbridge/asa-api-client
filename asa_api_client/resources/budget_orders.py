"""Budget Order resource for the Apple Search Ads API.

Provides read-only access to budget orders for an organization.
"""

from typing import TYPE_CHECKING

from asa_api_client.models.base import PaginatedResponse
from asa_api_client.models.budget_orders import BudgetOrder
from asa_api_client.resources.base import BaseResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class BudgetOrderResource(BaseResource[BudgetOrder, BudgetOrder, BudgetOrder]):
    """Resource for retrieving budget orders.

    Budget orders define spending limits and purchase orders
    for an organization's advertising campaigns.

    Example:
        List all budget orders::

            orders = client.budget_orders.list()
            for order in orders:
                print(f"{order.name}: {order.budget}")

        Get a specific budget order::

            order = client.budget_orders.get(order_id=123)
    """

    base_path = "budgetorders"
    model_class = BudgetOrder

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the budget order resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        super().__init__(client)

    def list(self, *, limit: int = 1000, offset: int = 0) -> PaginatedResponse[BudgetOrder]:
        """List all budget orders for the organization.

        Args:
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            A paginated response containing budget orders.
        """
        params = {"limit": limit, "offset": offset}
        data = self._request("GET", params=params)
        return self._parse_list_response(data)

    async def list_async(
        self, *, limit: int = 1000, offset: int = 0
    ) -> PaginatedResponse[BudgetOrder]:
        """List all budget orders asynchronously.

        Args:
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            A paginated response containing budget orders.
        """
        params = {"limit": limit, "offset": offset}
        data = await self._request_async("GET", params=params)
        return self._parse_list_response(data)

    def get(self, budget_order_id: int) -> BudgetOrder:
        """Get a specific budget order by ID.

        Args:
            budget_order_id: The budget order ID.

        Returns:
            The budget order.
        """
        data = self._request("GET", str(budget_order_id))
        return self._parse_response(data)

    async def get_async(self, budget_order_id: int) -> BudgetOrder:
        """Get a specific budget order by ID asynchronously.

        Args:
            budget_order_id: The budget order ID.

        Returns:
            The budget order.
        """
        data = await self._request_async("GET", str(budget_order_id))
        return self._parse_response(data)
