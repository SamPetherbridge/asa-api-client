"""Models for the Apple Ads Platform API v1 geo targeting search endpoints.

Geo targeting metadata lives under ``/v1/search/geo``: GET searches
locations by name, POST batch-resolves known IDs. Both return
``SearchEntity`` rows whose numeric ``id`` is the value used in ad
group ``targetingDimensions``.
"""

from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class GeoEntityType(StrEnum):
    """The type of a geographic targeting entity.

    Note:
        Values are CamelCase (``Country``, ``AdminArea``, ...) unlike
        the SCREAMING_SNAKE style used elsewhere in the API.
    """

    COUNTRY = "Country"
    ADMIN_AREA = "AdminArea"
    LOCALITY = "Locality"
    POSTAL_CODE = "PostalCode"


class SearchSupplySourceType(StrEnum):
    """The supply source scoping a geo search.

    ``APPSTORE`` excludes ``PostalCode`` entities; ``MAPS`` excludes
    ``Country`` entities and only covers the US and Canada.
    """

    APPSTORE = "APPSTORE"
    MAPS = "MAPS"


class GeoBlockedReason(StrEnum):
    """Reason codes restricting a geo for a supply source.

    Hard-block reasons (always filtered out of search results):
    ``NO_MUID``, ``NOT_SUPPORTED``, ``SOURCE_REMOVED``,
    ``COUNTRY_NOT_SUPPORTED``, ``COUNTRY_NOT_SEARCHABLE``,
    ``MAPS_SOURCE_NOT_MATCHED``. Soft-block reasons (included unless
    ``eligible=true``): ``LOCALITY_LOW_SEARCH_VOLUME``,
    ``POSTAL_CODE_SPARSE``.
    """

    NO_MUID = "NO_MUID"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    SOURCE_REMOVED = "SOURCE_REMOVED"
    COUNTRY_NOT_SUPPORTED = "COUNTRY_NOT_SUPPORTED"
    COUNTRY_NOT_SEARCHABLE = "COUNTRY_NOT_SEARCHABLE"
    MAPS_SOURCE_NOT_MATCHED = "MAPS_SOURCE_NOT_MATCHED"
    LOCALITY_LOW_SEARCH_VOLUME = "LOCALITY_LOW_SEARCH_VOLUME"
    POSTAL_CODE_SPARSE = "POSTAL_CODE_SPARSE"


class GeoBlockedGroup(V1Model):
    """A blocking rule restricting a geo for one or more supply sources.

    Attributes:
        supply_source: The supply sources this restriction applies to.
        reasons: The reason codes for the restriction.
    """

    supply_source: list[SearchSupplySourceType] | None = Field(default=None, alias="supplySource")
    reasons: list[GeoBlockedReason] | None = None


class GeoEligibility(V1Model):
    """Eligibility restrictions on a geo, scoped to the request's supply source.

    The whole object is absent from a response when no restrictions
    apply; when present, ``blocked_groups`` is always non-empty.

    Attributes:
        blocked_groups: The blocking rules matching the requested
            supply source.
    """

    blocked_groups: list[GeoBlockedGroup] | None = Field(default=None, alias="blockedGroups")


class SearchEntity(V1Model):
    """A single geographic location search result.

    Attributes:
        id: Numeric geo location identifier as a string (e.g.
            ``"11390462"``); the value used in ad group targeting.
        legacy_id: Pipe-delimited hierarchy code (e.g.
            ``US|CA|San Francisco``).
        entity: The geo entity type.
        display_name: Localized full-hierarchy name.
        country_or_region: ISO 3166-1 alpha-2 country code.
        admin_area: State/province identifier (AdminArea, Locality,
            and PostalCode entities).
        locality: City name (Locality entities only).
        postal_code: Postal code value (PostalCode entities only).
        eligibility: Restrictions scoped to the requested supply
            source; None means no restrictions apply.
    """

    id: str | None = None
    legacy_id: str | None = Field(default=None, alias="legacyId")
    entity: GeoEntityType | None = None
    display_name: str | None = Field(default=None, alias="displayName")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    admin_area: str | None = Field(default=None, alias="adminArea")
    locality: str | None = None
    postal_code: str | None = Field(default=None, alias="postalCode")
    eligibility: GeoEligibility | None = None


class GeoSearchPagination(V1Model):
    """Pagination for geo search requests and responses.

    Attributes:
        total_count: Total matching results (response only).
        offset: Zero-based index of the first result. Default 0.
        page_size: Maximum results per page. Default 20.
    """

    total_count: int | None = Field(default=None, alias="totalCount")
    offset: int | None = None
    page_size: int | None = Field(default=None, alias="pageSize")


class GeoRequest(V1Model):
    """A single geo entity lookup criterion for the batch POST endpoint.

    Exactly one of ``id`` or ``legacy_id`` must be provided.

    Attributes:
        id: Numeric-string geo location identifier. Mutually exclusive
            with ``legacy_id``.
        legacy_id: Pipe-delimited hierarchy code (e.g.
            ``US|CA|San Francisco``). Mutually exclusive with ``id``.
        entity: The geo entity type (required).
    """

    id: str | None = None
    legacy_id: str | None = Field(default=None, alias="legacyId")
    entity: GeoEntityType


class GeoSearchPostRequest(V1Model):
    """The request body for ``POST /v1/search/geo`` batch lookups.

    Attributes:
        geo_request: One entry per geo entity to look up; results are
            deduplicated across requested entities.
        supply_source: The supply source scope (``APPSTORE`` or
            ``MAPS``).
        pagination: Optional pagination; the API defaults to
            ``{offset: 0, pageSize: 20}`` when omitted.
    """

    geo_request: list[GeoRequest] = Field(alias="geoRequest")
    supply_source: SearchSupplySourceType = Field(alias="supplySource")
    pagination: GeoSearchPagination | None = None
