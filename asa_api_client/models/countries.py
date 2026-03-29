"""Country and region models for the Apple Search Ads API.

Supported countries/regions and their language details.
"""

from pydantic import BaseModel, ConfigDict, Field


class LanguageDetail(BaseModel):
    """A supported language for a country or region."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    language: str | None = None
    language_code: str | None = Field(default=None, alias="languageCode")


class CountryOrRegion(BaseModel):
    """A supported country or region for advertising.

    Attributes:
        country_or_region: The ISO alpha-2 country/region code.
        supported_languages: Languages supported for ads in this location.
        default_language: The default language for this location.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    country_or_region: str = Field(alias="countryOrRegion")
    supported_languages: list[LanguageDetail] | None = Field(
        default=None, alias="supportedLanguages"
    )
    default_language: LanguageDetail | None = Field(default=None, alias="defaultLanguage")
