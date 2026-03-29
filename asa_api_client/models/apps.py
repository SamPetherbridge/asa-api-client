"""App models for the Apple Search Ads API.

App models represent iOS apps eligible for advertising.
"""

from pydantic import BaseModel, ConfigDict, Field


class AppInfo(BaseModel):
    """An iOS app eligible for advertising.

    Attributes:
        adam_id: The App Store app ID.
        app_name: The app name.
        developer_name: The developer name.
        country_or_region_codes: Countries/regions where the app is available.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    adam_id: int = Field(alias="adamId")
    app_name: str = Field(alias="appName")
    developer_name: str | None = Field(default=None, alias="developerName")
    country_or_region_codes: list[str] | None = Field(
        default=None, alias="countryOrRegionCodes"
    )
