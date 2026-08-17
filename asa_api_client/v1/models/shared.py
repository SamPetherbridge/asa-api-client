"""Models shared across multiple v1 resource groups.

These objects appear verbatim in more than one part of the API surface
(campaigns and ad groups both embed bid strategies and targeting data;
campaigns and budget orders both embed invoice details and shared-budget
assignments). They are defined once here; the resource-group model
modules re-export them so existing import paths keep working.
"""

from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import Money, V1Model


class BidStrategyType(StrEnum):
    """How bids are set in auctions."""

    MANUAL_CPT = "MANUAL_CPT"
    MANUAL_CPM = "MANUAL_CPM"
    MAX_CONVERSIONS = "MAX_CONVERSIONS"
    MAX_ENGAGEMENTS = "MAX_ENGAGEMENTS"


class BidStrategyGoal(StrEnum):
    """The outcome a bid strategy optimizes for."""

    IMPRESSION = "IMPRESSION"
    INSTALL = "INSTALL"
    TAP = "TAP"


class TargetingData(V1Model):
    """A targeting dimension's include/exclude value sets.

    Campaign-level targeting is include-only: ``exclude`` is unsupported
    for every campaign targeting dimension (unlike ad-group targeting).

    Attributes:
        include: Values to target.
        exclude: Values to exclude (ad-group targeting only).
    """

    include: list[str] | None = None
    exclude: list[str] | None = None


class BidStrategy(V1Model):
    """How a campaign or ad group competes in auctions.

    ``bid_strategy_type`` and ``bid_strategy_goal`` must both be
    supplied together and match an allowed pairing on create and update.

    Attributes:
        bid_strategy_type: The bidding type (manual or automated).
        bid_strategy_goal: The outcome the strategy optimizes for.
        bid: The bid amount for manual strategies.
    """

    bid_strategy_type: BidStrategyType | None = Field(default=None, alias="bidStrategyType")
    bid_strategy_goal: BidStrategyGoal | None = Field(default=None, alias="bidStrategyGoal")
    bid: Money | None = None


class SharedBudgetAssignment(V1Model):
    """One budget-order assignment in a campaign's ``sharedBudgets``.

    Attributes:
        budget_id: The assigned budget order's ID.
    """

    budget_id: int | None = Field(default=None, alias="budgetId")


class InvoiceDetail(V1Model):
    """Billing details for Line of Credit (LOC) accounts.

    Embedded in budget order and campaign objects. On budget order
    creation the API requires ``name``, ``primary_buyer_name``,
    ``primary_buyer_email``, and ``billing_email``; all fields are
    modeled optional because responses may omit any of them.

    Attributes:
        name: Billing contact name (required on budget-order create).
        client_name: Identifies the advertiser or product. Nullable.
        primary_buyer_name: Primary buyer's name (required on create).
        primary_buyer_email: Primary buyer's email address (required
            on create).
        order_number: Purchase order (PO) number. Nullable.
        billing_email: Billing email address (required on create).
    """

    name: str | None = None
    client_name: str | None = Field(default=None, alias="clientName")
    primary_buyer_name: str | None = Field(default=None, alias="primaryBuyerName")
    primary_buyer_email: str | None = Field(default=None, alias="primaryBuyerEmail")
    order_number: str | None = Field(default=None, alias="orderNumber")
    billing_email: str | None = Field(default=None, alias="billingEmail")
