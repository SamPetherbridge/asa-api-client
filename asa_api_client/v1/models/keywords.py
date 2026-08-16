"""Models for Apple Ads Platform API v1 keywords and negative keywords.

Keywords connect App Store (or Apple Maps) search queries to an ad
group's ads; negative keywords exclude search terms at campaign or ad
group level. ``text`` and ``matchType`` are immutable after creation —
delete and recreate to change them.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import Money, V1Model


class KeywordStatus(StrEnum):
    """Advertiser-configurable serving state for a keyword."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class KeywordMatchType(StrEnum):
    """Matching behavior against user search queries.

    ``EXACT``/``BROAD`` apply to App Store Search results campaigns;
    ``PHRASE``/``CATEGORY`` apply to Apple Maps campaigns. ``CATEGORY``
    is not supported for negative keywords.
    """

    EXACT = "EXACT"
    BROAD = "BROAD"
    PHRASE = "PHRASE"
    CATEGORY = "CATEGORY"


class KeywordDisplayStatus(StrEnum):
    """Read-only rollup of keyword + ad group + campaign delivery state."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    AD_GROUP_ON_HOLD = "AD_GROUP_ON_HOLD"
    CAMPAIGN_ON_HOLD = "CAMPAIGN_ON_HOLD"


class NegativeKeywordStatus(StrEnum):
    """Advertiser-configurable active state for a negative keyword."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class Keyword(V1Model):
    """A targeting keyword connecting search queries to an ad group's ads.

    Inherits the ad group's default bid unless ``bid`` is set.

    Attributes:
        ad_account_id: Ad account this keyword belongs to. Read-only.
        campaign_id: Parent campaign ID. Read-only.
        ad_group_id: Owning ad group. Immutable after creation.
        text: Advertiser-given keyword text. Immutable after creation.
        match_type: Matching behavior. Immutable after creation.
        bid: Per-keyword bid override of the ad group default bid.
        status: Serving state (``ENABLED``/``PAUSED``).
        id: Unique identifier. Read-only.
        creation_time: Creation timestamp. Read-only.
        modification_time: Last-modified timestamp. Read-only.
        deleted: Soft-delete flag. Read-only.
        display_status: Computed delivery-state rollup. Read-only.
    """

    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    text: str | None = None
    match_type: KeywordMatchType | None = Field(default=None, alias="matchType")
    bid: Money | None = None
    status: KeywordStatus | None = None
    id: int | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    deleted: bool | None = None
    display_status: KeywordDisplayStatus | None = Field(default=None, alias="displayStatus")


class KeywordCreate(V1Model):
    """Request body for ``POST /v1/keywords``.

    Attributes:
        ad_group_id: The ad group this keyword targets. Required.
        text: Keyword text. Required; immutable after creation. For
            ``CATEGORY`` match on Maps, must be a Maps business category
            identifier (e.g. ``dining.restaurant``).
        match_type: Matching behavior. Immutable after creation.
        bid: Per-keyword bid override. Omit to default to the ad
            group's bid strategy.
        status: Initial serving state.
    """

    ad_group_id: int = Field(alias="adGroupId")
    text: str
    match_type: KeywordMatchType | None = Field(default=None, alias="matchType")
    bid: Money | None = None
    status: KeywordStatus | None = None


class KeywordUpdate(V1Model):
    """Request body for ``PUT /v1/keywords/{id}``.

    Only ``bid`` and ``status`` are mutable; ``text`` and ``matchType``
    are rejected by the API. Omitted fields keep their current values.

    Attributes:
        bid: New bid; must be a valid Money value (the API rejects
            an explicit ``null`` bid on update).
        status: New serving state (``ENABLED``/``PAUSED``).
    """

    bid: Money | None = None
    status: KeywordStatus | None = None


class NegativeKeyword(V1Model):
    """A keyword exclusion preventing ads from matching queries.

    Negative keywords can be campaign-level (``ad_group_id`` absent) or
    ad-group-level (``ad_group_id`` present). They never carry a bid.

    Attributes:
        ad_account_id: Owning ad account. Read-only.
        campaign_id: Campaign ID. Immutable after creation.
        ad_group_id: Owning ad group; None for campaign-level
            negatives. Immutable after creation.
        text: Excluded keyword text. Immutable after creation.
        match_type: Matching behavior (``CATEGORY`` is not supported
            for negatives). Immutable after creation.
        status: Active state (``ENABLED``/``PAUSED``).
        id: System-assigned unique identifier. Read-only.
        creation_time: Creation timestamp. Read-only.
        modification_time: Last-modified timestamp. Read-only.
        deleted: Soft-delete flag. Read-only.
    """

    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    text: str | None = None
    match_type: KeywordMatchType | None = Field(default=None, alias="matchType")
    status: NegativeKeywordStatus | None = None
    id: int | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    deleted: bool | None = None


class NegativeKeywordCreate(V1Model):
    """Request body for ``POST /v1/negative-keywords``.

    Set exactly one of ``campaign_id`` (campaign-level) or
    ``ad_group_id`` (ad-group-level).

    Attributes:
        campaign_id: Set for a campaign-level negative; must not be
            combined with ``ad_group_id``.
        ad_group_id: Set for an ad-group-level negative; must not be
            combined with ``campaign_id``.
        text: Keyword text to exclude. Required; immutable after
            creation.
        match_type: Matching behavior; defaults to ``BROAD`` when
            omitted. ``CATEGORY`` is not supported for negatives.
        status: Initial state; defaults to ``ENABLED`` when omitted.
    """

    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    text: str
    match_type: KeywordMatchType | None = Field(default=None, alias="matchType")
    status: NegativeKeywordStatus | None = None


class NegativeKeywordUpdate(V1Model):
    """Request body for ``PUT /v1/negative-keywords/{id}``.

    Only ``status`` is mutable; ``text`` and ``matchType`` are rejected
    by the API.

    Attributes:
        status: ``PAUSED`` temporarily allows traffic from the excluded
            term; ``ENABLED`` re-activates the exclusion.
    """

    status: NegativeKeywordStatus | None = None
