"""Campaign models for the Apple Search Ads API.

This module contains models for creating, reading, and updating
advertising campaigns on the Apple Search Ads platform.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from asa_api_client.models.base import Money


class AdChannelType(StrEnum):
    """The ad channel type for a campaign.

    Attributes:
        SEARCH: Search-based ads (Search Results, Search Tab).
        DISPLAY: Display-based ads (Today Tab, Product Pages).
    """

    SEARCH = "SEARCH"
    DISPLAY = "DISPLAY"


class BillingEvent(StrEnum):
    """The billing event type for a campaign.

    Attributes:
        TAPS: Cost-per-tap (CPT) billing - pay when users tap your ad.
        IMPRESSIONS: Cost-per-impression (CPM) billing - pay per 1000 impressions.
    """

    TAPS = "TAPS"
    IMPRESSIONS = "IMPRESSIONS"


class CampaignStatus(StrEnum):
    """The status of a campaign.

    Attributes:
        ENABLED: The campaign is active and can serve ads.
        PAUSED: The campaign is paused and will not serve ads.
    """

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class CampaignServingStatus(StrEnum):
    """The serving status of a campaign."""

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class CampaignServingStateReason(StrEnum):
    """Reasons why a campaign may not be serving."""

    AD_GROUP_MISSING = "AD_GROUP_MISSING"
    APP_LANGUAGE_INCOMPATIBLE = "APP_LANGUAGE_INCOMPATIBLE"
    APP_NOT_CATEGORIZED = "APP_NOT_CATEGORIZED"
    APP_NOT_ELIGIBLE = "APP_NOT_ELIGIBLE"
    APP_NOT_ELIGIBLE_SEARCHADS = "APP_NOT_ELIGIBLE_SEARCHADS"
    APP_NOT_ELIGIBLE_SUPPLY_SOURCE = "APP_NOT_ELIGIBLE_SUPPLY_SOURCE"
    APP_NOT_LINKED_TO_CAMPAIGN_GROUP = "APP_NOT_LINKED_TO_CAMPAIGN_GROUP"
    APP_NOT_PUBLISHED_YET = "APP_NOT_PUBLISHED_YET"
    APP_SENSITIVE_CONTENT = "APP_SENSITIVE_CONTENT"
    BO_END_DATE_REACHED = "BO_END_DATE_REACHED"
    BO_EXHAUSTED = "BO_EXHAUSTED"
    BO_START_DATE_IN_FUTURE = "BO_START_DATE_IN_FUTURE"
    CAMPAIGN_END_DATE_REACHED = "CAMPAIGN_END_DATE_REACHED"
    CAMPAIGN_START_DATE_IN_FUTURE = "CAMPAIGN_START_DATE_IN_FUTURE"
    CONTENT_PROVIDER_UNLINKED = "CONTENT_PROVIDER_UNLINKED"
    CREDIT_CARD_DECLINED = "CREDIT_CARD_DECLINED"
    DAILY_CAP_EXHAUSTED = "DAILY_CAP_EXHAUSTED"
    DELETED_BY_USER = "DELETED_BY_USER"
    FEATURE_NO_LONGER_AVAILABLE = "FEATURE_NO_LONGER_AVAILABLE"
    FEATURE_NOT_YET_AVAILABLE = "FEATURE_NOT_YET_AVAILABLE"
    INELIGIBLE_BUSINESS_LOCATION = "INELIGIBLE_BUSINESS_LOCATION"
    LOC_EXHAUSTED = "LOC_EXHAUSTED"
    MISSING_BO_OR_INVOICING_FIELDS = "MISSING_BO_OR_INVOICING_FIELDS"
    NO_AVAILABLE_AD_GROUPS = "NO_AVAILABLE_AD_GROUPS"
    NO_ELIGIBLE_COUNTRIES = "NO_ELIGIBLE_COUNTRIES"
    NO_PAYMENT_METHOD_ON_FILE = "NO_PAYMENT_METHOD_ON_FILE"
    ORG_CHARGE_BACK_DISPUTED = "ORG_CHARGE_BACK_DISPUTED"
    ORG_PAYMENT_TYPE_CHANGED = "ORG_PAYMENT_TYPE_CHANGED"
    ORG_SUSPENDED_FRAUD = "ORG_SUSPENDED_FRAUD"
    ORG_SUSPENDED_POLICY_VIOLATION = "ORG_SUSPENDED_POLICY_VIOLATION"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    SAPIN_LAW_AGENT_UNKNOWN = "SAPIN_LAW_AGENT_UNKNOWN"
    SAPIN_LAW_FRENCH_BIZ = "SAPIN_LAW_FRENCH_BIZ"
    SAPIN_LAW_FRENCH_BIZ_UNKNOWN = "SAPIN_LAW_FRENCH_BIZ_UNKNOWN"
    TAX_VERIFICATION_PENDING = "TAX_VERIFICATION_PENDING"
    TOTAL_BUDGET_EXHAUSTED = "TOTAL_BUDGET_EXHAUSTED"
    USER_REQUESTED_ACCOUNT_SUSPENSION = "USER_REQUESTED_ACCOUNT_SUSPENSION"


class CampaignCountryOrRegionServingStateReason(StrEnum):
    """Reasons for country/region-specific serving state."""

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
    APP_NOT_PUBLISHED_YET = "APP_NOT_PUBLISHED_YET"
    FEATURE_NOT_AVAILABLE_IN_COUNTRY_OR_REGION = "FEATURE_NOT_AVAILABLE_IN_COUNTRY_OR_REGION"
    SAPIN_LAW_AGENT_UNKNOWN = "SAPIN_LAW_AGENT_UNKNOWN"
    SAPIN_LAW_FRENCH_BIZ = "SAPIN_LAW_FRENCH_BIZ"
    SAPIN_LAW_FRENCH_BIZ_UNKNOWN = "SAPIN_LAW_FRENCH_BIZ_UNKNOWN"


class CampaignDisplayStatus(StrEnum):
    """Human-readable display status for campaigns."""

    RUNNING = "RUNNING"
    ON_HOLD = "ON_HOLD"
    PAUSED = "PAUSED"
    DELETED = "DELETED"


class CampaignSupplySource(StrEnum):
    """The supply source for the campaign.

    Determines where ads will be shown.
    """

    APPSTORE_SEARCH_RESULTS = "APPSTORE_SEARCH_RESULTS"
    APPSTORE_SEARCH_TAB = "APPSTORE_SEARCH_TAB"
    APPSTORE_TODAY_TAB = "APPSTORE_TODAY_TAB"
    APPSTORE_PRODUCT_PAGES = "APPSTORE_PRODUCT_PAGES"
    APPSTORE_PRODUCT_PAGES_BROWSE = "APPSTORE_PRODUCT_PAGES_BROWSE"


class BiddingStrategy(StrEnum):
    """The bidding strategy for a campaign.

    Attributes:
        MANUAL_CPT: Manual cost-per-tap bidding.
        MAX_CONVERSIONS: AI-powered automated bidding that optimizes
            bids per search query in real time toward a target CPA goal.
    """

    MANUAL_CPT = "MANUAL_CPT"
    MAX_CONVERSIONS = "MAX_CONVERSIONS"


# Keep as alias for backwards compatibility
BidStrategyType = BiddingStrategy


class Campaign(BaseModel):
    """An Apple Search Ads campaign.

    Attributes:
        id: The unique identifier for the campaign.
        org_id: The organization ID that owns this campaign.
        name: The campaign name.
        budget_amount: The total campaign budget.
        daily_budget_amount: The daily budget limit.
        adam_id: The App Store app ID being advertised.
        countries_or_regions: List of targeted country/region codes.
        status: The campaign status (ENABLED/PAUSED).
        serving_status: Whether the campaign is currently serving.
        serving_state_reasons: Reasons for the current serving state.
        modification_time: When the campaign was last modified.
        display_status: Human-readable status for display.
        supply_sources: Where ads will be shown.
        ad_channel_type: The ad channel type (SEARCH/DISPLAY).
        billing_event: The billing event type (TAPS/IMPRESSIONS).
        bidding_strategy: The bidding strategy (MANUAL_CPT/MAX_CONVERSIONS).
        target_cpa: Target cost per acquisition for MAX_CONVERSIONS.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    org_id: int = Field(alias="orgId")
    name: str
    budget_amount: Money | None = Field(default=None, alias="budgetAmount")
    daily_budget_amount: Money | None = Field(default=None, alias="dailyBudgetAmount")
    adam_id: int = Field(alias="adamId")
    countries_or_regions: list[str] = Field(alias="countriesOrRegions")
    status: CampaignStatus | str
    serving_status: CampaignServingStatus | str = Field(alias="servingStatus")
    serving_state_reasons: list[CampaignServingStateReason | str] | None = Field(
        default=None, alias="servingStateReasons"
    )
    modification_time: datetime = Field(alias="modificationTime")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    display_status: CampaignDisplayStatus | str = Field(alias="displayStatus")
    supply_sources: list[CampaignSupplySource | str] = Field(alias="supplySources")
    ad_channel_type: AdChannelType | str | None = Field(default=None, alias="adChannelType")
    billing_event: BillingEvent | str | None = Field(default=None, alias="billingEvent")
    country_or_region_serving_state_reasons: dict[str, list[str]] | None = Field(
        default=None, alias="countryOrRegionServingStateReasons"
    )
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    loc_invoice_details: dict[str, Any] | None = Field(default=None, alias="locInvoiceDetails")
    budget_orders: list[int] | None = Field(default=None, alias="budgetOrders")
    payment_model: str | None = Field(default=None, alias="paymentModel")
    bidding_strategy: BiddingStrategy | str | None = Field(
        default=None, alias="biddingStrategy"
    )
    target_cpa: Money | None = Field(default=None, alias="targetCpa")
    deleted: bool = False


class CampaignCreate(BaseModel):
    """Request model for creating a new campaign.

    Example:
        Create a search results campaign::

            campaign = CampaignCreate(
                name="My App Campaign",
                budget_amount=Money.usd(10000),
                daily_budget_amount=Money.usd(100),
                adam_id=123456789,
                countries_or_regions=["US", "CA", "GB"],
                supply_sources=[CampaignSupplySource.APPSTORE_SEARCH_RESULTS],
            )

            created = client.campaigns.create(campaign)
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    budget_amount: Money | None = Field(default=None, alias="budgetAmount")
    daily_budget_amount: Money | None = Field(default=None, alias="dailyBudgetAmount")
    adam_id: int = Field(alias="adamId")
    countries_or_regions: list[str] = Field(alias="countriesOrRegions")
    status: CampaignStatus = CampaignStatus.ENABLED
    ad_channel_type: AdChannelType = Field(default=AdChannelType.SEARCH, alias="adChannelType")
    billing_event: BillingEvent = Field(default=BillingEvent.TAPS, alias="billingEvent")
    supply_sources: list[CampaignSupplySource] = Field(alias="supplySources")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    loc_invoice_details: dict[str, Any] | None = Field(default=None, alias="locInvoiceDetails")
    budget_orders: list[int] | None = Field(default=None, alias="budgetOrders")
    payment_model: str | None = Field(default=None, alias="paymentModel")
    bidding_strategy: BiddingStrategy | None = Field(default=None, alias="biddingStrategy")
    target_cpa: Money | None = Field(default=None, alias="targetCpa")


class CampaignUpdate(BaseModel):
    """Request model for updating an existing campaign.

    Only include the fields you want to update. Fields set to None
    will not be modified.

    Example:
        Update campaign budget::

            update = CampaignUpdate(
                daily_budget_amount=Money.usd(200),
            )

            updated = client.campaigns.update(campaign_id=123, data=update)
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    budget_amount: Money | None = Field(default=None, alias="budgetAmount")
    daily_budget_amount: Money | None = Field(default=None, alias="dailyBudgetAmount")
    status: CampaignStatus | None = None
    countries_or_regions: list[str] | None = Field(default=None, alias="countriesOrRegions")
    bidding_strategy: BiddingStrategy | None = Field(default=None, alias="biddingStrategy")
    target_cpa: Money | None = Field(default=None, alias="targetCpa")
    loc_invoice_details: dict[str, Any] | None = Field(default=None, alias="locInvoiceDetails")
