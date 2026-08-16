"""Models for the Apple Ads Platform API v1 creatives and assets resources.

Ad creatives define the visual presentation (pre-tap ``creativeSpec``)
and tap destination (post-tap ``destination``) of an ad. Creatives are
account-level entities independent of campaigns and ad groups; one
creative can be linked to many ads. Assets are unified media entities
(currently images only) referenced from creative specs.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class CreativeType(StrEnum):
    """The type of an ad creative.

    Immutable after creation; determines the shape of ``creativeSpec``
    and the placements the creative is eligible for.
    """

    CUSTOM_PRODUCT_PAGE = "CUSTOM_PRODUCT_PAGE"
    DEFAULT_PRODUCT_PAGE = "DEFAULT_PRODUCT_PAGE"
    LOCAL_ADS_SEARCH_CREATIVE = "LOCAL_ADS_SEARCH_CREATIVE"


class CreativeSystemStatus(StrEnum):
    """System validation status of a creative."""

    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"


class CreativeSystemStatusReason(StrEnum):
    """Reasons accompanying a creative's system status."""

    NEEDS_REVIEW = "NEEDS_REVIEW"
    POLICY_PROHIBITED = "POLICY_PROHIBITED"
    POLICY_UNDEFINED = "POLICY_UNDEFINED"
    PENDING_ASSET_CHECKS = "PENDING_ASSET_CHECKS"
    MISSING_ASSET = "MISSING_ASSET"
    ASSET_DELETED = "ASSET_DELETED"
    FAILED_ASSET_RATIO_COMPATIBILITY = "FAILED_ASSET_RATIO_COMPATIBILITY"
    CREATIVE_ASSET_UNAVAILABLE = "CREATIVE_ASSET_UNAVAILABLE"
    CREATIVE_ASSET_PENDING_AVAILABILITY = "CREATIVE_ASSET_PENDING_AVAILABILITY"
    PRODUCT_PAGE_DELETED = "PRODUCT_PAGE_DELETED"
    PRODUCT_PAGE_HIDDEN = "PRODUCT_PAGE_HIDDEN"
    PRODUCT_PAGE_UNAVAILABLE = "PRODUCT_PAGE_UNAVAILABLE"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    DELETED_BY_USER = "DELETED_BY_USER"


class DestinationType(StrEnum):
    """The post-tap destination type of a creative."""

    APP_STORE_PRODUCT_PAGE = "APP_STORE_PRODUCT_PAGE"
    LOCAL_ADS_PLACECARD = "LOCAL_ADS_PLACECARD"


class CreativeSubtype(StrEnum):
    """Subtype of an Apple Maps (``LOCAL_ADS_SEARCH_CREATIVE``) creative."""

    BUSINESS_LOGO = "BUSINESS_LOGO"
    BUSINESS_ASSET = "BUSINESS_ASSET"


class AssetType(StrEnum):
    """The media type of an asset."""

    IMAGE = "IMAGE"


class ImageType(StrEnum):
    """Image file format of an asset.

    System-inferred, never set by callers. Upload accepts only PNG,
    JPG, and HEIC; the other values appear on assets sourced outside
    the upload path (e.g. App Store Connect).
    """

    JPEG = "JPEG"
    JPG = "JPG"
    PNG = "PNG"
    HEIC = "HEIC"
    HEIF = "HEIF"
    SVG = "SVG"
    WEBP = "WEBP"


class Orientation(StrEnum):
    """Orientation of an image asset."""

    PORTRAIT = "PORTRAIT"
    LANDSCAPE = "LANDSCAPE"
    SQUARE = "SQUARE"


class AssetEligibilityStatus(StrEnum):
    """Eligibility status of an asset.

    Do not use assets with ``INELIGIBLE`` or ``PENDING`` status in any
    ad unit; ``LIMITED`` assets serve only in some placements/markets.
    """

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    LIMITED = "LIMITED"
    PENDING = "PENDING"
    UNDEFINED = "UNDEFINED"


class AssetReference(V1Model):
    """A reference to a unified asset from a creative spec.

    Attributes:
        asset_id: Ads-generated UUID for the unified asset. Must
            reference an existing asset.
        sort_order: Zero-based display order within the creative.
    """

    asset_id: str | None = Field(default=None, alias="assetId")
    sort_order: int | None = Field(default=None, alias="sortOrder")


class LocalizedPromoText(V1Model):
    """Localized promotional text for an Apple Maps creative.

    Attributes:
        promo_text: The promotional text shown to viewers.
    """

    promo_text: str | None = Field(default=None, alias="promoText")


class CreativeSpec(V1Model):
    """The pre-tap visual specification of a creative.

    The shape varies by :class:`CreativeType`: pass an empty spec for
    App Ads types (``DEFAULT_PRODUCT_PAGE``, ``CUSTOM_PRODUCT_PAGE``);
    all fields below are required for ``LOCAL_ADS_SEARCH_CREATIVE``.

    Attributes:
        brand_id: The brand this creative belongs to (Apple Maps).
        creative_subtype: ``BUSINESS_LOGO`` or ``BUSINESS_ASSET``.
        creative_assets: Asset references composing the creative.
        localized_text: Promo text keyed by BCP-47 locale
            (e.g. ``"en-US"``).
        default_locale: Fallback locale when the viewer's locale is
            absent from ``localized_text``.
    """

    brand_id: str | None = Field(default=None, alias="brandId")
    creative_subtype: CreativeSubtype | None = Field(default=None, alias="creativeSubtype")
    creative_assets: list[AssetReference] | None = Field(default=None, alias="creativeAssets")
    localized_text: dict[str, LocalizedPromoText] | None = Field(
        default=None, alias="localizedText"
    )
    default_locale: str | None = Field(default=None, alias="defaultLocale")


class DestinationParameter(V1Model):
    """Parameters qualifying a creative destination.

    Attributes:
        adam_id: App Store app identifier. Required for
            ``APP_STORE_PRODUCT_PAGE`` destinations.
        product_page_id: Custom Product Page UUID from App Store
            Connect. Omit for the default product page.
    """

    adam_id: str | None = Field(default=None, alias="adamId")
    product_page_id: str | None = Field(default=None, alias="productPageId")


class Destination(V1Model):
    """The post-tap destination of a creative, as returned by the API.

    Attributes:
        destination_type: The destination type. Immutable.
        parameters: Destination parameters. Immutable.
        url: Read-only URL computed from type and parameters.
    """

    destination_type: DestinationType | None = Field(default=None, alias="destinationType")
    parameters: DestinationParameter | None = None
    url: str | None = None


class DestinationCreate(V1Model):
    """The post-tap destination in a creative-create request.

    Attributes:
        destination_type: The destination type. Immutable after
            creation.
        parameters: For App Store destinations provide ``adam_id`` and
            optionally ``product_page_id``. Omit entirely for
            ``LOCAL_ADS_PLACECARD``.
    """

    destination_type: DestinationType = Field(alias="destinationType")
    parameters: DestinationParameter | None = None


class CreativeConstraintGroup(V1Model):
    """A supply-placement/country group in creative eligibility.

    Attributes:
        supply_placement: Supply placements the group covers
            (e.g. ``APPSTORE_SEARCH_TAB``).
        country_or_region: ISO country/region codes the group covers.
        reason: Blocking reason; only present on blocked groups
            (e.g. ``APP_NOT_ELIGIBLE``).
    """

    supply_placement: list[str] | None = Field(default=None, alias="supplyPlacement")
    country_or_region: list[str] | None = Field(default=None, alias="countryOrRegion")
    reason: str | None = None


class CreativeEligibility(V1Model):
    """Where a creative is eligible to serve.

    Empty/absent while ``systemStatus`` is ``PENDING``; populated
    after review.

    Attributes:
        status: ``ELIGIBLE`` or ``INELIGIBLE``.
        allowed_groups: Supply sources/placements where eligible.
        blocked_groups: Where not eligible, with a blocking ``reason``.
    """

    status: str | None = None
    allowed_groups: list[CreativeConstraintGroup] | None = Field(
        default=None, alias="allowedGroups"
    )
    blocked_groups: list[CreativeConstraintGroup] | None = Field(
        default=None, alias="blockedGroups"
    )


class Creative(V1Model):
    """An ad creative: visual presentation plus tap destination.

    Attributes:
        id: Primary identifier. Read-only.
        ad_account_id: System-assigned ad account reference. Read-only.
        name: The creative name. Mutable.
        creative_type: The creative type. Immutable after creation.
        creative_spec: Pre-tap spec; empty for product-page types.
        destination: Post-tap destination. Immutable after creation.
        system_status: Review/validation state. Read-only.
        system_status_reasons: Reasons for the system status.
        creation_time: Creation timestamp. Read-only.
        modification_time: Last-modification timestamp. Read-only.
        eligibility: Serving eligibility. Read-only.
        deleted: Soft-delete flag.
    """

    id: int | None = None
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    name: str | None = None
    creative_type: CreativeType | None = Field(default=None, alias="creativeType")
    creative_spec: CreativeSpec | None = Field(default=None, alias="creativeSpec")
    destination: Destination | None = None
    system_status: CreativeSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[CreativeSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    eligibility: CreativeEligibility | None = None
    deleted: bool | None = None


class CreativeCreate(V1Model):
    """Request body for creating an ad creative.

    Attributes:
        name: The creative name.
        creative_type: The creative type; determines the shape of
            ``creative_spec``. Immutable.
        creative_spec: Pass an empty spec for product-page types;
            required for ``LOCAL_ADS_SEARCH_CREATIVE``.
        destination: The post-tap destination. Immutable.
    """

    name: str
    creative_type: CreativeType = Field(alias="creativeType")
    creative_spec: CreativeSpec | None = Field(default=None, alias="creativeSpec")
    destination: DestinationCreate


class CreativeUpdate(V1Model):
    """Request body for updating an ad creative.

    Only ``name`` and ``creative_spec`` are mutable; ``creative_type``
    and ``destination`` are permanently fixed at creation. Updating
    ``creative_spec`` may trigger re-review (``systemStatus`` returns
    to ``PENDING``).

    Attributes:
        name: New creative name. Omit if not updating.
        creative_spec: New creative spec. Omit if not updating.
    """

    name: str | None = None
    creative_spec: CreativeSpec | None = Field(default=None, alias="creativeSpec")


class AssetImage(V1Model):
    """Type-specific details for an ``IMAGE`` asset. All read-only.

    Attributes:
        ad_account_id: Owning ad account; present for custom assets.
        width: Width in pixels.
        height: Height in pixels.
        format: Image file format.
        size_bytes: File size in bytes.
        orientation: Portrait, landscape, or square.
        provider_asset_url: Source URL at the provider system.
        provider_token: Provider-specific auth/access token.
        check_sum: Integrity checksum.
        sort_position: Display order within an asset collection.
    """

    ad_account_id: str | None = Field(default=None, alias="adAccountId")
    width: int | None = None
    height: int | None = None
    format: ImageType | None = None
    size_bytes: int | None = Field(default=None, alias="sizeBytes")
    orientation: Orientation | None = None
    provider_asset_url: str | None = Field(default=None, alias="providerAssetUrl")
    provider_token: str | None = Field(default=None, alias="providerToken")
    check_sum: str | None = Field(default=None, alias="checkSum")
    sort_position: int | None = Field(default=None, alias="sortPosition")


class AssetConstraintGroup(V1Model):
    """A supply-placement/country group in asset eligibility.

    When both fields are populated the constraint applies to their
    intersection.

    Attributes:
        supply_placement: Supply placements (e.g. ``SEARCH_TAB``).
        country_or_region: ISO 3166-1 alpha-2 codes (e.g. ``US``).
    """

    supply_placement: list[str] | None = Field(default=None, alias="supplyPlacement")
    country_or_region: list[str] | None = Field(default=None, alias="countryOrRegion")


class AssetEligibility(V1Model):
    """Where an asset is eligible to serve. All read-only.

    Attributes:
        status: The asset's eligibility status.
        blocked_groups: Placement/country groups where blocked.
        allowed_groups: Placement/country groups explicitly allowed.
    """

    status: AssetEligibilityStatus | None = None
    blocked_groups: list[AssetConstraintGroup] | None = Field(default=None, alias="blockedGroups")
    allowed_groups: list[AssetConstraintGroup] | None = Field(default=None, alias="allowedGroups")


class Asset(V1Model):
    """A unified media asset referenced from creative specs.

    Attributes:
        id: Internal asset identifier (a UUID string, unlike the
            int64 creative id).
        name: The asset name.
        asset_type: The media type (currently only ``IMAGE``).
        provider_asset_id: Provider-assigned id (e.g. App Store
            Connect asset ID).
        promoted_object_id: E.g. ``adamId`` for apps, ``brandId`` for
            Apple Maps brands.
        promoted_object_type: ``BUSINESS_BRAND`` or ``APPSTORE_APP``.
        provider_asset_metadata: Free-form provider-specific metadata.
        asset_details: Type-specific details when the asset is an
            image.
        parent_asset_id: Parent asset id if this is a variant (crop or
            resize); ``None`` for originals.
        variant_ids: Variant identifiers (sizes, formats,
            localizations).
        creation_time: Creation timestamp. Read-only.
        modification_time: Last-modification timestamp. Read-only.
        deleted: Soft-delete flag. Read-only.
        eligibility: Serving eligibility. Read-only.
    """

    id: str | None = None
    name: str | None = None
    asset_type: AssetType | None = Field(default=None, alias="assetType")
    provider_asset_id: str | None = Field(default=None, alias="providerAssetId")
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    promoted_object_type: str | None = Field(default=None, alias="promotedObjectType")
    provider_asset_metadata: dict[str, Any] | None = Field(
        default=None, alias="providerAssetMetadata"
    )
    asset_details: AssetImage | None = Field(default=None, alias="assetDetails")
    parent_asset_id: str | None = Field(default=None, alias="parentAssetId")
    variant_ids: list[str] | None = Field(default=None, alias="variantIds")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    deleted: bool | None = None
    eligibility: AssetEligibility | None = None


class LocaleInfo(V1Model):
    """Locale metadata for localized creative text. All read-only.

    Attributes:
        language: ISO 639-1 language identifier (e.g. ``en``).
        language_code: BCP-47 code including region (e.g. ``en-US``);
            used as the map key in ``localizedText``.
    """

    language: str | None = None
    language_code: str | None = Field(default=None, alias="languageCode")
