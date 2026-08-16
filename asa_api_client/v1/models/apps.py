"""Models for the Apple Ads Platform API v1 apps group.

Covers the Search Apps, App Details, Supported App Languages, App
Eligibility, and Creative Rejection Reasons surfaces.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class DeviceClass(StrEnum):
    """Device classes an app supports."""

    IPHONE = "IPHONE"
    IPAD = "IPAD"


class EligibilityState(StrEnum):
    """Whether an app is eligible to run ads for a given combination."""

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"


class RejectionReasonLevel(StrEnum):
    """The product-page level a creative rejection reason applies to."""

    DEFAULT_PRODUCT_PAGE = "DEFAULT_PRODUCT_PAGE"
    DEFAULT_PRODUCT_PAGE_LOCALE = "DEFAULT_PRODUCT_PAGE_LOCALE"
    CUSTOM_PRODUCT_PAGE = "CUSTOM_PRODUCT_PAGE"
    CUSTOM_PRODUCT_PAGE_LOCALE = "CUSTOM_PRODUCT_PAGE_LOCALE"


class AppInfo(V1Model):
    """A single app search result from ``GET /v1/search/apps``.

    Attributes:
        adam_id: The app's Adam ID; use when creating campaigns
            targeting this app.
        app_name: App display name as shown in the App Store.
        developer_name: Developer or publisher name.
        country_or_region_codes: ISO 3166-1 alpha-2 codes for all
            storefronts where the app is available.
    """

    adam_id: int = Field(alias="adamId")
    app_name: str = Field(alias="appName")
    developer_name: str = Field(alias="developerName")
    country_or_region_codes: list[str] = Field(alias="countryOrRegionCodes")


class AppDetails(V1Model):
    """App Store metadata for one app from ``GET /v1/apps/{adamId}``.

    Attributes:
        id: App identifier (Adam ID as a string); equals the
            ``promotedObjectId`` used in targeting.
        app_name: Display name.
        artist_name: Developer or company name.
        primary_language: BCP-47 code, e.g. ``"en-US"``.
        primary_genre: Primary App Store genre path.
        secondary_genre: Secondary genre, if assigned.
        device_classes: Device classes the app supports.
        icon_picture_url: App icon URL.
        is_preorder: Whether the app is available for pre-order.
        available_storefronts: ISO 3166-1 alpha-2 country codes.
    """

    id: str | None = None
    app_name: str | None = Field(default=None, alias="appName")
    artist_name: str | None = Field(default=None, alias="artistName")
    primary_language: str | None = Field(default=None, alias="primaryLanguage")
    primary_genre: str | None = Field(default=None, alias="primaryGenre")
    secondary_genre: str | None = Field(default=None, alias="secondaryGenre")
    device_classes: list[DeviceClass] | None = Field(default=None, alias="deviceClasses")
    icon_picture_url: str | None = Field(default=None, alias="iconPictureUrl")
    is_preorder: bool | None = Field(default=None, alias="isPreorder")
    available_storefronts: list[str] | None = Field(default=None, alias="availableStorefronts")


class LocaleInfo(V1Model):
    """A language available for advertising in a market.

    Attributes:
        language: ISO 639-1 language code, e.g. ``"en"``.
        language_code: BCP-47 code with region subtag, e.g. ``"en-US"``.
    """

    language: str | None = None
    language_code: str | None = Field(default=None, alias="languageCode")


class AppSupportedLanguages(V1Model):
    """One advertising market's supported-language metadata.

    Attributes:
        name: Country/region display name, e.g. ``"United States"``.
        country_code: ISO 3166-1 alpha-2 code.
        ads_supported_languages: All languages available for ads in
            this market.
        ads_default_languages: Languages applied when no explicit
            language targeting is set.
    """

    name: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")
    ads_supported_languages: list[LocaleInfo] | None = Field(
        default=None, alias="adsSupportedLanguages"
    )
    ads_default_languages: list[LocaleInfo] | None = Field(
        default=None, alias="adsDefaultLanguages"
    )


class EligibilityResponse(V1Model):
    """One eligibility row from ``POST /v1/eligibilities/apps/query``.

    Each row covers one app x supply placement x supply source x
    country/region x device class combination; an app eligible in some
    placements and ineligible in others appears as multiple rows.

    Attributes:
        adam_id: The app's Adam ID.
        supply_placement: Placement evaluated, e.g.
            ``"APPSTORE_SEARCH_RESULTS"`` (no exhaustive enum documented).
        supply_source: Supply source evaluated, e.g. ``"APPSTORE"``.
        min_age: Minimum age rating required to serve ads for this app
            in this market.
        state: Whether the combination is eligible.
        country_or_region: Country/region evaluated.
        device_class: Device class evaluated, e.g. ``"IPHONE"``.
        reasons: Codes explaining ``INELIGIBLE`` (not exhaustive), e.g.
            ``"APP_NOT_ELIGIBLE_IN_STOREFRONT"``.
        creation_time: When the record was created.
        modification_time: When the record was last modified.
    """

    adam_id: int | None = Field(default=None, alias="adamId")
    supply_placement: str | None = Field(default=None, alias="supplyPlacement")
    supply_source: str | None = Field(default=None, alias="supplySource")
    min_age: float | None = Field(default=None, alias="minAge")
    state: EligibilityState | None = None
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")
    reasons: list[str] | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class CreativeRejectionReason(V1Model):
    """Why an ad creative was rejected during Apple review.

    Use alongside ``systemStatusReasons`` on the creative.

    Attributes:
        id: System-assigned record identifier.
        adam_id: App whose product page triggered the rejection.
        product_page_id: Product page ID, if applicable.
        asset_id: UUID of the offending asset, if applicable.
        supply_source: Supply source, e.g. ``"APPSTORE"``.
        supply_placement: Placement, e.g. ``"APPSTORE_TODAY_TAB"``.
        country_or_region: Country/region code.
        language_code: BCP-47 code, e.g. ``"en-US"``.
        reason_type: Reason type, e.g. ``"REJECTION_REASON"``.
        reason_code: Rejection code, e.g. ``"APP_NOT_ELIGIBLE"`` (no
            exhaustive enum documented).
        comment: Additional reviewer context.
        reason_level: The product-page level the reason applies to.
        creative_id: The rejected creative's ID (present in example
            payloads; absent from the documented property table).
        creation_time: When the record was created.
        modification_time: When the record was last modified.
    """

    id: int
    adam_id: int | None = Field(default=None, alias="adamId")
    product_page_id: str | None = Field(default=None, alias="productPageId")
    asset_id: str | None = Field(default=None, alias="assetId")
    supply_source: str | None = Field(default=None, alias="supplySource")
    supply_placement: str | None = Field(default=None, alias="supplyPlacement")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    language_code: str | None = Field(default=None, alias="languageCode")
    reason_type: str | None = Field(default=None, alias="reasonType")
    reason_code: str | None = Field(default=None, alias="reasonCode")
    comment: str | None = None
    reason_level: RejectionReasonLevel | None = Field(default=None, alias="reasonLevel")
    creative_id: int | None = Field(default=None, alias="creativeId")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
