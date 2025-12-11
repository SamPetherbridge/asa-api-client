"""Campaign resource for the Apple Search Ads API.

Provides methods for managing advertising campaigns.
"""

from typing import TYPE_CHECKING

from asa_api_client.models.campaigns import Campaign, CampaignCreate, CampaignUpdate
from asa_api_client.resources.base import WritableResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient
    from asa_api_client.resources.ad_groups import AdGroupResource
    from asa_api_client.resources.keywords import NegativeKeywordResource


class CampaignResource(WritableResource[Campaign, CampaignCreate, CampaignUpdate]):
    """Resource for managing Apple Search Ads campaigns.

    Campaigns are the top-level entities that contain ad groups,
    keywords, and ads. Each campaign has its own budget and targets
    specific countries or regions.

    Example:
        List all campaigns::

            campaigns = client.campaigns.list()
            for campaign in campaigns:
                print(f"{campaign.name}: {campaign.status}")

        Create a new campaign::

            from asa_api_client.models import CampaignCreate, Money, CampaignSupplySource

            campaign = client.campaigns.create(
                CampaignCreate(
                    name="My Campaign",
                    budget_amount=Money.usd(10000),
                    daily_budget_amount=Money.usd(100),
                    adam_id=123456789,
                    countries_or_regions=["US", "CA"],
                    supply_sources=[CampaignSupplySource.APPSTORE_SEARCH_RESULTS],
                )
            )

        Find enabled campaigns::

            from asa_api_client.models import Selector

            enabled = client.campaigns.find(
                Selector()
                .where("status", "==", "ENABLED")
                .sort_by("modificationTime", descending=True)
            )

        Access ad groups for a campaign::

            ad_groups = client.campaigns(123).ad_groups.list()
    """

    base_path = "campaigns"
    model_class = Campaign

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the campaign resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        super().__init__(client)
        self._campaign_id: int | None = None

    def __call__(self, campaign_id: int) -> "CampaignContext":
        """Get a context for a specific campaign.

        This allows accessing nested resources like ad groups and
        negative keywords for a specific campaign.

        Args:
            campaign_id: The campaign ID.

        Returns:
            A CampaignContext for accessing nested resources.

        Example:
            Access ad groups for campaign 123::

                ad_groups = client.campaigns(123).ad_groups.list()
        """
        return CampaignContext(self._client, campaign_id)


class CampaignContext:
    """Context for accessing resources within a specific campaign.

    This class provides access to nested resources like ad groups
    and negative keywords that belong to a specific campaign.

    Attributes:
        campaign_id: The campaign ID this context is for.
        ad_groups: Resource for managing ad groups in this campaign.
        negative_keywords: Resource for campaign-level negative keywords.
    """

    def __init__(self, client: "AppleSearchAdsClient", campaign_id: int) -> None:
        """Initialize the campaign context.

        Args:
            client: The parent AppleSearchAdsClient instance.
            campaign_id: The campaign ID.
        """
        self._client = client
        self.campaign_id = campaign_id

        # Import here to avoid circular imports
        from asa_api_client.resources.ad_groups import AdGroupResource
        from asa_api_client.resources.keywords import NegativeKeywordResource

        self._ad_groups = AdGroupResource(client, campaign_id)
        self._negative_keywords = NegativeKeywordResource(
            client,
            campaign_id=campaign_id,
        )

    @property
    def ad_groups(self) -> "AdGroupResource":
        """Get the ad groups resource for this campaign.

        Returns:
            AdGroupResource for managing ad groups in this campaign.

        Example:
            List ad groups::

                ad_groups = client.campaigns(123).ad_groups.list()
        """
        return self._ad_groups

    @property
    def negative_keywords(self) -> "NegativeKeywordResource":
        """Get the negative keywords resource for this campaign.

        Returns:
            NegativeKeywordResource for campaign-level negative keywords.

        Example:
            Add negative keyword::

                from asa_api_client.models import NegativeKeywordCreate, KeywordMatchType

                client.campaigns(123).negative_keywords.create(
                    NegativeKeywordCreate(
                        text="free",
                        match_type=KeywordMatchType.BROAD,
                    )
                )
        """
        return self._negative_keywords
