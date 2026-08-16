"""Resources for the Apple Ads Platform API v1 account-management surface.

Covers caller identity (``GET /me``), access control (``GET /acls``),
organizations (``GET /orgs/{id}``), ad accounts (``POST /ad-accounts``,
``GET/PUT /ad-accounts/{id}``), and advertiser resources
(``GET /advertiser-resources``).

Context-header semantics differ per endpoint: only ``GET`` and ``PUT``
on ``/ad-accounts/{id}`` require ``X-AP-Context``; identity, ACL, org,
advertiser-resource, and ad-account creation calls do not.
"""

from typing import TYPE_CHECKING

from asa_api_client.v1.models.ad_accounts import (
    AdAccount,
    AdAccountCreate,
    AdAccountUpdate,
    AdvertiserResourceType,
    Delegation,
    Me,
    Org,
    UserAccessResult,
    UserAcl,
)
from asa_api_client.v1.resources.base import GettableMixin, UpdatableMixin, V1Resource

if TYPE_CHECKING:
    from asa_api_client.v1.client import AppleAdsClient


class _ContextFreeAdAccountOps(V1Resource[AdAccount, AdAccountCreate, AdAccountUpdate]):
    """Context-free transport for ``GET /me`` and ``POST /ad-accounts``.

    These endpoints do not require the ``X-AP-Context`` header, unlike
    the get/update endpoints on :class:`AdAccountResource`, so they run
    through this sibling resource with an empty base path.
    """

    base_path = ""
    model_class = AdAccount
    requires_account_context = False


class AdAccountResource(
    GettableMixin[AdAccount, AdAccountCreate, AdAccountUpdate],
    UpdatableMixin[AdAccount, AdAccountCreate, AdAccountUpdate],
    V1Resource[AdAccount, AdAccountCreate, AdAccountUpdate],
):
    """Ad accounts: ``/ad-accounts`` plus the ``GET /me`` identity call.

    ``get()`` and ``update()`` require the client to have an
    ``ad_account_id`` (they send ``X-AP-Context``); ``create()`` and
    ``me()`` work without one, so a fresh org can bootstrap its first
    ad account.

    There is no list endpoint under ``/ad-accounts``; enumerate the
    caller's accessible accounts via :class:`AclResource`.
    """

    base_path = "ad-accounts"
    model_class = AdAccount
    requires_account_context = True

    def __init__(self, client: "AppleAdsClient") -> None:
        """Initialize the resource and its context-free sibling.

        Args:
            client: The parent AppleAdsClient instance.
        """
        super().__init__(client)
        self._context_free = _ContextFreeAdAccountOps(client)

    def me(self) -> Me:
        """Get the identity of the authenticated API caller.

        Calls ``GET /me``; no account context required.

        Returns:
            The caller's user ID and organization ID.
        """
        data = self._context_free._request("GET", "me")
        return Me.model_validate(data.get("result") or {})

    async def me_async(self) -> Me:
        """Get the identity of the authenticated API caller asynchronously.

        Returns:
            The caller's user ID and organization ID.
        """
        data = await self._context_free._request_async("GET", "me")
        return Me.model_validate(data.get("result") or {})

    def create(self, data: AdAccountCreate) -> AdAccount:
        """Create a new ad account under the caller's organization.

        Calls ``POST /ad-accounts``; no account context required. The
        account inherits ``currency``, ``timezone``, and
        ``paymentModel`` from the parent org, immutably.

        Args:
            data: The creation data (``name`` and ``product_features``
                required).

        Returns:
            The created ad account. Check ``system_status_reasons`` if
            ``system_status`` is ``INACTIVE``.

        Raises:
            ValidationError: If the data is invalid.
        """
        response = self._context_free._request("POST", "ad-accounts", json=self._dump(data))
        return self._parse_item(response)

    async def create_async(self, data: AdAccountCreate) -> AdAccount:
        """Create a new ad account asynchronously.

        Args:
            data: The creation data.

        Returns:
            The created ad account.

        Raises:
            ValidationError: If the data is invalid.
        """
        response = await self._context_free._request_async(
            "POST", "ad-accounts", json=self._dump(data)
        )
        return self._parse_item(response)


class AclResource(V1Resource[UserAcl, UserAcl, UserAcl]):
    """Access control lists: ``GET /acls``.

    The recommended session-start discovery call: returns the ad
    accounts and roles accessible to the authenticated caller. No
    account context required.
    """

    base_path = "acls"
    model_class = UserAcl
    requires_account_context = False

    # list_async is defined before list: once ``list`` binds in class
    # scope it shadows the builtin in later annotation evaluation.
    async def list_async(self) -> list[UserAcl]:
        """List the caller's accessible ad accounts asynchronously.

        Returns:
            One ACL entry per accessible ad account.
        """
        data = await self._request_async("GET")
        result = UserAccessResult.model_validate(data.get("result") or {})
        return result.acls or []

    def list(self) -> list[UserAcl]:
        """List the ad accounts and roles accessible to the caller.

        Returns:
            One ACL entry per accessible ad account.
        """
        data = self._request("GET")
        result = UserAccessResult.model_validate(data.get("result") or {})
        return result.acls or []


class OrgResource(GettableMixin[Org, Org, Org], V1Resource[Org, Org, Org]):
    """Organizations: ``GET /orgs/{id}``.

    Get the organization ID from ``client.ad_accounts.me()``. No account
    context required.
    """

    base_path = "orgs"
    model_class = Org
    requires_account_context = False


class AdvertiserResourceResource(V1Resource[Delegation, Delegation, Delegation]):
    """Advertiser resources: ``GET /advertiser-resources``.

    Lists the brands and content providers available across the
    organization that can be delegated to an ad account. No account
    context required.
    """

    base_path = "advertiser-resources"
    model_class = Delegation
    requires_account_context = False

    # list_async is defined before list: once ``list`` binds in class
    # scope it shadows the builtin in later annotation evaluation.
    async def list_async(self, resource_type: AdvertiserResourceType | str) -> list[Delegation]:
        """List advertiser resources of the given type asynchronously.

        Args:
            resource_type: The resource type to filter by.

        Returns:
            The matching advertiser resources.
        """
        data = await self._request_async("GET", params={"resourceType": str(resource_type)})
        return [Delegation.model_validate(item) for item in data.get("result") or []]

    def list(self, resource_type: AdvertiserResourceType | str) -> list[Delegation]:
        """List advertiser resources of the given type.

        Args:
            resource_type: The resource type to filter by (required by
                the API): ``CONTENT_PROVIDER`` or ``BUSINESS_BRAND``.

        Returns:
            The matching advertiser resources.
        """
        data = self._request("GET", params={"resourceType": str(resource_type)})
        return [Delegation.model_validate(item) for item in data.get("result") or []]
