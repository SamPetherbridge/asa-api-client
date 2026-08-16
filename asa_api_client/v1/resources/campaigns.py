"""Campaigns resource for the Apple Ads Platform API v1.

Provides full CRUD and query over ``/v1/campaigns``, plus the
legacy-app limited-status diagnostics endpoint. Create and update
bodies are sent unwrapped, and every endpoint requires the ad-account
context header.
"""

from asa_api_client.v1.models.campaigns import (
    Campaign,
    CampaignCreate,
    CampaignUpdate,
    LegacyAppLimitedStatusReasonDetails,
)
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)


class CampaignResource(
    GettableMixin[Campaign, CampaignCreate, CampaignUpdate],
    QueryableMixin[Campaign, CampaignCreate, CampaignUpdate],
    CreatableMixin[Campaign, CampaignCreate, CampaignUpdate],
    UpdatableMixin[Campaign, CampaignCreate, CampaignUpdate],
    DeletableMixin[Campaign, CampaignCreate, CampaignUpdate],
    V1Resource[Campaign, CampaignCreate, CampaignUpdate],
):
    """Access to the v1 campaigns endpoints.

    Endpoints:
        - ``POST /v1/campaigns`` — create.
        - ``POST /v1/campaigns/query`` — query with filters/sorting.
        - ``GET /v1/campaigns/{id}`` — get by ID.
        - ``PUT /v1/campaigns/{id}`` — partial update.
        - ``DELETE /v1/campaigns/{id}`` — soft delete (cascades to ad
          groups, keywords, and ads).
        - ``GET /v1/campaigns/{id}/legacy-app-limited-status-reason-details``
          — per-market limited-status diagnostics.

    Note:
        Deleted campaigns are excluded from query results by default
        (filter ``deleted IN [true, false]`` to include them), but
        ``get()`` returns them regardless of deletion status.
    """

    base_path = "campaigns"
    model_class = Campaign

    def legacy_app_limited_status_reason_details(
        self, campaign_id: int | str
    ) -> LegacyAppLimitedStatusReasonDetails:
        """Get per-market limited-status reasons for a legacy app campaign.

        Args:
            campaign_id: The campaign ID.

        Returns:
            A map of country/region codes to human-readable reason
            strings explaining why delivery is limited per market.

        Raises:
            NotFoundError: If the campaign doesn't exist.
        """
        data = self._request("GET", f"{campaign_id}/legacy-app-limited-status-reason-details")
        return LegacyAppLimitedStatusReasonDetails.model_validate(data.get("result") or {})

    async def legacy_app_limited_status_reason_details_async(
        self, campaign_id: int | str
    ) -> LegacyAppLimitedStatusReasonDetails:
        """Get per-market limited-status reasons asynchronously.

        Args:
            campaign_id: The campaign ID.

        Returns:
            A map of country/region codes to human-readable reason
            strings explaining why delivery is limited per market.

        Raises:
            NotFoundError: If the campaign doesn't exist.
        """
        data = await self._request_async(
            "GET", f"{campaign_id}/legacy-app-limited-status-reason-details"
        )
        return LegacyAppLimitedStatusReasonDetails.model_validate(data.get("result") or {})
