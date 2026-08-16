"""Resources for the Apple Ads Platform API v1 brands group.

Covers the "Ads on Apple Maps" business domain: brands
(``/business-brands``), business categories (``/business-categories``),
brand rejection reasons (``/rejection-reasons/business-brands``),
locations (``/locations``), and location groups (``/location-groups``).

Brands, categories, locations, and rejection reasons are read-only;
location groups are the only writable resource. Every endpoint in this
group requires the ad-account context header.
"""

from asa_api_client.v1.models.brands import (
    Brand,
    BrandRejectionReason,
    BusinessCategory,
    Location,
    LocationGroup,
    LocationGroupCreate,
    LocationGroupUpdate,
)
from asa_api_client.v1.resources.base import (
    CreatableMixin,
    DeletableMixin,
    GettableMixin,
    QueryableMixin,
    UpdatableMixin,
    V1Resource,
)


class BrandResource(
    GettableMixin[Brand, Brand, Brand],
    QueryableMixin[Brand, Brand, Brand],
    V1Resource[Brand, Brand, Brand],
):
    """Read-only access to brands promotable through Apple Maps ads.

    A brand's ``id`` is the ``promotedObjectId`` used when creating
    ``BUSINESS_BRAND`` campaigns; only brands with
    ``eligibility.status: ELIGIBLE`` can be promoted.

    Example:
        Look up a brand and its eligibility::

            brand = client.brands.get("brand-id")
            print(brand.eligibility.status)
    """

    base_path = "business-brands"
    model_class = Brand


class BusinessCategoryResource(
    GettableMixin[BusinessCategory, BusinessCategory, BusinessCategory],
    QueryableMixin[BusinessCategory, BusinessCategory, BusinessCategory],
    V1Resource[BusinessCategory, BusinessCategory, BusinessCategory],
):
    """Read-only access to the Apple Maps business category taxonomy.

    Category ``qualifiedId`` values (e.g. ``"dining.restaurant"``) are
    used as the ``text`` of ``CATEGORY`` match-type keywords; only
    ``ELIGIBLE`` categories can be used in active Apple Maps campaigns.
    """

    base_path = "business-categories"
    model_class = BusinessCategory


class BrandRejectionReasonResource(
    QueryableMixin[BrandRejectionReason, BrandRejectionReason, BrandRejectionReason],
    V1Resource[BrandRejectionReason, BrandRejectionReason, BrandRejectionReason],
):
    """Query-only access to policy rejection reasons for brands.

    Returns only non-deleted rejection reasons by default; filter by
    ``promotedObjectId`` to scope to a specific brand, or add a
    ``deleted EQUALS true`` filter to include soft-deleted records.

    Example:
        Find why a brand's assets were rejected::

            page = client.brand_rejection_reasons.query(
                Query().where("promotedObjectId", "EQUALS", "brand-id")
            )
    """

    base_path = "rejection-reasons/business-brands"
    model_class = BrandRejectionReason


class LocationResource(
    GettableMixin[Location, Location, Location],
    QueryableMixin[Location, Location, Location],
    V1Resource[Location, Location, Location],
):
    """Read-only access to physical business locations from Apple Maps.

    Always filter queries by ``brandId``, otherwise results span every
    brand in the ad account. Only ``status: OPEN`` locations can be
    added to location groups and targeted.
    """

    base_path = "locations"
    model_class = Location


class LocationGroupResource(
    GettableMixin[LocationGroup, LocationGroupCreate, LocationGroupUpdate],
    QueryableMixin[LocationGroup, LocationGroupCreate, LocationGroupUpdate],
    CreatableMixin[LocationGroup, LocationGroupCreate, LocationGroupUpdate],
    UpdatableMixin[LocationGroup, LocationGroupCreate, LocationGroupUpdate],
    DeletableMixin[LocationGroup, LocationGroupCreate, LocationGroupUpdate],
    V1Resource[LocationGroup, LocationGroupCreate, LocationGroupUpdate],
):
    """Full CRUD access to location groups for geographic targeting.

    Deletion is soft: the API returns the group envelope with
    ``systemStatus: DELETED``, and deleted groups stay fetchable by ID.
    Updates replace ``rules``/``locationIds`` arrays entirely — send
    the complete desired state. Groups in ``INVALID`` or ``PENDING``
    system status cannot be updated or deleted.

    Example:
        Create a static group of two stores::

            group = client.location_groups.create(
                LocationGroupCreate(
                    name="Bay Area Stores",
                    brand_id="brand-id",
                    ad_account_id="12345",
                    group_type=LocationGroupType.STATIC,
                    location_ids=["loc-1", "loc-2"],
                )
            )
    """

    base_path = "location-groups"
    model_class = LocationGroup
