"""Ad Group models for the Apple Search Ads API.

Ad groups are contained within campaigns and define targeting
criteria, bids, and contain keywords and ads.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from asa_api_client.models.base import Money


class AdGroupStatus(StrEnum):
    """The status of an ad group."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class AdGroupServingStatus(StrEnum):
    """The serving status of an ad group."""

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class AdGroupServingStateReason(StrEnum):
    """Reasons why an ad group may not be serving."""

    PAUSED_BY_USER = "PAUSED_BY_USER"
    DELETED_BY_USER = "DELETED_BY_USER"
    CAMPAIGN_NOT_RUNNING = "CAMPAIGN_NOT_RUNNING"
    AD_GROUP_END_DATE_REACHED = "AD_GROUP_END_DATE_REACHED"
    AD_GROUP_START_DATE_IN_FUTURE = "AD_GROUP_START_DATE_IN_FUTURE"
    NO_ELIGIBLE_ADS = "NO_ELIGIBLE_ADS"
    NO_ELIGIBLE_KEYWORDS = "NO_ELIGIBLE_KEYWORDS"
    TARGETING_INVALID = "TARGETING_INVALID"


class AdGroupDisplayStatus(StrEnum):
    """Human-readable display status for ad groups."""

    RUNNING = "RUNNING"
    ON_HOLD = "ON_HOLD"
    PAUSED = "PAUSED"
    DELETED = "DELETED"


class AutomatedKeywordsOptInStatus(StrEnum):
    """Whether Search Match is enabled for the ad group."""

    OPT_IN = "OPT_IN"
    OPT_OUT = "OPT_OUT"


class PricingModel(StrEnum):
    """The pricing model for the ad group."""

    CPC = "CPC"  # Cost per click
    CPM = "CPM"  # Cost per thousand impressions


class AgeRange(BaseModel):
    """Age targeting range.

    Attributes:
        min_age: Minimum age (inclusive).
        max_age: Maximum age (inclusive), or None for no upper limit.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    min_age: int | None = Field(default=None, alias="minAge")
    max_age: int | None = Field(default=None, alias="maxAge")


class Gender(StrEnum):
    """Gender targeting options."""

    MALE = "M"
    FEMALE = "F"


class DeviceClass(StrEnum):
    """Device class targeting options."""

    IPHONE = "IPHONE"
    IPAD = "IPAD"


class DaypartDetail(BaseModel):
    """Day and time targeting for ad delivery.

    Attributes:
        user_time: The hour of day (0-23) in user's local time.
        days_of_week: List of days (0=Sunday through 6=Saturday).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    user_time: int = Field(alias="userTime", ge=0, le=23)
    days_of_week: list[int] = Field(alias="daysOfWeek")


class TargetingDimensionValue(BaseModel):
    """A value in a targeting dimension.

    Attributes:
        included: List of values to include in targeting.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    included: list[Any] | None = None


class TargetingDimensions(BaseModel):
    """Targeting dimensions for an ad group.

    Defines who will see ads in this ad group based on various
    demographic and device criteria.

    Attributes:
        age: Age range targeting.
        gender: Gender targeting.
        device_class: Device type targeting.
        daypart: Day and time targeting.
        admin_area: Geographic admin area targeting.
        locality: Geographic locality targeting.
        app_downloaders: Target or exclude users who have downloaded
            specific apps.
        app_categories: Target by app category interests.

    Example:
        Target iPhone users ages 18-35::

            targeting = TargetingDimensions(
                age=TargetingDimensionValue(
                    included=[AgeRange(min_age=18, max_age=35)]
                ),
                device_class=TargetingDimensionValue(
                    included=[DeviceClass.IPHONE]
                ),
            )
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    age: TargetingDimensionValue | None = None
    gender: TargetingDimensionValue | None = None
    device_class: TargetingDimensionValue | None = Field(default=None, alias="deviceClass")
    daypart: TargetingDimensionValue | None = None
    admin_area: TargetingDimensionValue | None = Field(default=None, alias="adminArea")
    locality: TargetingDimensionValue | None = None
    app_downloaders: TargetingDimensionValue | None = Field(default=None, alias="appDownloaders")
    app_categories: TargetingDimensionValue | None = Field(default=None, alias="appCategories")


class CpaGoal(BaseModel):
    """Cost per acquisition goal.

    Attributes:
        amount: The target CPA amount (can be Money object or string).
        mode: The CPA goal mode.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: Money | str  # API sometimes returns just a string
    mode: str | None = None


class AdGroup(BaseModel):
    """An Apple Search Ads ad group.

    Ad groups belong to campaigns and contain keywords, targeting
    criteria, and ads. Each ad group has its own bid settings and
    targeting dimensions.

    Attributes:
        id: The unique identifier for the ad group.
        campaign_id: The parent campaign ID.
        org_id: The organization ID.
        name: The ad group name.
        default_bid_amount: The default bid for keywords.
        cpa_goal: Cost per acquisition goal.
        automated_keywords_opt_in: Whether Search Match is enabled.
        status: The ad group status.
        serving_status: Whether the ad group is serving.
        serving_state_reasons: Reasons for current serving state.
        display_status: Human-readable status.
        targeting_dimensions: Audience targeting settings.
        modification_time: When the ad group was last modified.
        pricing_model: The bid pricing model (CPC or CPM).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    campaign_id: int = Field(alias="campaignId")
    org_id: int = Field(alias="orgId")
    name: str
    default_bid_amount: Money = Field(alias="defaultBidAmount")
    cpa_goal: CpaGoal | None = Field(default=None, alias="cpaGoal")
    automated_keywords_opt_in: AutomatedKeywordsOptInStatus | str | bool = Field(
        alias="automatedKeywordsOptIn"
    )
    status: AdGroupStatus | str
    serving_status: AdGroupServingStatus | str = Field(alias="servingStatus")
    serving_state_reasons: list[AdGroupServingStateReason | str] | None = Field(
        default=None, alias="servingStateReasons"
    )
    display_status: AdGroupDisplayStatus | str = Field(alias="displayStatus")
    targeting_dimensions: TargetingDimensions | None = Field(
        default=None, alias="targetingDimensions"
    )
    modification_time: datetime = Field(alias="modificationTime")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    pricing_model: PricingModel | str | None = Field(default=None, alias="pricingModel")


class AdGroupCreate(BaseModel):
    """Request model for creating a new ad group.

    Example:
        Create an ad group with targeting::

            ad_group = AdGroupCreate(
                name="US iPhone Users",
                default_bid_amount=Money.usd("1.50"),
                targeting_dimensions=TargetingDimensions(
                    device_class=TargetingDimensionValue(
                        included=[DeviceClass.IPHONE]
                    ),
                ),
            )

            created = client.campaigns(123).ad_groups.create(ad_group)
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    default_bid_amount: Money = Field(alias="defaultBidAmount")
    cpa_goal: CpaGoal | None = Field(default=None, alias="cpaGoal")
    automated_keywords_opt_in: bool = Field(
        default=True,
        alias="automatedKeywordsOptIn",
    )
    status: AdGroupStatus = AdGroupStatus.ENABLED
    targeting_dimensions: TargetingDimensions | None = Field(
        default=None, alias="targetingDimensions"
    )
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    pricing_model: PricingModel = Field(default=PricingModel.CPC, alias="pricingModel")

    @field_serializer("start_time", "end_time")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO 8601 format for API."""
        if value is None:
            return None
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class AdGroupUpdate(BaseModel):
    """Request model for updating an existing ad group.

    Only include the fields you want to update.

    Example:
        Update the default bid::

            update = AdGroupUpdate(
                default_bid_amount=Money.usd("2.00"),
            )

            updated = client.campaigns(123).ad_groups.update(
                ad_group_id=456,
                data=update,
            )
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    default_bid_amount: Money | None = Field(default=None, alias="defaultBidAmount")
    cpa_goal: CpaGoal | None = Field(default=None, alias="cpaGoal")
    automated_keywords_opt_in: AutomatedKeywordsOptInStatus | None = Field(
        default=None, alias="automatedKeywordsOptIn"
    )
    status: AdGroupStatus | None = None
    targeting_dimensions: TargetingDimensions | None = Field(
        default=None, alias="targetingDimensions"
    )
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
