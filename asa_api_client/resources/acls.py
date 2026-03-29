"""ACL resource for the Apple Search Ads API.

Provides access to the user's access control list, showing
which organizations and roles are available.
"""

import builtins
from typing import TYPE_CHECKING

from asa_api_client.models.acls import UserAcl
from asa_api_client.resources.base import BaseResource

if TYPE_CHECKING:
    from asa_api_client.client import AppleSearchAdsClient


class ACLResource(BaseResource[UserAcl, UserAcl, UserAcl]):
    """Resource for retrieving access control lists.

    ACLs show which organizations the API user has access to
    and what roles they have. Essential for multi-org setups.

    Example:
        List all accessible organizations::

            acls = client.acls.list()
            for acl in acls:
                print(f"{acl.org_name} (org_id={acl.org_id}): {acl.role_names}")
    """

    base_path = "acls"
    model_class = UserAcl

    def __init__(self, client: "AppleSearchAdsClient") -> None:
        """Initialize the ACL resource.

        Args:
            client: The parent AppleSearchAdsClient instance.
        """
        super().__init__(client)

    def list(self) -> builtins.list[UserAcl]:
        """List all organizations and roles accessible to the API user.

        Returns:
            List of UserAcl entries.
        """
        data = self._request("GET")
        items = data.get("data", [])
        return [UserAcl.model_validate(item) for item in items]

    async def list_async(self) -> builtins.list[UserAcl]:
        """List all accessible organizations asynchronously.

        Returns:
            List of UserAcl entries.
        """
        data = await self._request_async("GET")
        items = data.get("data", [])
        return [UserAcl.model_validate(item) for item in items]
