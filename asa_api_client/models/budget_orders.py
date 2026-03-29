"""Budget Order models for the Apple Search Ads API.

Budget orders define spending limits and purchase orders
for an organization's advertising campaigns.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from asa_api_client.models.base import Money


class BudgetOrderStatus(StrEnum):
    """Budget order status values."""

    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    COMPLETED = "COMPLETED"
    EXHAUSTED = "EXHAUSTED"
    INACTIVE = "INACTIVE"


class BudgetOrder(BaseModel):
    """An Apple Search Ads budget order.

    Attributes:
        id: The budget order ID.
        parent_org_id: The parent organization ID.
        name: The budget order name.
        budget: The total budget amount.
        status: The budget order status.
        start_date: When the budget order starts.
        end_date: When the budget order ends.
        order_number: The purchase order number.
        supply_sources: Supply sources this budget order applies to.
        billing_email: The billing email address.
        client_name: The client name.
        primary_buyer_email: The primary buyer's email.
        primary_buyer_name: The primary buyer's name.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    parent_org_id: int | None = Field(default=None, alias="parentOrgId")
    name: str | None = None
    budget: Money | None = None
    status: BudgetOrderStatus | str | None = None
    start_date: datetime | None = Field(default=None, alias="startDate")
    end_date: datetime | None = Field(default=None, alias="endDate")
    order_number: str | None = Field(default=None, alias="orderNumber")
    supply_sources: list[str] | None = Field(default=None, alias="supplySources")
    billing_email: str | None = Field(default=None, alias="billingEmail")
    client_name: str | None = Field(default=None, alias="clientName")
    primary_buyer_email: str | None = Field(default=None, alias="primaryBuyerEmail")
    primary_buyer_name: str | None = Field(default=None, alias="primaryBuyerName")
