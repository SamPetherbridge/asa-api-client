"""Models for the Apple Ads Platform API v1 account-management surface.

Covers the data objects behind caller identity (``GET /me``), access
control (``GET /acls``), organizations (``GET /orgs/{id}``), ad accounts
(``POST /ad-accounts``, ``GET/PUT /ad-accounts/{id}``), and advertiser
resources (``GET /advertiser-resources``).
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class AdAccountCurrency(StrEnum):
    """Supported currencies for ad accounts and organizations.

    Inherited from the parent organization at ad-account creation and
    read-only afterward. The docs list the same value set for both
    ``AdAccount.currency`` and ``Org.currency``.
    """

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    AUD = "AUD"
    CAD = "CAD"
    MXN = "MXN"
    NZD = "NZD"
    RUB = "RUB"
    CNY = "CNY"
    RMB = "RMB"
    INR = "INR"
    BRL = "BRL"
    IDR = "IDR"


class PaymentModel(StrEnum):
    """Payment model of an organization or ad account.

    Attributes:
        LOC: Line of credit; enables budget orders, invoiced monthly.
        PAYG: Pay as you go; charged per campaign spend.
    """

    LOC = "LOC"
    PAYG = "PAYG"


class ProductFeatures(StrEnum):
    """Advertising capabilities of an ad account.

    Required on :class:`AdAccountCreate` and immutable after creation.
    An ad account gets exactly one surface (App Store or Apple Maps).

    Attributes:
        APPSTORE_APP_MANUAL: Authorizes App Store advertising; requires
            a ``CONTENT_PROVIDER`` delegation.
        BUSINESS_BRAND_MANUAL: Authorizes Apple Maps advertising;
            requires a ``BUSINESS_BRAND`` delegation.
    """

    APPSTORE_APP_MANUAL = "APPSTORE_APP_MANUAL"
    BUSINESS_BRAND_MANUAL = "BUSINESS_BRAND_MANUAL"


class AdvertiserResourceType(StrEnum):
    """Type of an advertiser resource (and delegation resource type).

    Attributes:
        CONTENT_PROVIDER: A content provider; ``resourceId`` is the
            Content Provider ID (CPID).
        BUSINESS_BRAND: A brand delegated from an organization;
            ``resourceId`` is the Brand ID.
    """

    CONTENT_PROVIDER = "CONTENT_PROVIDER"
    BUSINESS_BRAND = "BUSINESS_BRAND"


class AdAccountSystemStatus(StrEnum):
    """System status of an ad account.

    Attributes:
        ACTIVE: The ad account is active and capable of running campaigns.
        INACTIVE: The ad account is inactive; check ``systemStatusReasons``.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AdAccountSystemStatusReason(StrEnum):
    """Reasons an ad account's system status can be ``INACTIVE``.

    A superset of :class:`OrgSystemStatusReason`, adding
    ``INVALID_PAYMENT_PROFILE`` and ``ORG_NO_PAYMENT_METHOD_ON_FILE``.
    """

    CHARGE_BACK_DISPUTED = "CHARGE_BACK_DISPUTED"
    CREDIT_CARD_SUSPENDED = "CREDIT_CARD_SUSPENDED"
    ORG_PAYMENT_TYPE_DECLINED = "ORG_PAYMENT_TYPE_DECLINED"
    FRAUD = "FRAUD"
    INVALID_PAYMENT_PROFILE = "INVALID_PAYMENT_PROFILE"
    MSA_EXPIRED = "MSA_EXPIRED"
    MSA_NOT_RECEIVED = "MSA_NOT_RECEIVED"
    NO_PAYMENT_METHOD_ON_FILE = "NO_PAYMENT_METHOD_ON_FILE"
    ORG_NO_PAYMENT_METHOD_ON_FILE = "ORG_NO_PAYMENT_METHOD_ON_FILE"
    PAYMENT_DECLINED = "PAYMENT_DECLINED"
    PAYMENT_METHOD_CANCELED = "PAYMENT_METHOD_CANCELED"
    PAYMENT_METHOD_ON_HOLD = "PAYMENT_METHOD_ON_HOLD"
    PAYMENT_PENDING_CHARGES = "PAYMENT_PENDING_CHARGES"
    LOC_EXHAUSTED = "LOC_EXHAUSTED"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    TAX_VERIFICATION_PENDING = "TAX_VERIFICATION_PENDING"
    TERM_NOT_ACCEPTED = "TERM_NOT_ACCEPTED"
    USER_REQUESTED_ACCOUNT_SUSPENSION = "USER_REQUESTED_ACCOUNT_SUSPENSION"


class OrgSystemStatus(StrEnum):
    """System status of an organization.

    Attributes:
        ACTIVE: The organization is active and operational.
        INACTIVE: The organization is inactive; check ``systemStatusReasons``.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class OrgSystemStatusReason(StrEnum):
    """Reasons an organization's system status can be ``INACTIVE``."""

    CHARGE_BACK_DISPUTED = "CHARGE_BACK_DISPUTED"
    CREDIT_CARD_SUSPENDED = "CREDIT_CARD_SUSPENDED"
    ORG_PAYMENT_TYPE_DECLINED = "ORG_PAYMENT_TYPE_DECLINED"
    FRAUD = "FRAUD"
    LOC_EXHAUSTED = "LOC_EXHAUSTED"
    MSA_EXPIRED = "MSA_EXPIRED"
    MSA_NOT_RECEIVED = "MSA_NOT_RECEIVED"
    NO_PAYMENT_METHOD_ON_FILE = "NO_PAYMENT_METHOD_ON_FILE"
    PAYMENT_DECLINED = "PAYMENT_DECLINED"
    PAYMENT_METHOD_CANCELED = "PAYMENT_METHOD_CANCELED"
    PAYMENT_METHOD_ON_HOLD = "PAYMENT_METHOD_ON_HOLD"
    PAYMENT_PENDING_CHARGES = "PAYMENT_PENDING_CHARGES"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    TAX_VERIFICATION_PENDING = "TAX_VERIFICATION_PENDING"
    TERM_NOT_ACCEPTED = "TERM_NOT_ACCEPTED"
    USER_REQUESTED_ACCOUNT_SUSPENSION = "USER_REQUESTED_ACCOUNT_SUSPENSION"


class Me(V1Model):
    """Identity of the authenticated API caller (``GET /me``).

    Attributes:
        user_id: User ID of the authenticated user.
        org_id: Organization ID of the authenticated user.
    """

    user_id: int | None = Field(default=None, alias="userId")
    org_id: int | None = Field(default=None, alias="orgId")


class Delegation(V1Model):
    """A resource delegated to an ad account.

    Appears in ``AdAccount.delegations`` and as the items returned by
    ``GET /advertiser-resources``.

    Attributes:
        resource_id: CPID for ``CONTENT_PROVIDER``; Brand ID for
            ``BUSINESS_BRAND``. A string, not an integer.
        resource_type: The type of the delegated resource.
        resource_name: Display name of the delegated resource.
    """

    resource_id: str | None = Field(default=None, alias="resourceId")
    resource_type: AdvertiserResourceType | None = Field(default=None, alias="resourceType")
    resource_name: str | None = Field(default=None, alias="resourceName")


class DelegationCreate(V1Model):
    """A delegation entry in an :class:`AdAccountCreate` request.

    Attributes:
        resource_id: CPID for ``CONTENT_PROVIDER``; Brand ID for
            ``BUSINESS_BRAND``. Required, minimum length 1.
        resource_type: The type of resource to delegate. Must match the
            account's ``productFeatures`` surface.
    """

    resource_id: str = Field(alias="resourceId", min_length=1)
    resource_type: AdvertiserResourceType = Field(alias="resourceType")


class DelegationUpdate(V1Model):
    """A delegation entry in an :class:`AdAccountUpdate` request.

    The schema marks both fields optional, but the endpoint docs require
    both on every included entry. All delegations on an ad account must
    share the same ``resource_type``.

    Attributes:
        resource_id: CPID for ``CONTENT_PROVIDER``; Brand ID for
            ``BUSINESS_BRAND``.
        resource_type: The type of the delegated resource.
    """

    resource_id: str | None = Field(default=None, alias="resourceId")
    resource_type: AdvertiserResourceType | None = Field(default=None, alias="resourceType")


class AclAdAccount(V1Model):
    """Slim ad-account projection returned inside ACL entries.

    Attributes:
        id: Unique identifier for the ad account.
        name: Name of the ad account.
        org_id: Organization the ad account belongs to.
    """

    id: int | None = None
    name: str | None = None
    org_id: int | None = Field(default=None, alias="orgId")


class UserAcl(V1Model):
    """An access control entry for a single ad account (``GET /acls``).

    Attributes:
        ad_account: The ad account this ACL entry belongs to.
        roles: Role names for this ad account (e.g. ``"Admin"``,
            ``"API Account Manager"``). Assigned in the Apple Ads UI.
    """

    ad_account: AclAdAccount | None = Field(default=None, alias="adAccount")
    roles: list[str] | None = None


class UserAccessResult(V1Model):
    """The ``result`` payload of ``GET /acls``.

    Attributes:
        acls: One entry per ad account the caller has access to.
    """

    acls: list[UserAcl] | None = None


class Org(V1Model):
    """An organization: the top-level entity owning ad accounts.

    Attributes:
        id: Unique identifier for the organization.
        name: Organization name.
        currency: Currency of the organization.
        timezone: Timezone of the organization.
        payment_model: ``LOC`` or ``PAYG``.
        system_status: ``ACTIVE`` or ``INACTIVE``.
        system_status_reasons: Populated when the org is ``INACTIVE``.
    """

    id: int | None = None
    name: str | None = None
    currency: AdAccountCurrency | None = None
    timezone: str | None = None
    payment_model: PaymentModel | None = Field(default=None, alias="paymentModel")
    system_status: OrgSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[OrgSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )


class AdAccount(V1Model):
    """An ad account: the account-level container for campaigns.

    Each ad account belongs to exactly one organization (immutably) and
    is authorized for App Store OR Apple Maps advertising, never both.

    Attributes:
        id: System-assigned unique identifier. Read-only.
        name: Display name, unique within the parent org. Mutable.
        org_id: Parent organization ID. Read-only.
        timezone: Inherited from the parent org at creation. Read-only.
        currency: Inherited from the parent org at creation. Read-only.
        payment_model: Inherited from the parent org. Read-only.
        system_status: ``ACTIVE`` or ``INACTIVE``. Read-only.
        system_status_reasons: Populated when ``system_status`` is
            ``INACTIVE``. Read-only.
        delegations: Delegated resources (brands, content providers).
        product_features: Advertising surface set at creation; immutable.
        creation_time: Creation timestamp (no timezone suffix). Read-only.
        modification_time: Last-modified timestamp. Read-only.
    """

    id: int | None = None
    name: str | None = None
    org_id: int | None = Field(default=None, alias="orgId")
    timezone: str | None = None
    currency: AdAccountCurrency | None = None
    payment_model: PaymentModel | None = Field(default=None, alias="paymentModel")
    system_status: AdAccountSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[AdAccountSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    delegations: list[Delegation] | None = None
    product_features: list[ProductFeatures] | None = Field(default=None, alias="productFeatures")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class AdAccountCreate(V1Model):
    """Request body for ``POST /ad-accounts``.

    The new account inherits ``currency``, ``timezone``, and
    ``paymentModel`` from the parent organization at creation time.

    Attributes:
        name: Display name. Required, minimum length 1.
        product_features: Advertising surface — ``APPSTORE_APP_MANUAL``
            or ``BUSINESS_BRAND_MANUAL`` (one, not both). Required.
        delegations: Delegations matching the surface: a
            ``CONTENT_PROVIDER`` entry for App Store, a
            ``BUSINESS_BRAND`` entry for Apple Maps.
    """

    name: str = Field(min_length=1)
    product_features: list[ProductFeatures] = Field(alias="productFeatures")
    delegations: list[DelegationCreate] | None = None


class AdAccountUpdate(V1Model):
    """Request body for ``PUT /ad-accounts/{id}``.

    Include only the fields to change; omitted fields keep their current
    values. The ``delegations`` array uses full-replacement semantics:
    the array sent becomes the complete delegation set (an empty list
    removes all delegations). The API's update schema also lists
    ``productFeatures``, but it is silently ignored (immutable after
    creation), so this model omits it.

    Attributes:
        name: New display name. Minimum length 1 when provided.
        delegations: Complete replacement delegation set.
    """

    name: str | None = Field(default=None, min_length=1)
    delegations: list[DelegationUpdate] | None = None
