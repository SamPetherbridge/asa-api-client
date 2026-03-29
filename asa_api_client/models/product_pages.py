"""Product Page models for the Apple Search Ads API.

Product pages represent custom App Store product pages that can
be used as ad variations.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductPageLocaleDetail(BaseModel):
    """Locale-specific details for a product page.

    Attributes:
        adam_id: The App Store app ID.
        app_name: The app name.
        product_page_id: The product page ID.
        language: The language name.
        language_code: The language code (e.g., "en-US").
        device_classes: Supported device classes.
        promotional_text: Promotional text.
        short_description: Short description.
        sub_title: App subtitle.
        app_preview_device_with_assets: Map of devices with preview assets.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    adam_id: int | None = Field(default=None, alias="adamId")
    app_name: str | None = Field(default=None, alias="appName")
    product_page_id: str | None = Field(default=None, alias="productPageId")
    language: str | None = None
    language_code: str | None = Field(default=None, alias="languageCode")
    device_classes: list[str] | None = Field(default=None, alias="deviceClasses")
    promotional_text: str | None = Field(default=None, alias="promotionalText")
    short_description: str | None = Field(default=None, alias="shortDescription")
    sub_title: str | None = Field(default=None, alias="subTitle")
    app_preview_device_with_assets: dict[str, list[str]] | None = Field(
        default=None, alias="appPreviewDeviceWithAssets"
    )


class ProductPage(BaseModel):
    """An App Store custom product page.

    Attributes:
        id: The product page ID.
        adam_id: The App Store app ID.
        name: The product page name.
        state: The product page state (HIDDEN/VISIBLE).
        creation_time: When the product page was created.
        modification_time: When the product page was last modified.
        deep_link: The deep link URL (iOS 18+).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    adam_id: int | None = Field(default=None, alias="adamId")
    name: str | None = None
    state: str | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    deep_link: str | None = Field(default=None, alias="deepLink")
