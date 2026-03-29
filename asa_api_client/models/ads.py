"""Ad models for the Apple Search Ads API.

Ads are contained within ad groups and represent the actual
advertisements shown to users, including product page ad variations.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AdStatus(StrEnum):
    """The status of an ad."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class AdServingStatus(StrEnum):
    """The serving status of an ad."""

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class AdServingStateReason(StrEnum):
    """Reasons why an ad may not be serving."""

    AD_APPROVAL_PENDING = "AD_APPROVAL_PENDING"
    AD_APPROVAL_REJECTED = "AD_APPROVAL_REJECTED"
    AD_PROCESSING_IN_PROGRESS = "AD_PROCESSING_IN_PROGRESS"
    CREATIVE_SET_INVALID = "CREATIVE_SET_INVALID"
    CREATIVE_SET_UNSUPPORTED = "CREATIVE_SET_UNSUPPORTED"
    DELETED_BY_USER = "DELETED_BY_USER"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    PRODUCT_PAGE_DELETED = "PRODUCT_PAGE_DELETED"
    PRODUCT_PAGE_HIDDEN = "PRODUCT_PAGE_HIDDEN"
    PRODUCT_PAGE_INCOMPATIBLE = "PRODUCT_PAGE_INCOMPATIBLE"
    PRODUCT_PAGE_INSUFFICIENT_ASSETS = "PRODUCT_PAGE_INSUFFICIENT_ASSETS"


class AdDisplayStatus(StrEnum):
    """Human-readable display status for ads (used in reporting)."""

    ACTIVE = "ACTIVE"
    INVALID = "INVALID"
    ON_HOLD = "ON_HOLD"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"


class CreativeType(StrEnum):
    """The creative type of an ad."""

    CREATIVE_SET = "CREATIVE_SET"
    CUSTOM_PRODUCT_PAGE = "CUSTOM_PRODUCT_PAGE"
    DEFAULT_PRODUCT_PAGE = "DEFAULT_PRODUCT_PAGE"


class Ad(BaseModel):
    """An Apple Search Ads ad.

    Ads represent actual advertisements within ad groups,
    including product page ad variations.

    Attributes:
        id: The unique identifier for the ad.
        org_id: The organization ID.
        campaign_id: The parent campaign ID.
        ad_group_id: The parent ad group ID.
        name: The ad name.
        creative_type: The type of creative used.
        status: The ad status (ENABLED/PAUSED).
        serving_status: Whether the ad is serving.
        serving_state_reasons: Reasons for current serving state.
        modification_time: When the ad was last modified.
        creation_time: When the ad was created.
        creative_id: The ID of the associated creative.
        deleted: Whether the ad has been deleted.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    org_id: int = Field(alias="orgId")
    campaign_id: int = Field(alias="campaignId")
    ad_group_id: int = Field(alias="adGroupId")
    name: str
    creative_type: CreativeType | str = Field(alias="creativeType")
    status: AdStatus | str
    serving_status: AdServingStatus | str = Field(alias="servingStatus")
    serving_state_reasons: list[AdServingStateReason | str] | None = Field(
        default=None, alias="servingStateReasons"
    )
    modification_time: datetime = Field(alias="modificationTime")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    creative_id: int | None = Field(default=None, alias="creativeId")
    deleted: bool = False


class AdCreate(BaseModel):
    """Request model for creating a new ad.

    Example:
        Create a product page ad::

            ad = AdCreate(
                name="Holiday Product Page",
                creative_type=CreativeType.CUSTOM_PRODUCT_PAGE,
                product_page_id="abc123",
            )
            created = client.campaigns(123).ad_groups(456).ads.create(ad)
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str
    creative_type: CreativeType = Field(alias="creativeType")
    status: AdStatus = AdStatus.ENABLED
    product_page_id: str | None = Field(default=None, alias="productPageId")


class AdUpdate(BaseModel):
    """Request model for updating an existing ad.

    Only include fields you want to update.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str | None = None
    status: AdStatus | None = None
