"""Models for the Apple Ads Platform API v1 ads endpoints.

Ads link an ad creative to an ad group and are the atomic serving
unit. Only ``name`` and ``status`` are mutable after creation;
``adGroupId`` and ``creativeId`` are immutable. Deletes are soft.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class AdStatus(StrEnum):
    """Advertiser-configurable serving state of an ad.

    Attributes:
        ENABLED: The advertiser has set the ad to run, so it can
            participate in auctions.
        PAUSED: The advertiser has paused the ad, so it does not
            participate in auctions.
    """

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class AdSystemStatus(StrEnum):
    """System-evaluated delivery state of an ad.

    Attributes:
        RUNNING: The ad is active and eligible to serve.
        NOT_RUNNING: The system has identified a condition preventing
            the ad from delivering.
    """

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class AdDisplayStatus(StrEnum):
    """Rolled-up, read-only delivery state of an ad.

    Combines advertiser settings and system conditions across the ad,
    ad group, campaign, and creative. Intended for displaying ad
    health in a UI.

    Attributes:
        RUNNING: The ad is actively delivering.
        PAUSED: The advertiser paused the ad.
        ON_HOLD: A system or account condition stops delivery.
        LIMITED: The ad is serving but at reduced capacity.
        PROCESSING: The system is processing the ad after a recent
            creation or update.
        DELETED: The advertiser soft-deleted the ad.
        AD_GROUP_ON_HOLD: Delivery stops because the parent ad group
            is on hold.
        CAMPAIGN_ON_HOLD: Delivery stops because the parent campaign
            is on hold.
    """

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ON_HOLD = "ON_HOLD"
    LIMITED = "LIMITED"
    PROCESSING = "PROCESSING"
    DELETED = "DELETED"
    AD_GROUP_ON_HOLD = "AD_GROUP_ON_HOLD"
    CAMPAIGN_ON_HOLD = "CAMPAIGN_ON_HOLD"


class AdSystemStatusReason(StrEnum):
    """Reason codes explaining why an ad is not currently running.

    One or more appear in ``systemStatusReasons`` when the ad's
    ``systemStatus`` is ``NOT_RUNNING``. Read-only, system-applied.
    """

    PROCESSING = "PROCESSING"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    DELETED_BY_USER = "DELETED_BY_USER"
    AD_APPROVAL_PENDING = "AD_APPROVAL_PENDING"
    AD_APPROVAL_REJECTED = "AD_APPROVAL_REJECTED"
    AD_APPROVAL_CREATIVE_DOC_EXPIRED = "AD_APPROVAL_CREATIVE_DOC_EXPIRED"
    AD_APPROVAL_CREATIVE_DOC_NOT_SUBMITTED = "AD_APPROVAL_CREATIVE_DOC_NOT_SUBMITTED"
    AD_APPROVAL_CREATIVE_DOC_PENDING = "AD_APPROVAL_CREATIVE_DOC_PENDING"
    AD_APPROVAL_CREATIVE_DOC_REJECTED = "AD_APPROVAL_CREATIVE_DOC_REJECTED"
    CREATIVE_SET_INVALID = "CREATIVE_SET_INVALID"
    CREATIVE_SET_UNSUPPORTED = "CREATIVE_SET_UNSUPPORTED"
    CREATIVE_INVALID = "CREATIVE_INVALID"
    CREATIVE_PENDING = "CREATIVE_PENDING"
    PRODUCT_PAGE_DELETED = "PRODUCT_PAGE_DELETED"
    PRODUCT_PAGE_HIDDEN = "PRODUCT_PAGE_HIDDEN"
    PRODUCT_PAGE_INSUFFICIENT_ASSETS = "PRODUCT_PAGE_INSUFFICIENT_ASSETS"
    PRODUCT_PAGE_UNAVAILABLE = "PRODUCT_PAGE_UNAVAILABLE"
    PRODUCT_PAGE_INCOMPATIBLE = "PRODUCT_PAGE_INCOMPATIBLE"
    CREATIVE_LOCALE_INCOMPATIBLE = "CREATIVE_LOCALE_INCOMPATIBLE"


class AdSystemLimitedStatusReason(StrEnum):
    """Reason codes for an ad running at reduced capacity.

    Appears in ``systemStatusLimitingReasons`` when a policy
    condition limits, but does not fully stop, delivery.

    Attributes:
        CREATIVE_POLICY_ISSUES: The ad creative associated with this
            ad has policy violations that limit but do not fully stop
            delivery.
    """

    CREATIVE_POLICY_ISSUES = "CREATIVE_POLICY_ISSUES"


class Ad(V1Model):
    """An ad linking an ad creative to an ad group for serving.

    All fields are optional response properties. Only ``name`` and
    ``status`` are mutable; the rest are read-only or immutable after
    creation.

    Attributes:
        id: Unique ad identifier. Read-only.
        name: Advertiser-given name. Mutable.
        status: Advertiser-configurable on/off switch. Mutable.
        ad_account_id: Owning ad account. Immutable after creation.
        campaign_id: Parent campaign. Immutable after creation.
        ad_group_id: Parent ad group. Immutable after creation.
        creative_id: Ad creative the ad was created from. Immutable
            after creation.
        system_status: System-computed serving status. Read-only.
        system_status_reasons: Reasons for the current system status;
            populated when not serving. Read-only.
        system_status_limiting_reasons: Policy conditions limiting
            (but not stopping) delivery. Read-only.
        creation_time: Creation timestamp (no timezone suffix in API
            responses). Read-only.
        modification_time: Last-modified timestamp. Read-only.
        display_status: Rolled-up delivery state combining ad, ad
            group, campaign, and creative eligibility. Read-only.
        deleted: Soft-delete flag. Read-only.
    """

    id: int | None = None
    name: str | None = None
    status: AdStatus | None = None
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    creative_id: int | None = Field(default=None, alias="creativeId")
    system_status: AdSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[AdSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    system_status_limiting_reasons: list[AdSystemLimitedStatusReason] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    display_status: AdDisplayStatus | None = Field(default=None, alias="displayStatus")
    deleted: bool | None = None


class AdCreate(V1Model):
    """Request body for ``POST /v1/ads``. All fields are required.

    The referenced ad creative must have a ``systemStatus`` of
    ``VALID``, and an ad cannot be enabled until its parent ad group
    and campaign are also enabled.

    Attributes:
        ad_group_id: A valid ad group ID within the same account.
            Immutable after creation.
        creative_id: The ad creative to serve. Immutable after
            creation.
        name: Advertiser-given name (minimum length 1).
        status: ``ENABLED`` to enter auctions, ``PAUSED`` to create
            suspended.
    """

    ad_group_id: int = Field(alias="adGroupId")
    creative_id: int = Field(alias="creativeId")
    name: str
    status: AdStatus


class AdUpdate(V1Model):
    """Request body for ``PUT /v1/ads/{id}``.

    Both fields are optional; omitted fields retain their current
    values (partial-update semantics).

    Attributes:
        name: New advertiser-given name (minimum length 1 if
            provided).
        status: ``PAUSED`` immediately stops auction participation;
            ``ENABLED`` resumes.
    """

    name: str | None = None
    status: AdStatus | None = None
