"""Resources for Apple Ads Platform API v1 keywords and negative keywords.

Both resources use flat top-level paths (``/v1/keywords`` and
``/v1/negative-keywords``) and unwrapped request bodies. Create and
update operate on one record per request; bulk operations live in the
separate bulk-operations resource.
"""

from asa_api_client.v1.models.keywords import (
    Keyword,
    KeywordCreate,
    KeywordUpdate,
    NegativeKeyword,
    NegativeKeywordCreate,
    NegativeKeywordUpdate,
)
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)


class KeywordResource(
    GettableMixin[Keyword, KeywordCreate, KeywordUpdate],
    QueryableMixin[Keyword, KeywordCreate, KeywordUpdate],
    CreatableMixin[Keyword, KeywordCreate, KeywordUpdate],
    UpdatableMixin[Keyword, KeywordCreate, KeywordUpdate],
    DeletableMixin[Keyword, KeywordCreate, KeywordUpdate],
    V1Resource[Keyword, KeywordCreate, KeywordUpdate],
):
    """Targeting keywords for ad groups.

    Endpoints:
        - ``POST /v1/keywords`` — create one keyword.
        - ``POST /v1/keywords/query`` — query keywords (an
          ``adGroupId`` or ``campaignId`` filter is required unless
          filtering by ``id``).
        - ``GET /v1/keywords/{id}`` — get a keyword (soft-deleted
          keywords are still returned, with ``deleted=True``).
        - ``PUT /v1/keywords/{id}`` — update ``bid``/``status`` only.
        - ``DELETE /v1/keywords/{id}`` — soft-delete a keyword.

    Example:
        Pause a keyword::

            from asa_api_client.v1.models.keywords import KeywordStatus, KeywordUpdate

            client.keywords.update(300, KeywordUpdate(status=KeywordStatus.PAUSED))
    """

    base_path = "keywords"
    model_class = Keyword


class NegativeKeywordResource(
    GettableMixin[NegativeKeyword, NegativeKeywordCreate, NegativeKeywordUpdate],
    QueryableMixin[NegativeKeyword, NegativeKeywordCreate, NegativeKeywordUpdate],
    CreatableMixin[NegativeKeyword, NegativeKeywordCreate, NegativeKeywordUpdate],
    UpdatableMixin[NegativeKeyword, NegativeKeywordCreate, NegativeKeywordUpdate],
    DeletableMixin[NegativeKeyword, NegativeKeywordCreate, NegativeKeywordUpdate],
    V1Resource[NegativeKeyword, NegativeKeywordCreate, NegativeKeywordUpdate],
):
    """Keyword exclusions at campaign or ad group level.

    Endpoints:
        - ``POST /v1/negative-keywords`` — create one negative keyword
          (set exactly one of ``campaignId`` or ``adGroupId``).
        - ``POST /v1/negative-keywords/query`` — query negatives (an
          ``adGroupId`` filter is always required unless filtering by
          ``id``; ``IS_NULL``/``IS_NOT_NULL``/``NOT_EQUALS`` select
          campaign- vs ad-group-level records).
        - ``GET /v1/negative-keywords/{id}`` — get a negative keyword.
        - ``PUT /v1/negative-keywords/{id}`` — update ``status`` only.
        - ``DELETE /v1/negative-keywords/{id}`` — soft-delete.

    Example:
        Find campaign-level negatives::

            from asa_api_client.v1.query import Query

            page = client.negative_keywords.query(
                Query().where("adGroupId", "IS_NULL").where("campaignId", "EQUALS", 100)
            )
    """

    base_path = "negative-keywords"
    model_class = NegativeKeyword
