"""Geo targeting models for the Apple Search Ads API.

Geographic location models used for audience targeting
in ad groups.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GeoEntityType(StrEnum):
    """The type of geographic entity."""

    COUNTRY = "Country"
    ADMIN_AREA = "AdminArea"
    LOCALITY = "Locality"


class GeoLocation(BaseModel):
    """A geographic location for targeting.

    Attributes:
        id: The location identifier.
        display_name: The human-readable location name.
        entity: The type of geographic entity.
        country_or_region: The country/region code.
        admin_area: The admin area (state/province) name.
        locality: The locality (city) name.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    display_name: str = Field(alias="displayName")
    entity: GeoEntityType | str
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    admin_area: str | None = Field(default=None, alias="adminArea")
    locality: str | None = None
