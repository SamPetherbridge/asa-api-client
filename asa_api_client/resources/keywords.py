"""Keyword resources for the Apple Search Ads API.

Provides methods for managing targeting keywords and negative keywords.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from asa_api_client.models.base import PaginatedResponse
from asa_api_client.models.keywords import (
    Keyword,
    KeywordCreate,
    KeywordUpdate,
    NegativeKeyword,
    NegativeKeywordCreate,
)
from asa_api_client.resources.base import WritableResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class KeywordResource(WritableResource[Keyword, KeywordCreate, KeywordUpdate]):
    """Resource for managing targeting keywords in an ad group.

    Targeting keywords are the search terms you bid on to show
    your ads. Each keyword can have a custom bid amount.

    Example:
        List all keywords::

            keywords = client.campaigns(123).ad_groups(456).keywords.list()

        Create a keyword::

            from asa_api_client.models import KeywordCreate, KeywordMatchType, Money

            keyword = client.campaigns(123).ad_groups(456).keywords.create(
                KeywordCreate(
                    text="productivity app",
                    match_type=KeywordMatchType.EXACT,
                    bid_amount=Money.usd("2.00"),
                )
            )

        Bulk create keywords::

            keywords = [
                KeywordCreate(text="todo app", match_type=KeywordMatchType.EXACT),
                KeywordCreate(text="task manager", match_type=KeywordMatchType.BROAD),
            ]
            created = client.campaigns(123).ad_groups(456).keywords.create_bulk(keywords)
    """

    base_path = "campaigns/{campaign_id}/adgroups/{ad_group_id}/targetingkeywords"
    model_class = Keyword

    def __init__(
        self,
        client: "AppleSearchAdsClient",
        campaign_id: int,
        ad_group_id: int,
    ) -> None:
        """Initialize the keyword resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
            campaign_id: The parent campaign ID.
            ad_group_id: The parent ad group ID.
        """
        super().__init__(client)
        self.campaign_id = campaign_id
        self.ad_group_id = ad_group_id
        self.base_path = f"campaigns/{campaign_id}/adgroups/{ad_group_id}/targetingkeywords"

    def create_bulk(self, keywords: list[KeywordCreate]) -> PaginatedResponse[Keyword]:
        """Create multiple keywords at once.

        Args:
            keywords: List of keywords to create.

        Returns:
            A paginated response containing the created keywords.

        Example:
            Bulk create keywords::

                keywords = [
                    KeywordCreate(text="todo app", match_type=KeywordMatchType.EXACT),
                    KeywordCreate(text="task manager", match_type=KeywordMatchType.BROAD),
                ]
                created = client.campaigns(123).ad_groups(456).keywords.create_bulk(keywords)
        """
        data = [kw.model_dump(by_alias=True, exclude_none=True, mode="json") for kw in keywords]
        response = self._request("POST", "bulk", json=data)
        return self._parse_list_response(response)

    async def create_bulk_async(self, keywords: list[KeywordCreate]) -> PaginatedResponse[Keyword]:
        """Create multiple keywords at once asynchronously.

        Args:
            keywords: List of keywords to create.

        Returns:
            A paginated response containing the created keywords.
        """
        data = [kw.model_dump(by_alias=True, exclude_none=True, mode="json") for kw in keywords]
        response = await self._request_async("POST", "bulk", json=data)
        return self._parse_list_response(response)

    def update_bulk(self, updates: list[tuple[int, KeywordUpdate]]) -> PaginatedResponse[Keyword]:
        """Update multiple keywords at once.

        Args:
            updates: List of (keyword_id, update_data) tuples.

        Returns:
            A paginated response containing the updated keywords.

        Example:
            Bulk update keywords::

                updates = [
                    (789, KeywordUpdate(status=KeywordStatus.PAUSED)),
                    (790, KeywordUpdate(bid_amount=Money.usd("3.00"))),
                ]
                updated = client.campaigns(123).ad_groups(456).keywords.update_bulk(updates)
        """
        data = []
        for keyword_id, update in updates:
            update_dict = update.model_dump(by_alias=True, exclude_none=True, mode="json")
            update_dict["id"] = keyword_id
            data.append(update_dict)

        response = self._request("PUT", "bulk", json=data)
        return self._parse_list_response(response)

    async def update_bulk_async(
        self, updates: list[tuple[int, KeywordUpdate]]
    ) -> PaginatedResponse[Keyword]:
        """Update multiple keywords at once asynchronously.

        Args:
            updates: List of (keyword_id, update_data) tuples.

        Returns:
            A paginated response containing the updated keywords.
        """
        data = []
        for keyword_id, update in updates:
            update_dict = update.model_dump(by_alias=True, exclude_none=True, mode="json")
            update_dict["id"] = keyword_id
            data.append(update_dict)

        response = await self._request_async("PUT", "bulk", json=data)
        return self._parse_list_response(response)


class _NegativeKeywordUpdate(BaseModel):
    """Placeholder update model for negative keywords (updates not supported)."""

    pass


class NegativeKeywordResource(
    WritableResource[NegativeKeyword, NegativeKeywordCreate, _NegativeKeywordUpdate]
):
    """Resource for managing negative keywords.

    Negative keywords prevent your ads from showing for specific
    search terms. They can be set at the campaign or ad group level.

    Example:
        Campaign-level negative keywords::

            # Add a negative keyword to exclude from all ad groups
            client.campaigns(123).negative_keywords.create(
                NegativeKeywordCreate(
                    text="free",
                    match_type=KeywordMatchType.BROAD,
                )
            )

        Ad group-level negative keywords::

            # Add a negative keyword specific to an ad group
            client.campaigns(123).ad_groups(456).negative_keywords.create(
                NegativeKeywordCreate(
                    text="cheap",
                    match_type=KeywordMatchType.EXACT,
                )
            )
    """

    model_class = NegativeKeyword

    def __init__(
        self,
        client: "AppleSearchAdsClient",
        *,
        campaign_id: int,
        ad_group_id: int | None = None,
    ) -> None:
        """Initialize the negative keyword resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
            campaign_id: The parent campaign ID.
            ad_group_id: The parent ad group ID (for ad group-level negatives).
        """
        super().__init__(client)
        self.campaign_id = campaign_id
        self.ad_group_id = ad_group_id

        if ad_group_id is not None:
            self.base_path = f"campaigns/{campaign_id}/adgroups/{ad_group_id}/negativekeywords"
        else:
            self.base_path = f"campaigns/{campaign_id}/negativekeywords"

    def create_bulk(
        self, keywords: list[NegativeKeywordCreate]
    ) -> PaginatedResponse[NegativeKeyword]:
        """Create multiple negative keywords at once.

        Args:
            keywords: List of negative keywords to create.

        Returns:
            A paginated response containing the created negative keywords.
        """
        data = [kw.model_dump(by_alias=True, exclude_none=True, mode="json") for kw in keywords]
        response = self._request("POST", "bulk", json=data)
        return self._parse_list_response(response)

    async def create_bulk_async(
        self, keywords: list[NegativeKeywordCreate]
    ) -> PaginatedResponse[NegativeKeyword]:
        """Create multiple negative keywords at once asynchronously.

        Args:
            keywords: List of negative keywords to create.

        Returns:
            A paginated response containing the created negative keywords.
        """
        data = [kw.model_dump(by_alias=True, exclude_none=True, mode="json") for kw in keywords]
        response = await self._request_async("POST", "bulk", json=data)
        return self._parse_list_response(response)

    def update(self, resource_id: int, data: _NegativeKeywordUpdate) -> NegativeKeyword:
        """Update is not supported for negative keywords.

        Raises:
            NotImplementedError: Always, as negative keywords cannot be updated.
        """
        raise NotImplementedError(
            "Negative keywords cannot be updated. Delete and recreate instead."
        )

    async def update_async(self, resource_id: int, data: _NegativeKeywordUpdate) -> NegativeKeyword:
        """Update is not supported for negative keywords.

        Raises:
            NotImplementedError: Always, as negative keywords cannot be updated.
        """
        raise NotImplementedError(
            "Negative keywords cannot be updated. Delete and recreate instead."
        )
