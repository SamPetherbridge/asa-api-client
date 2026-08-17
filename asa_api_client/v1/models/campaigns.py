"""Models for the Apple Ads Platform API v1 campaigns endpoints.

Campaigns are the top-level advertising containers: each belongs to one
ad account and promotes either an App Store app or a brand on Apple
Maps. This module defines the ``Campaign`` read model, its
``CampaignCreate``/``CampaignUpdate`` write counterparts, and the
supporting enums and value objects documented in the campaigns group.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_serializer

from asa_api_client.v1.models.base import Money, V1Model
from asa_api_client.v1.models.shared import (
    BidStrategy,
    InvoiceDetail,
    SharedBudgetAssignment,
    TargetingData,
)
from asa_api_client.v1.models.shared import (
    BidStrategyGoal as BidStrategyGoal,
)
from asa_api_client.v1.models.shared import (
    BidStrategyType as BidStrategyType,
)


class BillingEvent(StrEnum):
    """The event an advertiser is charged for; immutable after create.

    ``IMPRESSIONS`` (CPM) is only valid for Apple Maps campaigns
    (``promotedObjectType: BUSINESS_BRAND``); App Store campaigns must
    use ``TAPS``.
    """

    TAPS = "TAPS"
    IMPRESSIONS = "IMPRESSIONS"


class PromotedObjectType(StrEnum):
    """What a campaign promotes; immutable after create.

    ``APPSTORE_APP`` promotes an iOS app (``promotedObjectId`` is the
    app's adamId); ``BUSINESS_BRAND`` promotes a brand on Apple Maps
    (``promotedObjectId`` is the brand's resource ID).
    """

    APPSTORE_APP = "APPSTORE_APP"
    BUSINESS_BRAND = "BUSINESS_BRAND"


class CampaignStatus(StrEnum):
    """Advertiser intent for whether the campaign should run."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class CampaignSystemStatus(StrEnum):
    """System-computed serving state (read-only)."""

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class CampaignDisplayStatus(StrEnum):
    """Rolled-up, user-facing status label (read-only, derived)."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ON_HOLD = "ON_HOLD"
    LIMITED = "LIMITED"
    PROCESSING = "PROCESSING"
    DELETED = "DELETED"


class CampaignSystemStatusReason(StrEnum):
    """Blocking reasons present when ``systemStatus`` is NOT_RUNNING."""

    PROCESSING = "PROCESSING"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    FEATURE_NOT_YET_AVAILABLE = "FEATURE_NOT_YET_AVAILABLE"
    FEATURE_NO_LONGER_AVAILABLE = "FEATURE_NO_LONGER_AVAILABLE"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    DELETED_BY_USER = "DELETED_BY_USER"
    USER_REQUESTED_ACCOUNT_SUSPENSION = "USER_REQUESTED_ACCOUNT_SUSPENSION"
    CAMPAIGN_DELETED_FOR_BASIC_MSF_MIGRATION = "CAMPAIGN_DELETED_FOR_BASIC_MSF_MIGRATION"
    SCHEDULE_PENDING = "SCHEDULE_PENDING"
    SCHEDULE_EXPIRED = "SCHEDULE_EXPIRED"
    APP_NOT_ELIGIBLE = "APP_NOT_ELIGIBLE"
    APP_NOT_ELIGIBLE_SEARCHADS = "APP_NOT_ELIGIBLE_SEARCHADS"
    APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT = "APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT"
    APP_NOT_PUBLISHED_YET = "APP_NOT_PUBLISHED_YET"
    APP_NOT_CATEGORIZED = "APP_NOT_CATEGORIZED"
    APP_SENSITIVE_CONTENT = "APP_SENSITIVE_CONTENT"
    APP_DOC_APPROVAL_REJECTED = "APP_DOC_APPROVAL_REJECTED"
    COUNTRIES_OR_REGIONS_NOT_ELIGIBLE = "COUNTRIES_OR_REGIONS_NOT_ELIGIBLE"
    SAPIN_LAW_AGENT_UNKNOWN = "SAPIN_LAW_AGENT_UNKNOWN"
    SAPIN_LAW_FRENCH_BIZ = "SAPIN_LAW_FRENCH_BIZ"
    SAPIN_LAW_FRENCH_BIZ_UNKNOWN = "SAPIN_LAW_FRENCH_BIZ_UNKNOWN"
    BUDGET_ORDER_EXHAUSTED = "BUDGET_ORDER_EXHAUSTED"
    BUDGET_ORDER_SCHEDULE_PENDING = "BUDGET_ORDER_SCHEDULE_PENDING"
    BUDGET_ORDER_SCHEDULE_EXPIRED = "BUDGET_ORDER_SCHEDULE_EXPIRED"
    BUDGET_ORDER_CANCELED = "BUDGET_ORDER_CANCELED"
    BUDGET_ORDER_OR_INVOICE_DETAIL_MISSING = "BUDGET_ORDER_OR_INVOICE_DETAIL_MISSING"
    LIFETIME_BUDGET_EXHAUSTED = "LIFETIME_BUDGET_EXHAUSTED"
    MONTHLY_BUDGET_EXHAUSTED = "MONTHLY_BUDGET_EXHAUSTED"
    LINE_OF_CREDIT_EXHAUSTED = "LINE_OF_CREDIT_EXHAUSTED"
    ORG_PAYMENT_TYPE_DECLINED = "ORG_PAYMENT_TYPE_DECLINED"
    TAX_VERIFICATION_PENDING = "TAX_VERIFICATION_PENDING"
    AD_ACCOUNT_PAYMENT_ISSUES = "AD_ACCOUNT_PAYMENT_ISSUES"
    ORG_NO_PAYMENT_METHOD_ON_FILE = "ORG_NO_PAYMENT_METHOD_ON_FILE"
    ORG_CHARGE_BACK_DISPUTED = "ORG_CHARGE_BACK_DISPUTED"
    ORG_PAYMENT_METHOD_CHANGED = "ORG_PAYMENT_METHOD_CHANGED"
    ORG_SUSPENDED_FRAUD = "ORG_SUSPENDED_FRAUD"
    ORG_SUSPENDED_POLICY_VIOLATION = "ORG_SUSPENDED_POLICY_VIOLATION"
    CONTENT_PROVIDER_UNLINKED = "CONTENT_PROVIDER_UNLINKED"
    AD_ACCOUNT_BRAND_DELEGATION_ISSUES = "AD_ACCOUNT_BRAND_DELEGATION_ISSUES"
    AD_GROUPS_MISSING = "AD_GROUPS_MISSING"
    AD_GROUPS_NOT_RUNNING = "AD_GROUPS_NOT_RUNNING"
    AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_MISSING = "AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_MISSING"
    AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_RUNNING = (
        "AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_RUNNING"
    )


class CampaignSystemLimitedStatusReason(StrEnum):
    """Non-blocking reasons that reduce delivery (read-only)."""

    FEATURE_NOT_AVAILABLE_IN_COUNTRY_OR_REGION = "FEATURE_NOT_AVAILABLE_IN_COUNTRY_OR_REGION"
    ACCOUNT_DOC_APPROVAL_EXPIRED = "ACCOUNT_DOC_APPROVAL_EXPIRED"
    ACCOUNT_DOC_APPROVAL_INFECTED = "ACCOUNT_DOC_APPROVAL_INFECTED"
    ACCOUNT_DOC_APPROVAL_NOT_SUBMITTED = "ACCOUNT_DOC_APPROVAL_NOT_SUBMITTED"
    ACCOUNT_DOC_APPROVAL_PENDING = "ACCOUNT_DOC_APPROVAL_PENDING"
    ACCOUNT_DOC_APPROVAL_REJECTED = "ACCOUNT_DOC_APPROVAL_REJECTED"
    APP_CONTENT_REJECTED = "APP_CONTENT_REJECTED"
    APP_CONTENT_REVIEW_PENDING = "APP_CONTENT_REVIEW_PENDING"
    APP_DOC_APPROVAL_EXPIRED = "APP_DOC_APPROVAL_EXPIRED"
    APP_DOC_APPROVAL_INFECTED = "APP_DOC_APPROVAL_INFECTED"
    APP_DOC_APPROVAL_NOT_SUBMITTED = "APP_DOC_APPROVAL_NOT_SUBMITTED"
    APP_DOC_APPROVAL_PENDING = "APP_DOC_APPROVAL_PENDING"
    APP_DOC_APPROVAL_REJECTED = "APP_DOC_APPROVAL_REJECTED"
    APP_NOT_ELIGIBLE = "APP_NOT_ELIGIBLE"
    APP_NOT_ELIGIBLE_SEARCHADS = "APP_NOT_ELIGIBLE_SEARCHADS"
    APP_NOT_ELIGIBLE_SUPPLY_SOURCE = "APP_NOT_ELIGIBLE_SUPPLY_SOURCE"
    APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT = "APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT"
    APP_LANGUAGE_INCOMPATIBLE = "APP_LANGUAGE_INCOMPATIBLE"
    APP_NOT_PUBLISHED_YET = "APP_NOT_PUBLISHED_YET"
    SAPIN_LAW_AGENT_UNKNOWN = "SAPIN_LAW_AGENT_UNKNOWN"
    SAPIN_LAW_FRENCH_BIZ = "SAPIN_LAW_FRENCH_BIZ"
    SAPIN_LAW_FRENCH_BIZ_UNKNOWN = "SAPIN_LAW_FRENCH_BIZ_UNKNOWN"
    BRAND_POLICY_ISSUES = "BRAND_POLICY_ISSUES"
    AD_GROUPS_LIMITED = "AD_GROUPS_LIMITED"


class SupplySource(StrEnum):
    """Documented values for the ``supplySource`` targeting dimension."""

    APPSTORE = "APPSTORE"
    MAPS = "MAPS"


class SupplyPlacement(StrEnum):
    """Documented values for the ``supplyPlacement`` targeting dimension."""

    APPSTORE_SEARCH_RESULTS = "APPSTORE_SEARCH_RESULTS"
    APPSTORE_SEARCH_TAB = "APPSTORE_SEARCH_TAB"
    APPSTORE_TODAY_TAB = "APPSTORE_TODAY_TAB"
    APPSTORE_PRODUCT_PAGES = "APPSTORE_PRODUCT_PAGES"
    MAPS_SEARCH_RESULTS = "MAPS_SEARCH_RESULTS"
    MAPS_SEARCH_HOME = "MAPS_SEARCH_HOME"


class RegulationType(StrEnum):
    """Regulatory disclosure types."""

    CAC = "CAC"
    CAMPAIGN_SAPIN_LAW = "CAMPAIGN_SAPIN_LAW"
    ORG_SAPIN_LAW = "ORG_SAPIN_LAW"


class RegulationResponseValue(StrEnum):
    """Responses to regulatory disclosures."""

    AGENT = "AGENT"
    NOT_AGENT = "NOT_AGENT"
    FRENCH_BUSINESS = "FRENCH_BUSINESS"
    NOT_FRENCH_BUSINESS = "NOT_FRENCH_BUSINESS"
    TRUE = "TRUE"
    FALSE = "FALSE"
    NOT_ANSWERED = "NOT_ANSWERED"


class CampaignTargeting(V1Model):
    """Campaign-level targeting: supply source, placements, markets.

    Attributes:
        supply_source: Where ads serve (``APPSTORE``/``MAPS``).
        supply_placement: Specific placements within the supply source.
        country_or_region: ISO 3166-1 alpha-2 country/region codes.
    """

    supply_source: TargetingData | None = Field(default=None, alias="supplySource")
    supply_placement: TargetingData | None = Field(default=None, alias="supplyPlacement")
    country_or_region: TargetingData | None = Field(default=None, alias="countryOrRegion")


class DailyBudget(V1Model):
    """A campaign's daily spend cap.

    Attributes:
        value: The cap amount; its currency must match the ad account's.
    """

    value: Money | None = None


class RegulationResponse(V1Model):
    """A regulatory consent acknowledgment on a campaign.

    Attributes:
        regulation_type: The regulation being responded to.
        response_value: The advertiser's response.
    """

    regulation_type: RegulationType | None = Field(default=None, alias="regulationType")
    response_value: RegulationResponseValue | None = Field(default=None, alias="responseValue")


class LegacyAppLimitedStatusReasonDetails(V1Model):
    """Per-market limited-status reasons for legacy app campaigns.

    Attributes:
        country_or_region_limited_status_reasons: Map of ISO 3166-1
            alpha-2 codes to human-readable reason strings; an empty
            array means no active limiting reasons for that market.
    """

    country_or_region_limited_status_reasons: dict[str, list[str]] | None = Field(
        default=None, alias="countryOrRegionLimitedStatusReasons"
    )


class Campaign(V1Model):
    """A campaign as returned by the API (read model).

    Every field is schema-optional; the server populates what applies.

    Attributes:
        id: System-assigned unique identifier.
        ad_account_id: The owning ad account's ID.
        name: The campaign name (max 200 characters).
        billing_event: The charged event; immutable after create.
        payment_model: The account payment model (e.g. ``LOC``,
            ``PAYG``); modeled as a string because Apple documents no
            closed enum for it.
        start_time: When the campaign starts serving (UTC).
        end_time: When the campaign stops serving; absent runs forever.
        promoted_object_type: What the campaign promotes; immutable.
        promoted_object_id: The promoted app adamId or brand ID.
        status: Advertiser intent (``ENABLED``/``PAUSED``).
        system_status: System-computed serving state.
        system_status_reasons: Blocking reasons when NOT_RUNNING.
        system_status_limiting_reasons: Delivery-reducing reasons.
        display_status: Rolled-up user-facing status label.
        daily_budget: The daily spend cap.
        shared_budgets: Budget-order assignments.
        targeting: Campaign-level targeting (include-only).
        bid_strategy: The auction bid strategy.
        invoice_detail: Billing contacts (LOC accounts).
        regulation_responses: Regulatory consent acknowledgments.
        creation_time: When the campaign was created.
        modification_time: When the campaign was last modified.
        deleted: Whether the campaign is soft-deleted.
    """

    id: int | None = None
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    name: str | None = None
    billing_event: BillingEvent | None = Field(default=None, alias="billingEvent")
    payment_model: str | None = Field(default=None, alias="paymentModel")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    promoted_object_type: PromotedObjectType | None = Field(
        default=None, alias="promotedObjectType"
    )
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    status: CampaignStatus | None = None
    system_status: CampaignSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[CampaignSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    system_status_limiting_reasons: list[CampaignSystemLimitedStatusReason] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    display_status: CampaignDisplayStatus | None = Field(default=None, alias="displayStatus")
    daily_budget: DailyBudget | None = Field(default=None, alias="dailyBudget")
    shared_budgets: list[SharedBudgetAssignment] | None = Field(default=None, alias="sharedBudgets")
    targeting: CampaignTargeting | None = None
    bid_strategy: BidStrategy | None = Field(default=None, alias="bidStrategy")
    invoice_detail: InvoiceDetail | None = Field(default=None, alias="invoiceDetail")
    regulation_responses: list[RegulationResponse] | None = Field(
        default=None, alias="regulationResponses"
    )
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    deleted: bool | None = None


def _serialize_campaign_time(value: datetime | None) -> str | None:
    """Serialize a campaign start/end time to Apple's wire format.

    Apple documents ``yyyy-MM-dd'T'HH:mm:ss.SSS`` in UTC with
    milliseconds and no timezone suffix (e.g. ``2026-06-07T00:00:00.000``).

    Args:
        value: The datetime to serialize, or None.

    Returns:
        The formatted timestamp string, or None.
    """
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


class CampaignCreate(V1Model):
    """Request body for creating a campaign (POST /v1/campaigns).

    The body is sent unwrapped. ``ad_account_id``, ``billing_event``,
    ``promoted_object_type``, and ``promoted_object_id`` are immutable
    after creation.

    Attributes:
        ad_account_id: The owning ad account's ID (required in the body
            despite the context header).
        name: The campaign name (1-200 characters).
        billing_event: The charged event; ``TAPS`` for App Store,
            ``TAPS`` or ``IMPRESSIONS`` for Maps.
        promoted_object_type: What the campaign promotes.
        promoted_object_id: The app adamId or brand resource ID.
        daily_budget: The daily spend cap.
        targeting: Campaign-level targeting (include-only).
        start_time: When to start serving; omitted starts immediately
            on activation.
        end_time: When to stop serving; omitted runs indefinitely.
        shared_budgets: Budget-order assignments.
        bid_strategy: The bid strategy; type and goal must both be
            supplied and match an allowed pairing.
        invoice_detail: Billing contacts; required for LOC accounts.
        regulation_responses: Required in certain markets.
        status: Initial advertiser intent, when a specific one is needed.
    """

    ad_account_id: int = Field(alias="adAccountId")
    name: str
    billing_event: BillingEvent = Field(alias="billingEvent")
    promoted_object_type: PromotedObjectType = Field(alias="promotedObjectType")
    promoted_object_id: str = Field(alias="promotedObjectId")
    daily_budget: DailyBudget = Field(alias="dailyBudget")
    targeting: CampaignTargeting
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    shared_budgets: list[SharedBudgetAssignment] | None = Field(default=None, alias="sharedBudgets")
    bid_strategy: BidStrategy | None = Field(default=None, alias="bidStrategy")
    invoice_detail: InvoiceDetail | None = Field(default=None, alias="invoiceDetail")
    regulation_responses: list[RegulationResponse] | None = Field(
        default=None, alias="regulationResponses"
    )
    status: CampaignStatus | None = None

    @field_serializer("start_time", "end_time")
    def _serialize_times(self, value: datetime | None) -> str | None:
        """Serialize start/end times to Apple's millisecond format.

        Args:
            value: The datetime to serialize, or None.

        Returns:
            The formatted timestamp string, or None.
        """
        return _serialize_campaign_time(value)


class CampaignUpdate(V1Model):
    """Request body for updating a campaign (PUT /v1/campaigns/{id}).

    The body is sent unwrapped. All fields are optional: include only
    the fields to change; omitted fields keep their current values.
    Immutable fields (``billingEvent``, ``promotedObjectType``,
    ``promotedObjectId``, ``adAccountId``) are absent from this schema.

    Attributes:
        name: New campaign name (1-200 characters).
        start_time: New start time.
        end_time: New end time.
        status: ``PAUSED`` to pause, ``ENABLED`` to resume.
        daily_budget: New daily spend cap.
        shared_budgets: Replacement budget-order assignments.
        targeting: New campaign-level targeting.
        bid_strategy: New bid strategy; type and goal must be sent
            together and match an allowed pairing.
        invoice_detail: New billing contacts (LOC accounts).
        regulation_responses: New regulatory responses.
    """

    name: str | None = None
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    status: CampaignStatus | None = None
    daily_budget: DailyBudget | None = Field(default=None, alias="dailyBudget")
    shared_budgets: list[SharedBudgetAssignment] | None = Field(default=None, alias="sharedBudgets")
    targeting: CampaignTargeting | None = None
    bid_strategy: BidStrategy | None = Field(default=None, alias="bidStrategy")
    invoice_detail: InvoiceDetail | None = Field(default=None, alias="invoiceDetail")
    regulation_responses: list[RegulationResponse] | None = Field(
        default=None, alias="regulationResponses"
    )

    @field_serializer("start_time", "end_time")
    def _serialize_times(self, value: datetime | None) -> str | None:
        """Serialize start/end times to Apple's millisecond format.

        Args:
            value: The datetime to serialize, or None.

        Returns:
            The formatted timestamp string, or None.
        """
        return _serialize_campaign_time(value)
