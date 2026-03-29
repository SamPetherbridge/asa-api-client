"""Ad resource for the Apple Search Ads API.

Provides methods for managing ads within ad groups.
"""

from typing import TYPE_CHECKING

from asa_api_client.models.ads import Ad, AdCreate, AdUpdate
from asa_api_client.models.base import PaginatedResponse, Selector
from asa_api_client.resources.base import WritableResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class AdResource(WritableResource[Ad, AdCreate, AdUpdate]):
    """Resource for managing ads within an ad group.

    Ads represent the actual advertisements shown to users,
    including product page ad variations.

    Example:
        List all ads in an ad group::

            ads = client.campaigns(123).ad_groups(456).ads.list()

        Create a product page ad::

            from asa_api_client.models.ads import AdCreate, CreativeType

            ad = client.campaigns(123).ad_groups(456).ads.create(
                AdCreate(
                    name="Holiday Product Page",
                    creative_type=CreativeType.CUSTOM_PRODUCT_PAGE,
                    product_page_id="abc123",
                )
            )
    """

    model_class = Ad

    def __init__(
        self,
        client: "AppleSearchAdsClient",
        campaign_id: int,
        ad_group_id: int,
    ) -> None:
        """Initialize the ad resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
            campaign_id: The parent campaign ID.
            ad_group_id: The parent ad group ID.
        """
        super().__init__(client)
        self.campaign_id = campaign_id
        self.ad_group_id = ad_group_id
        self.base_path = f"campaigns/{campaign_id}/adgroups/{ad_group_id}/ads"

    def find(self, selector: Selector) -> PaginatedResponse[Ad]:
        """Find ads matching a selector.

        Note: The find endpoint for ads is at the campaign level,
        not the ad group level.

        Args:
            selector: The query selector with conditions.

        Returns:
            A paginated response containing matching ads.
        """
        # Ad find is at campaign level: /campaigns/{id}/ads/find
        original_path = self.base_path
        self.base_path = f"campaigns/{self.campaign_id}/ads"
        try:
            return super().find(selector)
        finally:
            self.base_path = original_path

    async def find_async(self, selector: Selector) -> PaginatedResponse[Ad]:
        """Find ads matching a selector asynchronously.

        Args:
            selector: The query selector with conditions.

        Returns:
            A paginated response containing matching ads.
        """
        original_path = self.base_path
        self.base_path = f"campaigns/{self.campaign_id}/ads"
        try:
            return await super().find_async(selector)
        finally:
            self.base_path = original_path
