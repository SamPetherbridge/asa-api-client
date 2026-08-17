"""Models for Apple Ads Platform API v1 budget orders (shared budgets).

Budget orders put a spending cap across a group of campaigns within an
ad account. The REST resource is ``shared-budgets``; the entity is
documented as a "budget order". Budget orders require the Line of
Credit (LOC) payment model and are unavailable on PAYG accounts.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_serializer

from asa_api_client.v1.models.base import Money, V1Model
from asa_api_client.v1.models.shared import (
    InvoiceDetail,
)
from asa_api_client.v1.models.shared import (
    SharedBudgetAssignment as SharedBudgetAssignment,
)

# The API requires yyyy-MM-dd'T'HH:mm:ss.SSS timestamps in UTC with no
# timezone suffix.
_TIMESTAMP_FIELDS = ("start_time", "end_time")

# adAccountIds must contain exactly one ID on both create and update.
_SingleAdAccountIdList = Annotated[list[int], Field(min_length=1, max_length=1)]


def _format_timestamp(value: datetime | None) -> str | None:
    """Format a datetime as the API's ``yyyy-MM-dd'T'HH:mm:ss.SSS`` shape.

    Args:
        value: The naive UTC datetime to format, or None.

    Returns:
        The formatted timestamp string, or None when value is None.
    """
    if value is None:
        return None
    return f"{value:%Y-%m-%dT%H:%M:%S}.{value.microsecond // 1000:03d}"


class PaymentModel(StrEnum):
    """Billing model determining payment method and budget availability.

    Attributes:
        PAYG: Pay As You Go. Default when no payment model is
            configured; budget orders are NOT available.
        LOC: Line of Credit. Monthly invoicing model required to use
            budget orders.
    """

    PAYG = "PAYG"
    LOC = "LOC"


class BudgetSystemStatus(StrEnum):
    """Read-only, system-computed status of a budget order.

    Check ``systemStatusReasons`` for the cause when not ACTIVE.

    Attributes:
        ACTIVE: Assigned campaigns can draw spend.
        INACTIVE: No spend drawn until the underlying condition is
            resolved.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class BudgetSystemStatusReason(StrEnum):
    """Reasons appearing in a budget order's ``systemStatusReasons``.

    Attributes:
        CANCELED: Manually canceled; no longer eligible to receive
            spend.
        CAMPAIGN_BUDGET_UNASSIGNED: No campaigns currently assigned to
            draw against this budget.
        DELETED_BY_USER: Soft-deleted by a user action.
        EXHAUSTED: Monetary cap fully consumed; increase the value or
            create a new budget.
        PROCESSING: Recently created or modified, still processing.
            Transient.
        SCHEDULE_EXPIRED: The endTime has passed.
        SCHEDULE_PENDING: The startTime is not yet reached.
    """

    CANCELED = "CANCELED"
    CAMPAIGN_BUDGET_UNASSIGNED = "CAMPAIGN_BUDGET_UNASSIGNED"
    DELETED_BY_USER = "DELETED_BY_USER"
    EXHAUSTED = "EXHAUSTED"
    PROCESSING = "PROCESSING"
    SCHEDULE_EXPIRED = "SCHEDULE_EXPIRED"
    SCHEDULE_PENDING = "SCHEDULE_PENDING"


class InvoiceDetailUpdate(V1Model):
    """Partial update of a budget order's invoice details.

    All fields optional; omitted fields stay unchanged.

    Attributes:
        name: Billing contact name.
        client_name: Identifies the advertiser or product.
        primary_buyer_name: Primary buyer's name.
        primary_buyer_email: Primary buyer's email address.
        order_number: Purchase order (PO) number.
        billing_email: Billing email address.
    """

    name: str | None = None
    client_name: str | None = Field(default=None, alias="clientName")
    primary_buyer_name: str | None = Field(default=None, alias="primaryBuyerName")
    primary_buyer_email: str | None = Field(default=None, alias="primaryBuyerEmail")
    order_number: str | None = Field(default=None, alias="orderNumber")
    billing_email: str | None = Field(default=None, alias="billingEmail")


class SharedBudget(V1Model):
    """A budget order ("shared budget") capping spend across campaigns.

    Attributes:
        id: Unique budget identifier. Read-only.
        name: Non-empty label. Mutable.
        start_time: UTC start of the budget's flight period. Must be
            tomorrow (midnight UTC) or later at set-time. Mutable.
        end_time: UTC end of the flight period; absent means
            open-ended. Mutable.
        value: The monetary spending cap. Mutable.
        ad_account_ids: Ad account IDs the budget applies to; exactly
            one is allowed at creation. Mutable.
        org_id: The owning organization. Read-only.
        system_status: Whether the budget is currently usable.
            Read-only.
        system_status_reasons: Causes when the budget is not ACTIVE.
            Read-only.
        invoice_detail: Billing details (LOC accounts). Mutable.
        creation_time: When the budget order was created. Read-only.
        modification_time: When it was last modified. Read-only.
        deleted: Soft-delete flag. Read-only.
    """

    id: int | None = None
    name: str | None = None
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    value: Money | None = None
    ad_account_ids: list[int] | None = Field(default=None, alias="adAccountIds")
    org_id: int | None = Field(default=None, alias="orgId")
    system_status: BudgetSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[BudgetSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    invoice_detail: InvoiceDetail | None = Field(default=None, alias="invoiceDetail")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    deleted: bool | None = None


class SharedBudgetCreate(V1Model):
    """Request body for creating a budget order.

    Attributes:
        name: Non-empty budget order name.
        start_time: UTC start; must be tomorrow (midnight UTC) or
            later — today is rejected.
        end_time: UTC end; must be after start_time. Omit for an
            open-ended budget.
        value: The spending cap; currency must match the ad account's
            currency.
        ad_account_ids: Exactly ONE ad account ID; the API rejects
            more than one.
        invoice_detail: Billing details, required for LOC accounts
            (name, primary_buyer_name, primary_buyer_email, and
            billing_email must be set).
    """

    name: str = Field(min_length=1)
    start_time: datetime = Field(alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    value: Money
    ad_account_ids: _SingleAdAccountIdList = Field(alias="adAccountIds")
    invoice_detail: InvoiceDetail = Field(alias="invoiceDetail")

    @field_serializer(*_TIMESTAMP_FIELDS)
    def _serialize_timestamps(self, value: datetime | None) -> str | None:
        """Serialize timestamps in the API's millisecond format."""
        return _format_timestamp(value)


class SharedBudgetUpdate(V1Model):
    """Partial-update request body for a budget order.

    Only include fields to change; omitted fields stay unchanged. On
    ACTIVE budget orders the end date can only be shortened — except
    that explicitly setting ``end_time=None`` removes the expiration
    entirely (open-ended).

    Attributes:
        name: New non-empty name.
        start_time: New UTC start; must be tomorrow (midnight UTC) or
            later — today is rejected.
        end_time: New UTC end. Set explicitly to None to remove the
            expiration; leave unset to keep the current value.
        value: New spending cap; increase the amount to extend a
            budget approaching exhaustion.
        ad_account_ids: Exactly one ad account ID.
        invoice_detail: Partial invoice-detail update.
    """

    name: str | None = None
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    value: Money | None = None
    ad_account_ids: _SingleAdAccountIdList | None = Field(default=None, alias="adAccountIds")
    invoice_detail: InvoiceDetailUpdate | None = Field(default=None, alias="invoiceDetail")

    @field_serializer(*_TIMESTAMP_FIELDS)
    def _serialize_timestamps(self, value: datetime | None) -> str | None:
        """Serialize timestamps in the API's millisecond format."""
        return _format_timestamp(value)


class SharedBudgetAssignmentCreate(V1Model):
    """Assignment entry embedded in a CampaignCreate ``sharedBudgets`` array.

    Campaigns still require a ``dailyBudget`` regardless: dailyBudget
    caps daily spend; each shared budget caps spend over its flight
    period. Multiple assignments per campaign require strictly
    non-overlapping schedules.

    Attributes:
        budget_id: The budget order to assign the campaign to.
    """

    budget_id: int | None = Field(default=None, alias="budgetId")


class SharedBudgetAssignmentUpdate(V1Model):
    """Assignment entry embedded in a CampaignUpdate ``sharedBudgets`` array.

    Attributes:
        budget_id: The budget order to assign; omit to leave the
            current assignment unchanged.
    """

    budget_id: int | None = Field(default=None, alias="budgetId")
