"""Ad Group resource for the Apple Search Ads API.

Provides methods for managing ad groups within campaigns.
"""

from typing import TYPE_CHECKING

from asa_api_client.models.ad_groups import AdGroup, AdGroupCreate, AdGroupUpdate
from asa_api_client.resources.base import WritableResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient
    from asa_api_client.resources.keywords import KeywordResource, NegativeKeywordResource


class AdGroupResource(WritableResource[AdGroup, AdGroupCreate, AdGroupUpdate]):
    """Resource for managing ad groups within a campaign.

    Ad groups are contained within campaigns and define targeting
    criteria, bids, and contain keywords and ads.

    Example:
        List all ad groups in a campaign::

            ad_groups = client.campaigns(123).ad_groups.list()
            for ad_group in ad_groups:
                print(f"{ad_group.name}: {ad_group.status}")

        Create a new ad group::

            from asa_api_client.models import AdGroupCreate, Money

            ad_group = client.campaigns(123).ad_groups.create(
                AdGroupCreate(
                    name="US Users",
                    default_bid_amount=Money.usd("1.50"),
                )
            )

        Access keywords for an ad group::

            keywords = client.campaigns(123).ad_groups(456).keywords.list()
    """

    base_path = "campaigns/{campaign_id}/adgroups"
    model_class = AdGroup

    def __init__(self, client: "AppleSearchAdsClient", campaign_id: int) -> None:
        """Initialize the ad group resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
            campaign_id: The parent campaign ID.
        """
        super().__init__(client)
        self.campaign_id = campaign_id
        self.base_path = f"campaigns/{campaign_id}/adgroups"

    def __call__(self, ad_group_id: int) -> "AdGroupContext":
        """Get a context for a specific ad group.

        This allows accessing nested resources like keywords for
        a specific ad group.

        Args:
            ad_group_id: The ad group ID.

        Returns:
            An AdGroupContext for accessing nested resources.

        Example:
            Access keywords for ad group 456::

                keywords = client.campaigns(123).ad_groups(456).keywords.list()
        """
        return AdGroupContext(self._client, self.campaign_id, ad_group_id)


class AdGroupContext:
    """Context for accessing resources within a specific ad group.

    This class provides access to nested resources like keywords
    that belong to a specific ad group.

    Attributes:
        campaign_id: The parent campaign ID.
        ad_group_id: The ad group ID this context is for.
        keywords: Resource for managing targeting keywords.
        negative_keywords: Resource for ad group-level negative keywords.
    """

    def __init__(
        self,
        client: "AppleSearchAdsClient",
        campaign_id: int,
        ad_group_id: int,
    ) -> None:
        """Initialize the ad group context.

        Args:
            client: The parent AppleSearchAdsClient instance.
            campaign_id: The parent campaign ID.
            ad_group_id: The ad group ID.
        """
        self._client = client
        self.campaign_id = campaign_id
        self.ad_group_id = ad_group_id

        # Import here to avoid circular imports
        from asa_api_client.resources.keywords import KeywordResource, NegativeKeywordResource

        self._keywords = KeywordResource(client, campaign_id, ad_group_id)
        self._negative_keywords = NegativeKeywordResource(
            client,
            campaign_id=campaign_id,
            ad_group_id=ad_group_id,
        )

    @property
    def keywords(self) -> "KeywordResource":
        """Get the keywords resource for this ad group.

        Returns:
            KeywordResource for managing targeting keywords.

        Example:
            List keywords::

                keywords = client.campaigns(123).ad_groups(456).keywords.list()
        """
        return self._keywords

    @property
    def negative_keywords(self) -> "NegativeKeywordResource":
        """Get the negative keywords resource for this ad group.

        Returns:
            NegativeKeywordResource for ad group-level negative keywords.

        Example:
            Add negative keyword::

                from asa_api_client.models import NegativeKeywordCreate, KeywordMatchType

                client.campaigns(123).ad_groups(456).negative_keywords.create(
                    NegativeKeywordCreate(
                        text="free",
                        match_type=KeywordMatchType.EXACT,
                    )
                )
        """
        return self._negative_keywords
