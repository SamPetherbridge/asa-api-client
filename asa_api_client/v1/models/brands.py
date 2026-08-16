"""Models for the Apple Ads Platform API v1 brands group.

Covers the "Ads on Apple Maps" business domain: brands, business
categories (Apple Maps taxonomy), physical locations, location groups
for geographic targeting, and brand rejection reasons (policy
assignments). Brands, categories, and locations are read-only —
sourced from Apple Maps / Apple Business Connect; location groups are
the only writable resource in this group.

A brand's ``id`` doubles as the ``promotedObjectId`` when creating
``BUSINESS_BRAND`` campaigns.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class EligibilityStatus(StrEnum):
    """Ad-serving eligibility status of a business-domain entity."""

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    LIMITED = "LIMITED"
    PENDING = "PENDING"
    UNDEFINED = "UNDEFINED"


class LocationStatus(StrEnum):
    """Operational status of a physical business location."""

    OPEN = "OPEN"
    OPENING_SOON = "OPENING_SOON"
    CLOSED = "CLOSED"
    MOVED = "MOVED"
    TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"


class LocationGroupType(StrEnum):
    """Membership model of a location group.

    ``STATIC`` groups list explicit ``locationIds``; ``DYNAMIC`` groups
    derive membership from ``rules`` evaluated against the brand's full
    location catalog.
    """

    STATIC = "STATIC"
    DYNAMIC = "DYNAMIC"


class LocationGroupSystemStatus(StrEnum):
    """System-evaluated lifecycle status of a location group."""

    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"
    DELETED = "DELETED"


class RuleField(StrEnum):
    """Field a dynamic location-group rule filters on.

    ``ADMIN_AREA`` values are full English state/province names
    ("Illinois", never "IL"). ``LOCALITY`` values are pipe-delimited
    ``countryOrRegion|adminArea|locality`` strings, e.g.
    ``"US|New York|Brooklyn"``.
    """

    ADMIN_AREA = "adminArea"
    LOCALITY = "locality"
    POSTAL_CODE = "postalCode"
    LOCATION_ID = "locationId"


class RuleOperator(StrEnum):
    """Comparison operator of a dynamic location-group rule."""

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"
    NOT_IN = "NOT_IN"


class ConstraintGroup(V1Model):
    """Supply placements and markets scoping an eligibility rule.

    When both fields are populated the constraint applies to their
    intersection.

    Attributes:
        supply_placement: Supply placement identifiers (open string
            set; e.g. ``MAPS_SEARCH_RESULTS``, ``SEARCH_TAB``).
        country_or_region: ISO 3166-1 alpha-2 country codes.
    """

    supply_placement: list[str] | None = Field(default=None, alias="supplyPlacement")
    country_or_region: list[str] | None = Field(default=None, alias="countryOrRegion")


class Eligibility(V1Model):
    """Eligibility status and constraints of a business-domain entity.

    Attributes:
        status: The overall eligibility status.
        blocked_groups: Placements/markets where serving is blocked.
        allowed_groups: Placements/markets where serving is allowed.
        modification_time: Timestamp of the last eligibility evaluation.
    """

    status: EligibilityStatus | None = None
    blocked_groups: list[ConstraintGroup] | None = Field(default=None, alias="blockedGroups")
    allowed_groups: list[ConstraintGroup] | None = Field(default=None, alias="allowedGroups")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class Brand(V1Model):
    """A brand eligible for promotion through Apple Maps ads.

    Read-only, sourced from Apple registration. Use ``id`` as the
    campaign ``promotedObjectId`` for ``BUSINESS_BRAND`` campaigns;
    only brands with ``eligibility.status: ELIGIBLE`` can be promoted.

    Attributes:
        id: The brand identifier (equals the campaign promotedObjectId).
        name: Primary display name.
        country_or_region: ISO 3166-1 alpha-2 code of the primary market.
        categories: Category taxonomy identifiers; first is primary.
        eligibility: Ad-serving eligibility.
        creation_time: When the brand record was created.
        modification_time: When the brand record last changed.
    """

    id: str
    name: str | None = None
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    categories: list[str] | None = None
    eligibility: Eligibility | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class BusinessCategory(V1Model):
    """A category in the Apple Maps business taxonomy. Read-only.

    Attributes:
        id: The MUID (Maps Unique Identifier).
        name: English display name.
        qualified_id: Dot-delimited taxonomy path (e.g.
            ``"dining.restaurant"``); used as the ``text`` of
            ``CATEGORY`` match-type keywords.
        description: Human-readable description.
        eligibility: Ad-serving eligibility; only ``ELIGIBLE``
            categories can be used in active Apple Maps campaigns.
        creation_time: When the category record was created.
        modification_time: When the category record last changed.
    """

    id: str
    name: str | None = None
    qualified_id: str | None = Field(default=None, alias="qualifiedId")
    description: str | None = None
    eligibility: Eligibility | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class BrandRejectionReason(V1Model):
    """A policy assignment with rejection details for a brand entity.

    Read-only; documented as ``BrandRejectionReasonResponse``. Returned
    by the rejection-reasons query for brands.

    Attributes:
        id: Policy assignment identifier (an integer, unlike the
            string IDs elsewhere in this group).
        promoted_object_id: The brand / promoted object identifier.
        promoted_object_type: Promoted object type (e.g.
            ``BUSINESS_BRAND``; not a documented closed enum).
        entity_id: Identifier of the affected entity.
        entity_type: Type of the affected entity.
        component_type: Component that triggered the policy (e.g.
            ``ENTITY_ASSET``).
        component: Identifier of the specific component (e.g. an asset
            UUID).
        code: Rejection reason code (e.g. ``PERSONAL_INFORMATION``).
        title: Human-readable title.
        body: Detailed explanation.
    """

    id: int | None = None
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    promoted_object_type: str | None = Field(default=None, alias="promotedObjectType")
    entity_id: str | None = Field(default=None, alias="entityId")
    entity_type: str | None = Field(default=None, alias="entityType")
    component_type: str | None = Field(default=None, alias="componentType")
    component: str | None = None
    code: str | None = None
    title: str | None = None
    body: str | None = None


class LocationAddress(V1Model):
    """Postal address of a location, sourced from Apple Maps. Read-only.

    Attributes:
        country_or_region: ISO 3166-1 alpha-2 code (e.g. ``"US"``).
        admin_area: State/province full name (e.g. ``"California"``).
        admin_area_code: Abbreviated code (e.g. ``"CA"``).
        locality: City or town name.
        sub_locality: Neighborhood/district within a city.
        sub_admin_area: County / sub-administrative area.
        postal_code: Postal or ZIP code.
        thoroughfare: Street name.
        sub_thoroughfare: Street number.
        full_thoroughfare: Combined street number and street name.
        full_address: Complete formatted address string.
        unit: Unit designation (e.g. ``"Suite 100"``).
        floor: Floor designation.
        building: Building name.
        dependent_locality: Additional locality components.
    """

    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    admin_area: str | None = Field(default=None, alias="adminArea")
    admin_area_code: str | None = Field(default=None, alias="adminAreaCode")
    locality: str | None = None
    sub_locality: str | None = Field(default=None, alias="subLocality")
    sub_admin_area: str | None = Field(default=None, alias="subAdminArea")
    postal_code: str | None = Field(default=None, alias="postalCode")
    thoroughfare: str | None = None
    sub_thoroughfare: str | None = Field(default=None, alias="subThoroughfare")
    full_thoroughfare: str | None = Field(default=None, alias="fullThoroughfare")
    full_address: str | None = Field(default=None, alias="fullAddress")
    unit: str | None = None
    floor: str | None = None
    building: str | None = None
    dependent_locality: list[str] | None = Field(default=None, alias="dependentLocality")


class LocationDisplayPoint(V1Model):
    """Coordinates for map placement rendering. Read-only.

    Attributes:
        latitude: Latitude as a string (e.g. ``"37.3318"``).
        longitude: Longitude as a string (e.g. ``"-122.0312"``).
    """

    latitude: str | None = None
    longitude: str | None = None


class Location(V1Model):
    """A physical place of business sourced from Apple Maps. Read-only.

    Only ``status: OPEN`` locations can be added to location groups and
    targeted; only ``eligibility.status: ELIGIBLE`` locations can be
    assigned to ad group targeting.

    Attributes:
        id: The location identifier (used in targeting).
        brand_id: Associated brand identifier.
        status: Operational status of the location.
        name: Display name.
        categories: Category identifiers; first is primary.
        address: Postal address, sourced from Apple Maps.
        display_point: Coordinates for map placement rendering.
        country_or_region: ISO 3166-1 alpha-2 code (also present inside
            ``address``).
        creation_time: When the location record was created.
        modification_time: When the location record last changed.
        eligibility: Ad-serving eligibility.
    """

    id: str
    brand_id: str | None = Field(default=None, alias="brandId")
    status: LocationStatus | None = None
    name: str | None = None
    categories: list[str] | None = None
    address: LocationAddress | None = None
    display_point: LocationDisplayPoint | None = Field(default=None, alias="displayPoint")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    eligibility: Eligibility | None = None


class Rule(V1Model):
    """A single membership filter rule for a DYNAMIC location group.

    Attributes:
        field: Location field the rule filters on.
        operator: Comparison operator.
        value: A string for ``EQUALS``/``NOT_EQUALS``; a list of
            strings for ``IN``/``NOT_IN``.
    """

    field: RuleField
    operator: RuleOperator
    value: str | list[str]


class LocationGroup(V1Model):
    """A collection of business locations used for geo targeting.

    Belongs to exactly one brand and one ad account, both fixed at
    creation. Groups in ``INVALID`` or ``PENDING`` system status cannot
    be updated or deleted.

    Attributes:
        id: System-assigned identifier. Read-only.
        name: Display name.
        brand_id: Owning brand; immutable after creation.
        ad_account_id: Owning ad account; immutable after creation.
        group_type: Membership model; immutable after creation.
        system_status: System-evaluated lifecycle status. Read-only.
        rules: Membership criteria for ``DYNAMIC`` groups.
        query: Server-generated RSQL string derived from ``rules``.
            Read-only.
        location_ids: Explicit membership for ``STATIC`` groups.
        is_all_locations_group: True for the system-created
            "All Locations" group of a brand. Read-only.
        description: Optional description.
        group_total: Total locations in the group. Read-only.
        eligibility: Ad-serving eligibility. Read-only.
        creation_time: When the group was created. Read-only.
        modification_time: When the group last changed. Read-only.
    """

    id: str
    name: str
    brand_id: str | None = Field(default=None, alias="brandId")
    ad_account_id: str | None = Field(default=None, alias="adAccountId")
    group_type: LocationGroupType = Field(alias="groupType")
    system_status: LocationGroupSystemStatus | None = Field(default=None, alias="systemStatus")
    rules: list[Rule] | None = None
    query: str | None = None
    location_ids: list[str] | None = Field(default=None, alias="locationIds")
    is_all_locations_group: bool | None = Field(default=None, alias="isAllLocationsGroup")
    description: str | None = None
    group_total: int = Field(default=0, alias="groupTotal")
    eligibility: Eligibility | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class LocationGroupCreate(V1Model):
    """Creation payload for a location group (sent bare, unwrapped).

    ``STATIC`` groups require at least one entry in ``location_ids``;
    ``DYNAMIC`` groups require at least one entry in ``rules``.

    Attributes:
        name: Display name.
        brand_id: Owning brand; immutable afterward.
        ad_account_id: Owning ad account; immutable afterward.
        group_type: Membership model; immutable afterward.
        rules: Membership criteria (``DYNAMIC`` groups).
        location_ids: Explicit membership (``STATIC`` groups).
        description: Optional description.
    """

    name: str
    brand_id: str = Field(alias="brandId")
    ad_account_id: str = Field(alias="adAccountId")
    group_type: LocationGroupType = Field(alias="groupType")
    rules: list[Rule] | None = None
    location_ids: list[str] | None = Field(default=None, alias="locationIds")
    description: str | None = None


class LocationGroupUpdate(V1Model):
    """Update payload for a location group (sent bare, unwrapped).

    Omitted fields keep their current values, but ``rules`` and
    ``location_ids`` are full replacements of the existing arrays —
    send the complete desired state, not a diff.

    Attributes:
        name: Updated display name.
        group_type: Present in the API schema but documented as
            immutable after creation — delete and recreate to switch.
        rules: Replaces existing rules entirely; transitions the
            group's system status to ``PENDING``.
        location_ids: Replaces the existing list entirely.
        description: Updated description.
    """

    name: str | None = None
    group_type: LocationGroupType | None = Field(default=None, alias="groupType")
    rules: list[Rule] | None = None
    location_ids: list[str] | None = Field(default=None, alias="locationIds")
    description: str | None = None
