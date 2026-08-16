"""Models for Apple Ads Platform API v1 product pages.

Product pages (Default Product Pages, Custom Product Pages, and Product
Page Optimization variants) are created in App Store Connect; the Apple
Ads Platform API only reads their state. Product page IDs are
ASC-assigned UUID strings, not integers.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import V1Model


class DeviceClass(StrEnum):
    """Device classes a product page locale supports."""

    IPHONE = "IPHONE"
    IPAD = "IPAD"


class AssetReference(V1Model):
    """A reference to an App Store asset by its identifier.

    Attributes:
        asset_id: The unique identifier of the referenced asset.
    """

    asset_id: str | None = Field(default=None, alias="assetId")


class DeviceAssetGroup(V1Model):
    """Assets for one device type inside an ``assetsByDevice`` map.

    Map keys are specific device-type strings (e.g. ``iphone_6_5``,
    ``ipadPro``), not :class:`DeviceClass` values.

    Attributes:
        assets: Ordered asset references for this device type.
        app_preview_device_fall_back_devices: Fallback device-type
            strings used when assets aren't available for this device;
            empty when no fallback applies.
    """

    assets: list[AssetReference] | None = None
    app_preview_device_fall_back_devices: list[str] | None = Field(
        default=None, alias="appPreviewDeviceFallBackDevices"
    )


class ProductPageDetails(V1Model):
    """Metadata for a DPP, CPP, or PPO product page variant.

    Attributes:
        id: The ASC product page UUID (a string, not an integer).
        adam_id: The App Store app identifier this page belongs to.
        name: Page name as configured in App Store Connect.
        state: Page state as a plain string (no closed enum); typically
            ``PUBLISHED``, but ASC may surface others such as
            ``READY_FOR_DISTRIBUTION`` during propagation.
        deep_link: Deep link URL, when configured as a destination.
        creation_time: When the page was created (ISO 8601).
        modification_time: When the page was last modified (ISO 8601).
    """

    id: str | None = None
    adam_id: int | None = Field(default=None, alias="adamId")
    name: str | None = None
    state: str | None = None
    deep_link: str | None = Field(default=None, alias="deepLink")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")


class ProductPageLocaleDetails(V1Model):
    """Locale-specific content for an App Store product page.

    Attributes:
        adam_id: The app's Adam ID.
        language: Language identifier, e.g. ``en``.
        language_code: BCP-47 language code, e.g. ``en-US``.
        app_name: Localized app display name.
        sub_title: App subtitle for the locale.
        promotional_text: Promotional text (max 170 characters).
        short_description: Short description (max 4000 characters).
        device_classes: Device classes the locale supports.
        assets_by_device: Map of device-type string (e.g.
            ``iphone_6_5``) to its asset group.
        product_page_id: Parent product page UUID.
    """

    adam_id: int | None = Field(default=None, alias="adamId")
    language: str | None = None
    language_code: str | None = Field(default=None, alias="languageCode")
    app_name: str | None = Field(default=None, alias="appName")
    sub_title: str | None = Field(default=None, alias="subTitle")
    promotional_text: str | None = Field(default=None, alias="promotionalText")
    short_description: str | None = Field(default=None, alias="shortDescription")
    device_classes: list[DeviceClass] | None = Field(default=None, alias="deviceClasses")
    assets_by_device: dict[str, DeviceAssetGroup] | None = Field(
        default=None, alias="assetsByDevice"
    )
    product_page_id: str | None = Field(default=None, alias="productPageId")


class AppLocaleDetails(V1Model):
    """Localized content for an app's Default Product Page.

    Same shape as :class:`ProductPageLocaleDetails`, except it carries
    ``isPrimaryLocale`` and has no ``productPageId``.

    Attributes:
        adam_id: App Store identifier for the app.
        language: Language identifier, e.g. ``en``.
        language_code: BCP-47 language code, e.g. ``en-US``.
        is_primary_locale: Whether this locale's language code matches
            the app's primary language.
        app_name: Localized app name.
        sub_title: Localized app subtitle.
        promotional_text: Promotional text (max 170 characters).
        short_description: Short description (max 4000 characters).
        device_classes: Device classes the locale supports.
        assets_by_device: Map of device-type string (e.g.
            ``iphone_6_5``) to its asset group.
    """

    adam_id: int | None = Field(default=None, alias="adamId")
    language: str | None = None
    language_code: str | None = Field(default=None, alias="languageCode")
    is_primary_locale: bool | None = Field(default=None, alias="isPrimaryLocale")
    app_name: str | None = Field(default=None, alias="appName")
    sub_title: str | None = Field(default=None, alias="subTitle")
    promotional_text: str | None = Field(default=None, alias="promotionalText")
    short_description: str | None = Field(default=None, alias="shortDescription")
    device_classes: list[DeviceClass] | None = Field(default=None, alias="deviceClasses")
    assets_by_device: dict[str, DeviceAssetGroup] | None = Field(
        default=None, alias="assetsByDevice"
    )
