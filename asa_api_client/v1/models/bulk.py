"""Models for Apple Ads Platform API v1 bulk operations.

Bulk endpoints create and update keywords and negative keywords in
batches. Every bulk request has the shape ``{allowPartialSuccess,
items: [{correlationId, data}]}``; the response ``result`` is an array
of per-item envelopes positionally parallel to the request items, each
carrying the client-supplied ``correlationId`` back alongside the
operation outcome and the full entity (or a per-item error).

The ``data`` payload models here mirror the single-record write models
in :mod:`asa_api_client.v1.models.keywords` but follow the bulk docs'
restrictions: keyword updates accept only ``bid``/``status``, negative
keyword updates only ``status``, and update payloads carry the target
``id`` inline (there is no path parameter on bulk endpoints).
"""

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import Field

from asa_api_client.v1.models.base import Money, V1Error, V1Model
from asa_api_client.v1.models.keywords import (
    Keyword,
    KeywordMatchType,
    KeywordStatus,
    NegativeKeyword,
    NegativeKeywordStatus,
)

DataT = TypeVar("DataT", bound=V1Model)
EntityT = TypeVar("EntityT", bound=V1Model)


class BulkOperation(StrEnum):
    """The operation a bulk item result reports on.

    ``DELETE`` is defined by the API's shared result envelope, but bulk
    delete endpoints are documented as "coming soon" and do not exist
    yet.
    """

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class BulkRequestItem(V1Model, Generic[DataT]):
    """One item in a bulk request: ``{correlationId, data}``.

    Attributes:
        correlation_id: Client-supplied int64 echoed back on the
            matching result entry. Results are also positionally
            parallel to request items, so this is optional.
        data: The operation payload (a ``Bulk*Create``/``Bulk*Update``
            model).
    """

    correlation_id: int | None = Field(default=None, alias="correlationId")
    data: DataT


class BulkItemResult(V1Model, Generic[EntityT]):
    """Per-item result envelope shared by all bulk responses.

    Attributes:
        correlation_id: Echo of the client-supplied correlation ID.
        operation: The operation performed (``CREATE``/``UPDATE``).
        success: Whether this item succeeded.
        result: The full entity after the operation; None on failure.
        error: Per-item error details; None on success.
    """

    correlation_id: int | None = Field(default=None, alias="correlationId")
    operation: BulkOperation | None = None
    success: bool | None = None
    result: EntityT | None = None
    error: V1Error | None = None


class BulkItemResultKeyword(BulkItemResult[Keyword]):
    """Per-item result for keyword bulk-create and bulk-update.

    ``result`` holds the full :class:`Keyword` entity on success.
    """


class BulkItemResultNegativeKeyword(BulkItemResult[NegativeKeyword]):
    """Per-item result for negative-keyword bulk-create and bulk-update.

    ``result`` holds the full :class:`NegativeKeyword` entity on
    success; its ``ad_group_id`` is None for campaign-level negatives.
    """


class BulkKeywordCreate(V1Model):
    """The ``data`` payload for one keyword bulk-create item.

    Items in one request may target different ad groups.

    Attributes:
        ad_group_id: Ad group in which the keyword is created. Required.
        text: Keyword text. Required; immutable after creation.
        match_type: Matching behavior (``CATEGORY`` is Apple Maps only).
        bid: Per-keyword bid; omit to default to the ad group's bid.
            Not used with Maximize Conversions campaigns.
        status: Initial serving state (``ENABLED``/``PAUSED``).
    """

    ad_group_id: int = Field(alias="adGroupId")
    text: str
    match_type: KeywordMatchType | None = Field(default=None, alias="matchType")
    bid: Money | None = None
    status: KeywordStatus | None = None


class BulkKeywordUpdate(V1Model):
    """The ``data`` payload for one keyword bulk-update item.

    Only ``bid`` and ``status`` are updatable; ``text`` and
    ``matchType`` are immutable after creation. Omitted fields retain
    their current values.

    Attributes:
        id: The keyword to update. Required.
        bid: New bid. Not used with Maximize Conversions campaigns.
        status: New serving state (``ENABLED``/``PAUSED``).
    """

    id: int
    bid: Money | None = None
    status: KeywordStatus | None = None


class BulkNegativeKeywordCreate(V1Model):
    """The ``data`` payload for one negative-keyword bulk-create item.

    Campaign-level and ad-group-level negatives can be mixed in one
    request: campaign-level sets ``campaign_id`` only; ad-group-level
    sets both ``campaign_id`` and ``ad_group_id``.

    Attributes:
        campaign_id: The owning campaign.
        ad_group_id: The owning ad group; omit for a campaign-level
            negative.
        text: Keyword text to exclude. Required.
        match_type: Matching behavior; ``CATEGORY`` is not supported
            for negative keywords.
        status: Initial state (``ENABLED``/``PAUSED``).
    """

    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    text: str
    match_type: KeywordMatchType | None = Field(default=None, alias="matchType")
    status: NegativeKeywordStatus | None = None


class BulkNegativeKeywordUpdate(V1Model):
    """The ``data`` payload for one negative-keyword bulk-update item.

    Only ``status`` is updatable. Omitted fields retain their current
    values.

    Attributes:
        id: The negative keyword to update. Required.
        status: New state (``ENABLED``/``PAUSED``).
    """

    id: int
    status: NegativeKeywordStatus | None = None
