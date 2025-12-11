"""Keyword models for the Apple Search Ads API.

This module contains models for targeting keywords (positive keywords
that you bid on) and negative keywords (keywords you want to exclude).
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from asa_api_client.models.base import Money


class KeywordMatchType(StrEnum):
    """Match type for keywords.

    Attributes:
        BROAD: Matches search queries that contain the keyword terms
            in any order, including synonyms and related words.
        EXACT: Matches search queries that exactly match the keyword
            or very close variants.
    """

    BROAD = "BROAD"
    EXACT = "EXACT"


class KeywordStatus(StrEnum):
    """Status of a keyword."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class KeywordServingStatus(StrEnum):
    """Serving status of a keyword."""

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class KeywordDisplayStatus(StrEnum):
    """Human-readable display status for keywords."""

    RUNNING = "RUNNING"
    ON_HOLD = "ON_HOLD"
    PAUSED = "PAUSED"
    DELETED = "DELETED"


class Keyword(BaseModel):
    """A targeting keyword for bidding.

    Targeting keywords are the search terms you bid on to show
    your ads. Each keyword can have a custom bid amount.

    Attributes:
        id: The unique identifier for the keyword.
        campaign_id: The parent campaign ID.
        ad_group_id: The parent ad group ID.
        text: The keyword text.
        match_type: How strictly to match search queries.
        status: The keyword status.
        bid_amount: The bid amount for this keyword.
        modification_time: When the keyword was last modified.
        deleted: Whether the keyword has been deleted.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    campaign_id: int = Field(alias="campaignId")
    ad_group_id: int = Field(alias="adGroupId")
    text: str
    match_type: KeywordMatchType | str = Field(alias="matchType")
    status: KeywordStatus | str
    bid_amount: Money = Field(alias="bidAmount")
    modification_time: datetime = Field(alias="modificationTime")
    deleted: bool = False
    serving_status: KeywordServingStatus | str | None = Field(default=None, alias="servingStatus")
    display_status: KeywordDisplayStatus | str | None = Field(default=None, alias="displayStatus")


class KeywordCreate(BaseModel):
    """Request model for creating a targeting keyword.

    Example:
        Create an exact match keyword::

            keyword = KeywordCreate(
                text="productivity app",
                match_type=KeywordMatchType.EXACT,
                bid_amount=Money.usd("2.50"),
            )

            created = client.campaigns(123).ad_groups(456).keywords.create(keyword)

        Bulk create keywords::

            keywords = [
                KeywordCreate(text="task manager", match_type=KeywordMatchType.BROAD),
                KeywordCreate(text="todo app", match_type=KeywordMatchType.EXACT),
            ]

            created = client.campaigns(123).ad_groups(456).keywords.create_bulk(keywords)
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    text: Annotated[str, Field(min_length=1, max_length=80)]
    match_type: KeywordMatchType = Field(alias="matchType")
    status: KeywordStatus = KeywordStatus.ACTIVE
    bid_amount: Money | None = Field(default=None, alias="bidAmount")


class KeywordUpdate(BaseModel):
    """Request model for updating a targeting keyword.

    Example:
        Update keyword bid::

            update = KeywordUpdate(
                bid_amount=Money.usd("3.00"),
            )

            updated = client.campaigns(123).ad_groups(456).keywords.update(
                keyword_id=789,
                data=update,
            )
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    status: KeywordStatus | None = None
    bid_amount: Money | None = Field(default=None, alias="bidAmount")


class NegativeKeyword(BaseModel):
    """A negative keyword to exclude from targeting.

    Negative keywords prevent your ads from showing for specific
    search terms. They can be set at the campaign or ad group level.

    Attributes:
        id: The unique identifier for the negative keyword.
        campaign_id: The parent campaign ID.
        ad_group_id: The ad group ID (if ad group level negative).
        text: The keyword text to exclude.
        match_type: How strictly to match search queries.
        status: The keyword status.
        modification_time: When the keyword was last modified.
        deleted: Whether the keyword has been deleted.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int
    campaign_id: int = Field(alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    text: str
    match_type: KeywordMatchType | str = Field(alias="matchType")
    status: KeywordStatus | str
    modification_time: datetime = Field(alias="modificationTime")
    deleted: bool = False


class NegativeKeywordCreate(BaseModel):
    """Request model for creating a negative keyword.

    Example:
        Create campaign-level negative keyword::

            negative = NegativeKeywordCreate(
                text="free",
                match_type=KeywordMatchType.BROAD,
            )

            created = client.campaigns(123).negative_keywords.create(negative)

        Create ad group-level negative keyword::

            negative = NegativeKeywordCreate(
                text="cheap",
                match_type=KeywordMatchType.EXACT,
            )

            created = client.campaigns(123).ad_groups(456).negative_keywords.create(negative)
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    text: Annotated[str, Field(min_length=1, max_length=80)]
    match_type: KeywordMatchType = Field(alias="matchType")
    status: KeywordStatus = KeywordStatus.ACTIVE
