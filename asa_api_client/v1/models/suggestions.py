"""Models for the Apple Ads Platform API v1 suggestions group.

Covers keyword, phrase, and category suggestions plus the Target CPA
suggestion for Maximize Conversions campaigns. All suggestion objects
are read-only; requests are built with the shared query body via
:class:`asa_api_client.v1.query.Query`, identifying the promoted object
through mandatory ``promotedObjectId`` / ``promotedObjectType`` filters
(filter values are always arrays of strings).
"""

from enum import StrEnum

from pydantic import Field

from asa_api_client.v1.models.base import Money, V1Model


class SuggestionPromotedObjectType(StrEnum):
    """The promoted object type used in suggestion query filters."""

    APPSTORE_APP = "APPSTORE_APP"
    BUSINESS_BRAND = "BUSINESS_BRAND"


class SuggestionQueryType(StrEnum):
    """Route selector for the phrase and category suggestion queries.

    ``SUGGESTION`` discovers phrases/categories for a specific app or
    brand; ``SEARCH`` looks up specific phrases/categories by value.
    """

    SUGGESTION = "SUGGESTION"
    SEARCH = "SEARCH"


class KeywordSuggestion(V1Model):
    """One keyword suggestion from ``POST /v1/suggestions/keywords/query``.

    Attributes:
        text: The suggested keyword text.
        popularity: Relative popularity score across App Store
            countries/regions (0-100; not absolute search volume).
    """

    text: str | None = None
    popularity: int | None = None


class PhraseSuggestion(V1Model):
    """One phrase suggestion from ``POST /v1/suggestions/phrases/query``.

    Attributes:
        phrase: The suggested phrase text (may be a multi-word,
            longer-tail query).
        popularity: Relative popularity score — how frequently the
            phrase appears in user searches.
    """

    phrase: str | None = None
    popularity: int | None = None


class CategorySuggestion(V1Model):
    """One category suggestion from ``POST /v1/suggestions/categories/query``.

    Attributes:
        category: The category name. For App Store apps this is an app
            category (e.g. ``"Productivity"``); for Apple Maps brands
            it's a brand category (e.g. ``"Restaurants"``).
        popularity: Relative popularity score for this category.
    """

    category: str | None = None
    popularity: int | None = None


class TargetCpaSuggestion(V1Model):
    """The Target CPA suggestion from ``POST /v1/suggestions/target-cpas/query``.

    The suggestion is the maximum tap-install CPI observed across the
    app's eligible markets over the last 28 days; only countries or
    regions with at least 10 installs in that window qualify.

    Attributes:
        suggested_target_cpa: The suggested Target CPA amount, in the
            ad account's billing currency.
        country_or_region: The country/region codes the suggestion
            applies to.
        promoted_object_id: ID of the promoted object (app or brand)
            the suggestion was calculated for.
        app_category: The App Store category used to scope the
            suggestion's performance data.
    """

    suggested_target_cpa: Money | None = Field(default=None, alias="suggestedTargetCPA")
    country_or_region: list[str] | None = Field(default=None, alias="countryOrRegion")
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    app_category: str | None = Field(default=None, alias="appCategory")
