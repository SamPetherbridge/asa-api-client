"""App search resource for the Apple Search Ads API.

Provides methods for searching iOS apps eligible for advertising.
"""

import builtins
from typing import TYPE_CHECKING, Any

from asa_api_client.models.apps import AppInfo
from asa_api_client.resources.base import BaseResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class AppResource(BaseResource[AppInfo, AppInfo, AppInfo]):
    """Resource for searching eligible iOS apps.

    Used to find apps that can be promoted in campaigns.

    Example:
        Search for apps::

            apps = client.apps.search(query="my app name")
            for app in apps:
                print(f"{app.app_name} (adam_id={app.adam_id})")
    """

    base_path = "search/apps"
    model_class = AppInfo

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the app search resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        super().__init__(client)

    def search(
        self,
        *,
        query: str,
        return_own_apps: bool = False,
        limit: int = 1000,
        offset: int = 0,
    ) -> builtins.list[AppInfo]:
        """Search for iOS apps eligible for advertising.

        Args:
            query: The search query string.
            return_own_apps: If True, only return apps owned by the org.
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            List of matching app info.
        """
        params: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "returnOwnedApps": str(return_own_apps).lower(),
        }

        data = self._request("GET", params=params)
        items = data.get("data", [])
        return [AppInfo.model_validate(item) for item in items]

    async def search_async(
        self,
        *,
        query: str,
        return_own_apps: bool = False,
        limit: int = 1000,
        offset: int = 0,
    ) -> builtins.list[AppInfo]:
        """Search for iOS apps eligible for advertising asynchronously.

        Args:
            query: The search query string.
            return_own_apps: If True, only return apps owned by the org.
            limit: Maximum number of results to return.
            offset: Starting position for results.

        Returns:
            List of matching app info.
        """
        params: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "returnOwnedApps": str(return_own_apps).lower(),
        }

        data = await self._request_async("GET", params=params)
        items = data.get("data", [])
        return [AppInfo.model_validate(item) for item in items]
