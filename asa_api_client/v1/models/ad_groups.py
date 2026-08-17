"""Models for Apple Ads Platform API v1 ad groups.

Ad groups are the primary unit governing targeting, bid strategy,
pricing model, and scheduling within a campaign. This module contains
the ad group resource models, their create/update payloads, and the
enums documented for the ``/v1/adgroups`` endpoints.

The deprecated ``cpaCap`` field is intentionally not modeled; use
``bidStrategy`` with ``MAX_CONVERSIONS`` instead.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import V1Model
from asa_api_client.v1.models.shared import (
    BidStrategy,
    TargetingData,
)
from asa_api_client.v1.models.shared import (
    BidStrategyGoal as BidStrategyGoal,
)
from asa_api_client.v1.models.shared import (
    BidStrategyType as BidStrategyType,
)


class PricingModel(StrEnum):
    """How the ad group is priced.

    Must match the parent campaign's ``billingEvent`` (``CPT`` pairs
    with ``TAPS``, ``CPM`` with ``IMPRESSIONS``). Immutable after
    creation.
    """

    CPA = "CPA"
    CPM = "CPM"
    CPT = "CPT"


class AdGroupStatus(StrEnum):
    """Advertiser-managed serving status of an ad group."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class AdGroupSystemStatus(StrEnum):
    """System-derived serving status of an ad group.

    When ``NOT_RUNNING``, inspect ``systemStatusReasons`` for the
    specific cause.
    """

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class AdGroupDisplayStatus(StrEnum):
    """Rolled-up delivery label combining status and system status."""

    CAMPAIGN_ON_HOLD = "CAMPAIGN_ON_HOLD"
    DELETED = "DELETED"
    LIMITED = "LIMITED"
    ON_HOLD = "ON_HOLD"
    PAUSED = "PAUSED"
    PROCESSING = "PROCESSING"
    RUNNING = "RUNNING"


class AdGroupSystemStatusReason(StrEnum):
    """Reasons contributing to an ad group's system status."""

    PROCESSING = "PROCESSING"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    DELETED_BY_USER = "DELETED_BY_USER"
    SCHEDULE_PENDING = "SCHEDULE_PENDING"
    SCHEDULE_EXPIRED = "SCHEDULE_EXPIRED"
    TARGETED_DEVICE_CLASS_NOT_SUPPORTED_SUPPLY_PLACEMENT = (
        "TARGETED_DEVICE_CLASS_NOT_SUPPORTED_SUPPLY_PLACEMENT"
    )
    PENDING_AUDIENCE_VERIFICATION = "PENDING_AUDIENCE_VERIFICATION"
    AUDIENCE_BELOW_THRESHOLD = "AUDIENCE_BELOW_THRESHOLD"
    CAMPAIGN_NOT_RUNNING = "CAMPAIGN_NOT_RUNNING"
    ADS_NOT_RUNNING = "ADS_NOT_RUNNING"
    AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_ALLOWED_IN_MANUAL_CAMPAIGNS = (
        "AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_ALLOWED_IN_MANUAL_CAMPAIGNS"
    )
    KEYWORDS_MISSING = "KEYWORDS_MISSING"


class AdGroupSystemLimitedStatusReason(StrEnum):
    """Reasons limiting delivery below its maximum potential."""

    LOCATION_POLICY_ISSUES = "LOCATION_POLICY_ISSUES"
    LOCATION_GROUP_ISSUES = "LOCATION_GROUP_ISSUES"
    ADS_LIMITED = "ADS_LIMITED"


class AdGroupTargeting(V1Model):
    """Targeting dimensions for an ad group.

    Combining dimensions uses AND logic. On update, only the included
    dimensions change; omitted dimensions remain unchanged.

    Attributes:
        country: Country IDs from the Geo Search API. Include only.
        admin_area: State/province IDs from the Geo API. Include only.
        locality: City IDs from the Geo API. Include only.
        postal_code: Postal code IDs from the Geo API. Include only.
        radius: ``CLOSE``, ``MEDIUM``, or ``FAR``. Include only.
        device_class: ``IPHONE`` and/or ``IPAD``. Include only.
        min_age: Lower age bound (18-64) as a string. Include only.
        max_age: Upper age bound (18-64) as a string; omit for 65+.
        gender: ``M`` and/or ``F``. Include only.
        app_category: Category IDs; ``100`` means the promoted app's
            own category. Include and exclude supported.
        app_downloader: Adam IDs of downloaded apps. Include and
            exclude supported.
        daypart: Hour-slot integers 0-167 as strings (7-day week grid
            starting Sunday). Include only.
        location_group: Location group IDs. Include only.
    """

    country: TargetingData | None = None
    admin_area: TargetingData | None = Field(default=None, alias="adminArea")
    locality: TargetingData | None = None
    postal_code: TargetingData | None = Field(default=None, alias="postalCode")
    radius: TargetingData | None = None
    device_class: TargetingData | None = Field(default=None, alias="deviceClass")
    min_age: TargetingData | None = Field(default=None, alias="minAge")
    max_age: TargetingData | None = Field(default=None, alias="maxAge")
    gender: TargetingData | None = None
    app_category: TargetingData | None = Field(default=None, alias="appCategory")
    app_downloader: TargetingData | None = Field(default=None, alias="appDownloader")
    daypart: TargetingData | None = None
    location_group: TargetingData | None = Field(default=None, alias="locationGroup")


class AdGroup(V1Model):
    """An ad group as returned by the API.

    All fields are schema-optional in responses.

    Attributes:
        id: Unique identifier. Read-only.
        name: Advertiser-given name.
        ad_account_id: The owning ad account. Read-only.
        campaign_id: The parent campaign. Immutable after creation.
        start_time: Scheduling start (ISO 8601, no timezone suffix).
        end_time: Scheduling end; omitted inherits the campaign end.
        pricing_model: How the ad group is priced. Immutable.
        automated_keywords_opt_in: Search Match opt-in.
        automated_keywords_required: Immutable after creation.
        status: Advertiser-managed status (ENABLED/PAUSED).
        system_status: System-derived status. Read-only.
        system_status_reasons: Reasons behind system_status. Read-only.
        system_status_limiting_reasons: Reasons limiting delivery
            below maximum potential. Read-only.
        display_status: Rolled-up delivery label. Read-only.
        bid_strategy: Ad-group bid strategy; when omitted, the
            campaign-level strategy applies.
        targeting: Targeting dimensions; can be null in responses.
        deleted: Whether the ad group is soft-deleted. Read-only.
        creation_time: When the ad group was created. Read-only.
        modification_time: When it was last modified. Read-only.
    """

    id: int | None = None
    name: str | None = None
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    campaign_id: int | None = Field(default=None, alias="campaignId")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    pricing_model: PricingModel | None = Field(default=None, alias="pricingModel")
    automated_keywords_opt_in: bool | None = Field(default=None, alias="automatedKeywordsOptIn")
    automated_keywords_required: bool | None = Field(
        default=None, alias="automatedKeywordsRequired"
    )
    status: AdGroupStatus | None = None
    system_status: AdGroupSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[AdGroupSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    system_status_limiting_reasons: list[AdGroupSystemLimitedStatusReason] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    display_status: AdGroupDisplayStatus | None = Field(default=None, alias="displayStatus")
    bid_strategy: BidStrategy | None = Field(default=None, alias="bidStrategy")
    targeting: AdGroupTargeting | None = None
    deleted: bool | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class AdGroupCreate(V1Model):
    """Request body for ``POST /v1/adgroups``.

    Attributes:
        name: The ad group name. Required.
        campaign_id: The parent campaign. Required; immutable.
        pricing_model: Pricing model matching the campaign's billing
            event. Required; immutable.
        start_time: Scheduling start (ISO 8601).
        end_time: Scheduling end; omit to inherit the campaign end.
        automated_keywords_opt_in: Search Match auto opt-in.
        status: Initial status; the API applies no default if omitted.
        automated_keywords_required: Settable only at creation.
        bid_strategy: Omit to inherit the campaign-level bid strategy.
        targeting: Targeting dimensions for the new ad group.
    """

    name: str
    campaign_id: int = Field(alias="campaignId")
    pricing_model: PricingModel = Field(alias="pricingModel")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    automated_keywords_opt_in: bool | None = Field(default=None, alias="automatedKeywordsOptIn")
    status: AdGroupStatus | None = None
    automated_keywords_required: bool | None = Field(
        default=None, alias="automatedKeywordsRequired"
    )
    bid_strategy: BidStrategy | None = Field(default=None, alias="bidStrategy")
    targeting: AdGroupTargeting | None = None


class AdGroupUpdate(V1Model):
    """Request body for ``PUT /v1/adgroups/{id}``.

    Include only the fields to change. ``campaignId``,
    ``pricingModel``, and ``automatedKeywordsRequired`` are immutable
    and are not modeled here.

    Attributes:
        name: New ad group name.
        start_time: New scheduling start.
        end_time: New scheduling end; omit to inherit the campaign end.
        automated_keywords_opt_in: Search Match opt-in.
        status: ``PAUSED`` to pause, ``ENABLED`` to resume.
        bid_strategy: New bid strategy; ``bidStrategyType`` and
            ``bidStrategyGoal`` must be sent together.
        targeting: Partial update — only included dimensions change.
    """

    name: str | None = None
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    automated_keywords_opt_in: bool | None = Field(default=None, alias="automatedKeywordsOptIn")
    status: AdGroupStatus | None = None
    bid_strategy: BidStrategy | None = Field(default=None, alias="bidStrategy")
    targeting: AdGroupTargeting | None = None
