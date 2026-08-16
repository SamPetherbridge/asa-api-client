"""Models for Apple Ads Platform API v1 reports.

Covers the APPS report endpoints (``reports/apps/...``), the Brands /
Apple Maps report endpoints (``reports/business-brands/...``), and the
shared reporting objects (time ranges, filters, sorting, pagination,
metrics, and per-entity metadata).

Every report response is a ``{result, pagination, error}`` envelope
whose ``result`` is a result container with ``rows`` (each row holding
``metadata``, ``totalMetrics``, and optional ``granularMetrics``) and an
optional ``summary`` populated when ``GRAND_TOTAL`` is requested.
"""

import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from asa_api_client.v1.models.base import Money, V1Error, V1Model, V1Pagination

# ---------------------------------------------------------------------------
# Shared reporting enums
# ---------------------------------------------------------------------------


class ReportGranularity(StrEnum):
    """Time period breakdown for ``granularMetrics`` in report responses.

    ``HOURLY`` is not supported for ad-level or search term-level
    reports. Omit granularity entirely to request a single day of data.
    """

    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"
    DAILY = "DAILY"
    HOURLY = "HOURLY"


class ReportTimeZone(StrEnum):
    """Time zone for the report date range.

    Search term-level reports support only ``ORTZ``.
    """

    UTC = "UTC"
    ORTZ = "ORTZ"


class ReportFilterOperator(StrEnum):
    """Comparison operators supported by reporting filters."""

    EQUALS = "EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    IN = "IN"
    LIKE = "LIKE"
    STARTS_WITH = "STARTS_WITH"
    CONTAINS = "CONTAINS"
    ENDS_WITH = "ENDS_WITH"
    CONTAINS_ANY = "CONTAINS_ANY"
    CONTAINS_ALL = "CONTAINS_ALL"
    BETWEEN = "BETWEEN"
    GREATER_THAN_OR_EQUAL_TO = "GREATER_THAN_OR_EQUAL_TO"
    LESS_THAN_OR_EQUAL_TO = "LESS_THAN_OR_EQUAL_TO"
    NOT_EQUALS = "NOT_EQUALS"


class ReportSortOrder(StrEnum):
    """Sort direction for reporting sort conditions."""

    ASC = "ASC"
    DESC = "DESC"


class AppsGroupBy(StrEnum):
    """``groupBy`` dimensions for APPS reports.

    KEYWORD and SEARCHTERM entities exclude ``ageRange``, ``gender``,
    ``countryCode``, ``adminArea``, and ``locality``. The AD entity
    supports only ``storefront`` and ``countryOrRegion``.
    """

    DEVICE_CLASS = "deviceClass"
    AGE_RANGE = "ageRange"
    GENDER = "gender"
    COUNTRY_CODE = "countryCode"
    ADMIN_AREA = "adminArea"
    LOCALITY = "locality"
    STOREFRONT = "storefront"
    COUNTRY_OR_REGION = "countryOrRegion"


class BrandsGroupBy(StrEnum):
    """``groupBy`` dimensions for BRANDS (Apple Maps) reports.

    KEYWORD and SEARCHTERM entities exclude ``supplyPlacement`` and
    ``locationId``.
    """

    DEVICE_CLASS = "deviceClass"
    LOCATION_ID = "locationId"
    SUPPLY_PLACEMENT = "supplyPlacement"


class AppsIncludeRows(StrEnum):
    """Row inclusion options for APPS reports.

    ``EMPTY_METRICS`` cannot be combined with ``groupBy``.
    """

    GRAND_TOTAL = "GRAND_TOTAL"
    EMPTY_METRICS = "EMPTY_METRICS"


class BrandsIncludeRows(StrEnum):
    """Row inclusion options for BRANDS reports.

    ``EMPTY_METRICS`` is not supported for any BRANDS entity.
    """

    GRAND_TOTAL = "GRAND_TOTAL"


class ReportingStatus(StrEnum):
    """Advertiser-configurable run state of a reported entity."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"


class ReportingSystemStatus(StrEnum):
    """System-evaluated delivery state of a reported entity."""

    RUNNING = "RUNNING"
    NOT_RUNNING = "NOT_RUNNING"


class ReportingAdChannelType(StrEnum):
    """The ad channel that served a report row's metrics."""

    SEARCH = "SEARCH"
    DISPLAY = "DISPLAY"


class ReportingBillingEvent(StrEnum):
    """The billing event of the campaign a report row belongs to."""

    TAPS = "TAPS"
    IMPRESSIONS = "IMPRESSIONS"


class ReportingPricingModel(StrEnum):
    """The pricing model of the ad group a report row belongs to."""

    CPA = "CPA"
    CPM = "CPM"
    CPT = "CPT"


class ReportingBidStrategyType(StrEnum):
    """Auction participation approach applied at report time."""

    MANUAL_CPT = "MANUAL_CPT"
    MANUAL_CPM = "MANUAL_CPM"
    MAX_CONVERSIONS = "MAX_CONVERSIONS"
    MAX_ENGAGEMENTS = "MAX_ENGAGEMENTS"


class AppsCreativeType(StrEnum):
    """Creative type of an APPS ad at report time."""

    CUSTOM_PRODUCT_PAGE = "CUSTOM_PRODUCT_PAGE"
    DEFAULT_PRODUCT_PAGE = "DEFAULT_PRODUCT_PAGE"


class BrandsCreativeType(StrEnum):
    """Creative type of a BRANDS (Apple Maps) ad at report time."""

    LOCAL_ADS_SEARCH_CREATIVE = "LOCAL_ADS_SEARCH_CREATIVE"


class ReportingCreativeSystemStatus(StrEnum):
    """System-evaluated validation state of a creative at report time."""

    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"


class ReportingKeywordStatus(StrEnum):
    """Status of a keyword in a report row.

    The docs list ``ACTIVE``/``PAUSED``/``DELETED`` but the live API
    returns ``ENABLED`` (observed 2026-08-16); both sets are accepted.
    """

    ACTIVE = "ACTIVE"
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    DELETED = "DELETED"


class AppsKeywordMatchType(StrEnum):
    """Match type of an App Store keyword in a report row."""

    BROAD = "BROAD"
    EXACT = "EXACT"


class BrandsKeywordMatchType(StrEnum):
    """Match type of an Apple Maps keyword in a report row."""

    PHRASE = "PHRASE"
    CATEGORY = "CATEGORY"


class CampaignDisplayStatus(StrEnum):
    """Rolled-up user-facing delivery state for a campaign."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ON_HOLD = "ON_HOLD"
    LIMITED = "LIMITED"
    PROCESSING = "PROCESSING"
    DELETED = "DELETED"


class CampaignSystemStatusReason(StrEnum):
    """Reason a campaign is not currently running."""

    PROCESSING = "PROCESSING"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    FEATURE_NOT_YET_AVAILABLE = "FEATURE_NOT_YET_AVAILABLE"
    FEATURE_NO_LONGER_AVAILABLE = "FEATURE_NO_LONGER_AVAILABLE"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    DELETED_BY_USER = "DELETED_BY_USER"
    USER_REQUESTED_ACCOUNT_SUSPENSION = "USER_REQUESTED_ACCOUNT_SUSPENSION"
    CAMPAIGN_DELETED_FOR_BASIC_MSF_MIGRATION = "CAMPAIGN_DELETED_FOR_BASIC_MSF_MIGRATION"
    SCHEDULE_PENDING = "SCHEDULE_PENDING"
    SCHEDULE_EXPIRED = "SCHEDULE_EXPIRED"
    APP_NOT_ELIGIBLE = "APP_NOT_ELIGIBLE"
    APP_NOT_ELIGIBLE_SEARCHADS = "APP_NOT_ELIGIBLE_SEARCHADS"
    APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT = "APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT"
    APP_NOT_PUBLISHED_YET = "APP_NOT_PUBLISHED_YET"
    APP_NOT_CATEGORIZED = "APP_NOT_CATEGORIZED"
    APP_SENSITIVE_CONTENT = "APP_SENSITIVE_CONTENT"
    APP_DOC_APPROVAL_REJECTED = "APP_DOC_APPROVAL_REJECTED"
    COUNTRIES_OR_REGIONS_NOT_ELIGIBLE = "COUNTRIES_OR_REGIONS_NOT_ELIGIBLE"
    SAPIN_LAW_AGENT_UNKNOWN = "SAPIN_LAW_AGENT_UNKNOWN"
    SAPIN_LAW_FRENCH_BIZ = "SAPIN_LAW_FRENCH_BIZ"
    SAPIN_LAW_FRENCH_BIZ_UNKNOWN = "SAPIN_LAW_FRENCH_BIZ_UNKNOWN"
    BUDGET_ORDER_EXHAUSTED = "BUDGET_ORDER_EXHAUSTED"
    BUDGET_ORDER_SCHEDULE_PENDING = "BUDGET_ORDER_SCHEDULE_PENDING"
    BUDGET_ORDER_SCHEDULE_EXPIRED = "BUDGET_ORDER_SCHEDULE_EXPIRED"
    BUDGET_ORDER_CANCELED = "BUDGET_ORDER_CANCELED"
    BUDGET_ORDER_OR_INVOICE_DETAIL_MISSING = "BUDGET_ORDER_OR_INVOICE_DETAIL_MISSING"
    LIFETIME_BUDGET_EXHAUSTED = "LIFETIME_BUDGET_EXHAUSTED"
    MONTHLY_BUDGET_EXHAUSTED = "MONTHLY_BUDGET_EXHAUSTED"
    LINE_OF_CREDIT_EXHAUSTED = "LINE_OF_CREDIT_EXHAUSTED"
    ORG_PAYMENT_TYPE_DECLINED = "ORG_PAYMENT_TYPE_DECLINED"
    TAX_VERIFICATION_PENDING = "TAX_VERIFICATION_PENDING"
    AD_ACCOUNT_PAYMENT_ISSUES = "AD_ACCOUNT_PAYMENT_ISSUES"
    ORG_NO_PAYMENT_METHOD_ON_FILE = "ORG_NO_PAYMENT_METHOD_ON_FILE"
    ORG_CHARGE_BACK_DISPUTED = "ORG_CHARGE_BACK_DISPUTED"
    ORG_PAYMENT_METHOD_CHANGED = "ORG_PAYMENT_METHOD_CHANGED"
    ORG_SUSPENDED_FRAUD = "ORG_SUSPENDED_FRAUD"
    ORG_SUSPENDED_POLICY_VIOLATION = "ORG_SUSPENDED_POLICY_VIOLATION"
    CONTENT_PROVIDER_UNLINKED = "CONTENT_PROVIDER_UNLINKED"
    AD_ACCOUNT_BRAND_DELEGATION_ISSUES = "AD_ACCOUNT_BRAND_DELEGATION_ISSUES"
    AD_GROUPS_MISSING = "AD_GROUPS_MISSING"
    AD_GROUPS_NOT_RUNNING = "AD_GROUPS_NOT_RUNNING"
    AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_MISSING = "AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_MISSING"
    AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_RUNNING = (
        "AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_RUNNING"
    )


class CampaignSystemLimitedStatusReason(StrEnum):
    """Reason a campaign is delivering at reduced capacity."""

    FEATURE_NOT_AVAILABLE_IN_COUNTRY_OR_REGION = "FEATURE_NOT_AVAILABLE_IN_COUNTRY_OR_REGION"
    ACCOUNT_DOC_APPROVAL_EXPIRED = "ACCOUNT_DOC_APPROVAL_EXPIRED"
    ACCOUNT_DOC_APPROVAL_INFECTED = "ACCOUNT_DOC_APPROVAL_INFECTED"
    ACCOUNT_DOC_APPROVAL_NOT_SUBMITTED = "ACCOUNT_DOC_APPROVAL_NOT_SUBMITTED"
    ACCOUNT_DOC_APPROVAL_PENDING = "ACCOUNT_DOC_APPROVAL_PENDING"
    ACCOUNT_DOC_APPROVAL_REJECTED = "ACCOUNT_DOC_APPROVAL_REJECTED"
    APP_CONTENT_REJECTED = "APP_CONTENT_REJECTED"
    APP_CONTENT_REVIEW_PENDING = "APP_CONTENT_REVIEW_PENDING"
    APP_DOC_APPROVAL_EXPIRED = "APP_DOC_APPROVAL_EXPIRED"
    APP_DOC_APPROVAL_INFECTED = "APP_DOC_APPROVAL_INFECTED"
    APP_DOC_APPROVAL_NOT_SUBMITTED = "APP_DOC_APPROVAL_NOT_SUBMITTED"
    APP_DOC_APPROVAL_PENDING = "APP_DOC_APPROVAL_PENDING"
    APP_DOC_APPROVAL_REJECTED = "APP_DOC_APPROVAL_REJECTED"
    APP_NOT_ELIGIBLE = "APP_NOT_ELIGIBLE"
    APP_NOT_ELIGIBLE_SEARCHADS = "APP_NOT_ELIGIBLE_SEARCHADS"
    APP_NOT_ELIGIBLE_SUPPLY_SOURCE = "APP_NOT_ELIGIBLE_SUPPLY_SOURCE"
    APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT = "APP_NOT_ELIGIBLE_SUPPLY_PLACEMENT"
    APP_LANGUAGE_INCOMPATIBLE = "APP_LANGUAGE_INCOMPATIBLE"
    APP_NOT_PUBLISHED_YET = "APP_NOT_PUBLISHED_YET"
    SAPIN_LAW_AGENT_UNKNOWN = "SAPIN_LAW_AGENT_UNKNOWN"
    SAPIN_LAW_FRENCH_BIZ = "SAPIN_LAW_FRENCH_BIZ"
    SAPIN_LAW_FRENCH_BIZ_UNKNOWN = "SAPIN_LAW_FRENCH_BIZ_UNKNOWN"
    BRAND_POLICY_ISSUES = "BRAND_POLICY_ISSUES"
    AD_GROUPS_LIMITED = "AD_GROUPS_LIMITED"


class AdGroupSystemStatusReason(StrEnum):
    """Reason an ad group's system status is ``NOT_RUNNING``."""

    PROCESSING = "PROCESSING"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    DELETED_BY_USER = "DELETED_BY_USER"
    SCHEDULE_PENDING = "SCHEDULE_PENDING"
    SCHEDULE_EXPIRED = "SCHEDULE_EXPIRED"
    TARGETED_DEVICE_CLASS_NOT_SUPPORTED_SUPPLY_PLACEMENT = (
        "TARGETED_DEVICE_CLASS_NOT_SUPPORTED_SUPPLY_PLACEMENT"
    )
    PENDING_AUDIENCE_VERIFICATION = "PENDING_AUDIENCE_VERIFICATION"
    AUDIENCE_BELOW_THRESHOLD = "AUDIENCE_BELOW_THRESHOLD"
    CAMPAIGN_NOT_RUNNING = "CAMPAIGN_NOT_RUNNING"
    ADS_NOT_RUNNING = "ADS_NOT_RUNNING"
    AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_ALLOWED_IN_MANUAL_CAMPAIGNS = (
        "AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_NOT_ALLOWED_IN_MANUAL_CAMPAIGNS"
    )
    KEYWORDS_MISSING = "KEYWORDS_MISSING"


class AdSystemStatusReason(StrEnum):
    """Reason an ad is not currently running."""

    PROCESSING = "PROCESSING"
    PAUSED_BY_USER = "PAUSED_BY_USER"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"
    DELETED_BY_USER = "DELETED_BY_USER"
    AD_APPROVAL_PENDING = "AD_APPROVAL_PENDING"
    AD_APPROVAL_REJECTED = "AD_APPROVAL_REJECTED"
    AD_APPROVAL_CREATIVE_DOC_EXPIRED = "AD_APPROVAL_CREATIVE_DOC_EXPIRED"
    AD_APPROVAL_CREATIVE_DOC_NOT_SUBMITTED = "AD_APPROVAL_CREATIVE_DOC_NOT_SUBMITTED"
    AD_APPROVAL_CREATIVE_DOC_PENDING = "AD_APPROVAL_CREATIVE_DOC_PENDING"
    AD_APPROVAL_CREATIVE_DOC_REJECTED = "AD_APPROVAL_CREATIVE_DOC_REJECTED"
    CREATIVE_SET_INVALID = "CREATIVE_SET_INVALID"
    CREATIVE_SET_UNSUPPORTED = "CREATIVE_SET_UNSUPPORTED"
    CREATIVE_INVALID = "CREATIVE_INVALID"
    CREATIVE_PENDING = "CREATIVE_PENDING"
    PRODUCT_PAGE_DELETED = "PRODUCT_PAGE_DELETED"
    PRODUCT_PAGE_HIDDEN = "PRODUCT_PAGE_HIDDEN"
    PRODUCT_PAGE_INSUFFICIENT_ASSETS = "PRODUCT_PAGE_INSUFFICIENT_ASSETS"
    PRODUCT_PAGE_UNAVAILABLE = "PRODUCT_PAGE_UNAVAILABLE"
    PRODUCT_PAGE_INCOMPATIBLE = "PRODUCT_PAGE_INCOMPATIBLE"
    CREATIVE_LOCALE_INCOMPATIBLE = "CREATIVE_LOCALE_INCOMPATIBLE"


# ---------------------------------------------------------------------------
# Shared reporting request objects
# ---------------------------------------------------------------------------


class RequestPagination(V1Model):
    """Pagination settings for reporting requests.

    Attributes:
        offset: Zero-based starting position for the result set.
        page_size: Records per page. Maximum 5000, default 100.
    """

    offset: int | None = None
    page_size: int | None = Field(default=None, alias="pageSize")


class ReportTimeRange(V1Model):
    """Date range, time zone, and granularity for a reporting request.

    Attributes:
        start: Inclusive start date (YYYY-MM-DD).
        end: Inclusive end date (YYYY-MM-DD).
        time_zone: ``ORTZ`` (default) or ``UTC``. Search term reports
            require ``ORTZ``.
        granularity: Breakdown period for ``granularMetrics``. Omit to
            request a single day of data.
    """

    start: datetime.date | None = None
    end: datetime.date | None = None
    time_zone: ReportTimeZone | None = Field(default=None, alias="timeZone")
    granularity: ReportGranularity | None = None


class ReportFilter(V1Model):
    """Filter condition for reporting requests.

    Attributes:
        field: Field name to filter on (e.g. ``campaignId``).
        operator: Comparison operator.
        value: A bare string for single-value operators or an array of
            strings for multi-value operators (``IN``, ``BETWEEN``,
            ``CONTAINS_ANY``, ``CONTAINS_ALL``).
    """

    field: str | None = None
    operator: ReportFilterOperator | None = None
    value: str | list[str] | None = None


class ReportSorting(V1Model):
    """Sort condition for reporting requests.

    Attributes:
        field: Field name to sort on (e.g. ``localSpend``).
        order: Sort direction (``ASC`` or ``DESC``).
    """

    field: str | None = None
    order: ReportSortOrder | None = None


class AppsOptions(V1Model):
    """Reporting options for APPS reports.

    Attributes:
        include_rows: Row inclusion options. ``EMPTY_METRICS`` cannot be
            combined with ``groupBy``.
    """

    include_rows: list[AppsIncludeRows] | None = Field(default=None, alias="includeRows")


class BrandsOptions(V1Model):
    """Reporting options for BRANDS reports.

    Attributes:
        include_rows: Row inclusion options; only ``GRAND_TOTAL`` is
            supported for BRANDS entities.
    """

    include_rows: list[BrandsIncludeRows] | None = Field(default=None, alias="includeRows")


class AppsReportingRequest(V1Model):
    """Request body for APPS reporting queries.

    Attributes:
        pagination: Pagination settings for the report results.
        sorting: Sort entities ascending or descending (default: by ID,
            ascending).
        filters: Filter field conditions for the report.
        fields: Field names to return; omit to include all fields.
        group_by: Dimensions to group responses by.
        time_range: Date range, time zone, and granularity.
        options: Row inclusion options (``GRAND_TOTAL``,
            ``EMPTY_METRICS``).
    """

    pagination: RequestPagination | None = None
    sorting: list[ReportSorting] | None = None
    filters: list[ReportFilter] | None = None
    fields: list[str] | None = None
    group_by: list[AppsGroupBy] | None = Field(default=None, alias="groupBy")
    time_range: ReportTimeRange | None = Field(default=None, alias="timeRange")
    options: AppsOptions | None = None


class BrandsReportingRequest(V1Model):
    """Request body for BRANDS (Apple Maps) reporting queries.

    Attributes:
        pagination: Pagination settings for the report results.
        sorting: Sort entities ascending or descending (default: by ID,
            ascending).
        filters: Filter field conditions for the report.
        fields: Field names to return; omit to include all fields.
        group_by: Dimensions to group responses by.
        time_range: Date range, time zone, and granularity.
        options: Row inclusion options (``GRAND_TOTAL`` only).
    """

    pagination: RequestPagination | None = None
    sorting: list[ReportSorting] | None = None
    filters: list[ReportFilter] | None = None
    fields: list[str] | None = None
    group_by: list[BrandsGroupBy] | None = Field(default=None, alias="groupBy")
    time_range: ReportTimeRange | None = Field(default=None, alias="timeRange")
    options: BrandsOptions | None = None


# ---------------------------------------------------------------------------
# Shared reporting value objects
# ---------------------------------------------------------------------------


class ReportingMoney(V1Model):
    """Monetary value wrapper used in reporting metadata.

    Attributes:
        value: The wrapped monetary amount.
    """

    value: Money | None = None


class ReportingBidStrategy(V1Model):
    """Bid strategy configuration as captured in report rows.

    Attributes:
        bid_strategy_type: The bid strategy applied.
        bid: Bid amount for manual strategies; None for automated ones.
    """

    bid_strategy_type: ReportingBidStrategyType | None = Field(
        default=None, alias="bidStrategyType"
    )
    bid: Money | None = None


class IncludeExclude(V1Model):
    """Targeting criteria values included in ad delivery.

    Attributes:
        include: Values to target; accepted values depend on the field.
    """

    include: list[str] | None = None


class PromotedObject(V1Model):
    """Promoted object details in report metadata.

    Attributes:
        name: The promoted object's name (brand or location name for
            BRANDS campaigns).
    """

    name: str | None = None


class ReportingCampaignMin(V1Model):
    """Minimal campaign information embedded in report rows.

    The docs list no properties for this object; it exists as a
    placeholder for future campaign context.
    """


class ReportingAdGroupMin(V1Model):
    """Minimal ad group information embedded in report rows.

    Attributes:
        name: The ad group name.
        deleted: Whether the ad group has been deleted.
    """

    name: str | None = None
    deleted: bool | None = None


class ReportingCreativeSpec(V1Model):
    """Creative specification embedded in report rows.

    Attributes:
        language: BCP 47 language tag of the creative (e.g. ``en-US``).
    """

    language: str | None = None


class ReportingDestination(V1Model):
    """Creative destination embedded in report rows.

    Attributes:
        parameters: Destination parameters as a key-value map (content
            varies by creative and destination type; see
            ``DestinationParameter`` in the docs).
    """

    parameters: dict[str, Any] | None = None


class ReportingKeywordBidRecommendation(V1Model):
    """Keyword bid recommendation details.

    Attributes:
        suggested_bid_amount: Suggested bid amount. Read-only.
    """

    suggested_bid_amount: float | None = Field(default=None, alias="suggestedBidAmount")


class KeywordInsights(V1Model):
    """Insights for keyword reporting rows.

    Attributes:
        bid_recommendation: Suggested bid information for this keyword.
    """

    bid_recommendation: ReportingKeywordBidRecommendation | None = Field(
        default=None, alias="bidRecommendation"
    )


class AppsTargetingProjection(V1Model):
    """Targeting projection for APPS campaigns.

    Attributes:
        supply_placement: Ad placement slots included in delivery.
        lifetime_storefronts: Storefronts targeted over the campaign's
            lifetime.
        country_or_region: Country codes currently targeted.
    """

    supply_placement: IncludeExclude | None = Field(default=None, alias="supplyPlacement")
    lifetime_storefronts: IncludeExclude | None = Field(default=None, alias="lifetimeStorefronts")
    country_or_region: IncludeExclude | None = Field(default=None, alias="countryOrRegion")


class BrandsTargetingProjection(V1Model):
    """Targeting projection for BRANDS ad groups and campaigns.

    Attributes:
        supply_placement: Placement slots within Maps supply.
        lifetime_storefronts: Country/region targeting over the
            campaign's lifetime.
        supply_source: Supply source restriction (``MAPS``).
        promoted_location_group: Targeted location group ID.
        promoted_location: Targeted individual location ID.
    """

    supply_placement: IncludeExclude | None = Field(default=None, alias="supplyPlacement")
    lifetime_storefronts: IncludeExclude | None = Field(default=None, alias="lifetimeStorefronts")
    supply_source: IncludeExclude | None = Field(default=None, alias="supplySource")
    promoted_location_group: IncludeExclude | None = Field(
        default=None, alias="promotedLocationGroup"
    )
    promoted_location: IncludeExclude | None = Field(default=None, alias="promotedLocation")


# ---------------------------------------------------------------------------
# APPS metrics
# ---------------------------------------------------------------------------


class AppsMetrics(V1Model):
    """Metrics for the APPS promoted object type.

    Attributes:
        date: Report date (present in granular metrics).
        local_spend: Total spend in the reporting period.
        impressions: Total ad impressions.
        taps: Total ad taps.
        ttr: Tap-through rate (taps / impressions).
        cpt: Average cost per tap.
        cpm: Average cost per thousand impressions.
        tap_installs: Installs attributed to taps.
        tap_install_cpi: Average cost per tap-attributed install.
        total_new_downloads: Total first-time installs.
        total_redownloads: Total redownloads across attribution types.
        view_installs: Installs from view-through attribution.
        total_installs: Total installs across attribution types.
        tap_new_downloads: New downloads attributed to taps.
        tap_redownloads: Redownloads attributed to taps.
        view_new_downloads: New downloads from view-through impressions.
        view_redownloads: Redownloads from view-through impressions.
        total_avg_cpi: Average cost per install across attribution types.
        total_install_rate: Total installs divided by taps.
        tap_install_rate: Tap installs divided by taps.
        tap_pre_orders_placed: Pre-orders placed attributed to taps.
        view_pre_orders_placed: Pre-orders from view-through impressions.
        total_pre_orders_placed: Total pre-orders placed.
    """

    date: datetime.date | None = None
    local_spend: Money | None = Field(default=None, alias="localSpend")
    impressions: int | None = None
    taps: int | None = None
    ttr: float | None = None
    cpt: Money | None = None
    cpm: Money | None = None
    tap_installs: int | None = Field(default=None, alias="tapInstalls")
    tap_install_cpi: Money | None = Field(default=None, alias="tapInstallCPI")
    total_new_downloads: int | None = Field(default=None, alias="totalNewDownloads")
    total_redownloads: int | None = Field(default=None, alias="totalRedownloads")
    view_installs: int | None = Field(default=None, alias="viewInstalls")
    total_installs: int | None = Field(default=None, alias="totalInstalls")
    tap_new_downloads: int | None = Field(default=None, alias="tapNewDownloads")
    tap_redownloads: int | None = Field(default=None, alias="tapRedownloads")
    view_new_downloads: int | None = Field(default=None, alias="viewNewDownloads")
    view_redownloads: int | None = Field(default=None, alias="viewRedownloads")
    total_avg_cpi: Money | None = Field(default=None, alias="totalAvgCPI")
    total_install_rate: float | None = Field(default=None, alias="totalInstallRate")
    tap_install_rate: float | None = Field(default=None, alias="tapInstallRate")
    tap_pre_orders_placed: int | None = Field(default=None, alias="tapPreOrdersPlaced")
    view_pre_orders_placed: int | None = Field(default=None, alias="viewPreOrdersPlaced")
    total_pre_orders_placed: int | None = Field(default=None, alias="totalPreOrdersPlaced")


class AppsCampaignMetrics(AppsMetrics):
    """Campaign-level APPS metrics (inherits all ``AppsMetrics``)."""


class AppsAdGroupMetrics(AppsMetrics):
    """Ad group-level APPS metrics (inherits all ``AppsMetrics``)."""


# ---------------------------------------------------------------------------
# BRANDS metrics
# ---------------------------------------------------------------------------


class ActionMetrics(V1Model):
    """Action count metrics broken down by attribution type.

    Attributes:
        tap: Action count attributed to taps.
    """

    tap: int | None = None


class CostMetrics(V1Model):
    """Cost metrics broken down by attribution type.

    Attributes:
        tap: Cost attributed to taps, in the reporting currency.
    """

    tap: Money | None = None


class RateMetrics(V1Model):
    """Rate metrics broken down by attribution type.

    Attributes:
        tap: Rate attributed to taps as a decimal (0.035 is 3.5%).
    """

    tap: float | None = None


class BrandsMetrics(V1Model):
    """Metrics for the BRANDS promoted object type.

    Attributes:
        date: Report date (present in granular metrics).
        local_spend: Total spend.
        impressions: Total ad impressions.
        taps: Total ad taps.
        ttr: Tap-through rate.
        cpt: Average cost per tap.
        cpm: Average cost per thousand impressions.
        first_actions: First-time action counts.
        first_actions_per_tap: First-action rates per tap.
        first_actions_per_impression: First-action rates per impression.
        cost_per_first_action: Cost per first action.
        actions: Total action counts.
        cost_per_action: Cost per action.
        get_directions: Get-directions action counts.
        tap_url: Tap-URL action counts.
        call: Call action counts.
        share: Share action counts.
        get_the_app: Get-the-app action counts.
        gallery_engagement: Gallery engagement action counts.
        actions_per_tap: Total actions per tap rate.
        actions_per_impression: Total actions per impression rate.
    """

    date: datetime.date | None = None
    local_spend: Money | None = Field(default=None, alias="localSpend")
    impressions: int | None = None
    taps: int | None = None
    ttr: float | None = None
    cpt: Money | None = None
    cpm: Money | None = None
    first_actions: ActionMetrics | None = Field(default=None, alias="firstActions")
    first_actions_per_tap: RateMetrics | None = Field(default=None, alias="firstActionsPerTap")
    first_actions_per_impression: RateMetrics | None = Field(
        default=None, alias="firstActionsPerImpression"
    )
    cost_per_first_action: CostMetrics | None = Field(default=None, alias="costPerFirstAction")
    actions: ActionMetrics | None = None
    cost_per_action: CostMetrics | None = Field(default=None, alias="costPerAction")
    get_directions: ActionMetrics | None = Field(default=None, alias="getDirections")
    tap_url: ActionMetrics | None = Field(default=None, alias="tapURL")
    call: ActionMetrics | None = None
    share: ActionMetrics | None = None
    get_the_app: ActionMetrics | None = Field(default=None, alias="getTheApp")
    gallery_engagement: ActionMetrics | None = Field(default=None, alias="galleryEngagement")
    actions_per_tap: RateMetrics | None = Field(default=None, alias="actionsPerTap")
    actions_per_impression: RateMetrics | None = Field(default=None, alias="actionsPerImpression")


class BrandsCampaignMetrics(BrandsMetrics):
    """Campaign-level BRANDS metrics (inherits all ``BrandsMetrics``)."""


class BrandsAdGroupMetrics(BrandsMetrics):
    """Ad group-level BRANDS metrics (inherits all ``BrandsMetrics``)."""


# ---------------------------------------------------------------------------
# APPS report metadata
# ---------------------------------------------------------------------------


class AppsReportingCampaign(V1Model):
    """Campaign metadata for APPS report rows.

    Attributes:
        id: The campaign's unique identifier.
        promoted_object: Promoted object details.
        promoted_object_type: Always ``APPSTORE_APP`` for Apple Ads.
        promoted_object_id: Adam ID of the promoted App Store app.
        name: Campaign name at report time.
        status: Advertiser-configured run state.
        deleted: Whether the campaign has been soft-deleted.
        display_status: Rolled-up delivery state label.
        modification_time: Last modification timestamp.
        creation_time: Creation timestamp.
        ad_account_id: Owning ad account.
        system_status: System-evaluated delivery state.
        system_status_reasons: Reasons for the current system status.
        billing_event: The campaign's billing event.
        system_status_limiting_reasons: Reasons limiting delivery.
        targeting: Targeting projection.
        daily_budget: Daily budget.
        start_time: Campaign start time.
        end_time: Campaign end time.
        lifetime_budget: Lifetime budget.
        bid_strategy: Bid strategy configuration.
        ad_channel_type: Advertising channel type.
        country_or_region: groupBy dimension value.
        device_class: groupBy dimension value.
        gender: groupBy dimension value.
        age_range: groupBy dimension value.
        locality: groupBy dimension value.
        country_code: groupBy dimension value.
        admin_area: groupBy dimension value.
    """

    id: int | None = None
    promoted_object: PromotedObject | None = Field(default=None, alias="promotedObject")
    promoted_object_type: str | None = Field(default=None, alias="promotedObjectType")
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    name: str | None = None
    status: ReportingStatus | None = None
    deleted: bool | None = None
    display_status: str | None = Field(default=None, alias="displayStatus")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    system_status: ReportingSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[CampaignSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    billing_event: ReportingBillingEvent | None = Field(default=None, alias="billingEvent")
    system_status_limiting_reasons: list[str] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    targeting: AppsTargetingProjection | None = None
    daily_budget: ReportingMoney | None = Field(default=None, alias="dailyBudget")
    start_time: datetime.datetime | None = Field(default=None, alias="startTime")
    end_time: datetime.datetime | None = Field(default=None, alias="endTime")
    lifetime_budget: ReportingMoney | None = Field(default=None, alias="lifetimeBudget")
    bid_strategy: ReportingBidStrategy | None = Field(default=None, alias="bidStrategy")
    ad_channel_type: ReportingAdChannelType | None = Field(default=None, alias="adChannelType")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")
    gender: str | None = None
    age_range: str | None = Field(default=None, alias="ageRange")
    locality: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")
    admin_area: str | None = Field(default=None, alias="adminArea")


class AppsReportingAdGroup(V1Model):
    """Ad group metadata for APPS report rows.

    Attributes:
        id: The ad group's unique identifier.
        campaign_id: Owning campaign.
        ad_account_id: Owning ad account.
        name: Ad group name at report time.
        status: Advertiser-configured serving state.
        deleted: Whether the ad group has been soft-deleted.
        system_status: System-evaluated delivery state.
        system_status_reasons: Reasons for the current system status.
        system_status_limiting_reasons: Reasons limiting delivery.
        automated_keywords_opt_in: Automated keywords opt-in flag.
        automated_keywords_required: Automated keywords required flag.
        pricing_model: The ad group's pricing model.
        display_status: Rolled-up delivery state label.
        modification_time: Last modification timestamp.
        creation_time: Creation timestamp.
        start_time: Ad group start time.
        end_time: Ad group end time.
        campaign: Minimal parent campaign context.
        cpa_cap: CPA cap amount.
        bid_strategy: Bid strategy configuration.
        country_or_region: groupBy dimension value.
        device_class: groupBy dimension value.
        gender: groupBy dimension value.
        age_range: groupBy dimension value.
        locality: groupBy dimension value.
        country_code: groupBy dimension value.
        admin_area: groupBy dimension value.
    """

    id: int | None = None
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    name: str | None = None
    status: ReportingStatus | None = None
    deleted: bool | None = None
    system_status: ReportingSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[AdGroupSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    system_status_limiting_reasons: list[str] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    automated_keywords_opt_in: bool | None = Field(default=None, alias="automatedKeywordsOptIn")
    automated_keywords_required: bool | None = Field(
        default=None, alias="automatedKeywordsRequired"
    )
    pricing_model: ReportingPricingModel | None = Field(default=None, alias="pricingModel")
    display_status: str | None = Field(default=None, alias="displayStatus")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    start_time: datetime.datetime | None = Field(default=None, alias="startTime")
    end_time: datetime.datetime | None = Field(default=None, alias="endTime")
    campaign: ReportingCampaignMin | None = None
    cpa_cap: ReportingMoney | None = Field(default=None, alias="cpaCap")
    bid_strategy: ReportingBidStrategy | None = Field(default=None, alias="bidStrategy")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")
    gender: str | None = None
    age_range: str | None = Field(default=None, alias="ageRange")
    locality: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")
    admin_area: str | None = Field(default=None, alias="adminArea")


class AppsReportingCreative(V1Model):
    """Creative metadata for APPS ads.

    Attributes:
        id: The creative's unique identifier.
        creative_type: Creative type at report time.
        system_status: System-evaluated validation state.
        creative_spec: Creative specification (language).
        destination: Post-tap destination details.
    """

    id: int | None = None
    creative_type: AppsCreativeType | None = Field(default=None, alias="creativeType")
    system_status: ReportingCreativeSystemStatus | None = Field(default=None, alias="systemStatus")
    creative_spec: ReportingCreativeSpec | None = Field(default=None, alias="creativeSpec")
    destination: ReportingDestination | None = None


class AppsReportingAd(V1Model):
    """Ad metadata for APPS report rows.

    Attributes:
        id: The ad's unique identifier.
        name: Ad name at report time.
        deleted: Whether the ad has been soft-deleted.
        status: Advertiser-configured serving state.
        system_status: System-evaluated delivery state.
        system_status_reasons: Reasons for the current system status.
        system_status_limiting_reasons: Reasons limiting delivery.
        ad_account_id: Owning ad account.
        campaign_id: Owning campaign.
        ad_group_id: Owning ad group.
        creation_time: Creation timestamp.
        modification_time: Last modification timestamp.
        display_status: Rolled-up delivery state label.
        creative: Creative details for the ad.
        country_or_region: groupBy dimension value.
        device_class: groupBy dimension value.
    """

    id: int | None = None
    name: str | None = None
    deleted: bool | None = None
    status: ReportingStatus | None = None
    system_status: ReportingSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[AdSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    system_status_limiting_reasons: list[str] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    display_status: str | None = Field(default=None, alias="displayStatus")
    creative: AppsReportingCreative | None = None
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")


class ReportingKeyword(V1Model):
    """Keyword metadata in an APPS report row.

    Attributes:
        id: The keyword identifier.
        campaign_id: Owning campaign.
        ad_account_id: Owning ad account.
        deleted: Whether the keyword has been deleted.
        text: The keyword text.
        status: Keyword status.
        match_type: Keyword match type (``BROAD`` or ``EXACT``).
        bid: The keyword bid.
        ad_group_id: Owning ad group.
        modification_time: Last modification timestamp.
        creation_time: Creation timestamp.
        display_status: Computed display status.
        ad_group: Minimal ad group context.
        country_or_region: groupBy dimension value.
        device_class: groupBy dimension value.
    """

    id: int | None = None
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    deleted: bool | None = None
    text: str | None = None
    status: ReportingKeywordStatus | None = None
    match_type: AppsKeywordMatchType | None = Field(default=None, alias="matchType")
    bid: Money | None = None
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    display_status: str | None = Field(default=None, alias="displayStatus")
    ad_group: ReportingAdGroupMin | None = Field(default=None, alias="adGroup")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")


class ReportingSearchTerm(V1Model):
    """Search term metadata in an APPS report row.

    Attributes:
        campaign_id: Owning campaign.
        ad_account_id: Owning ad account.
        search_term_text: The actual user-entered query string.
        search_term_source: Direct user search or auto-match source.
        keyword: The matched keyword.
        ad_group_id: Owning ad group.
        ad_group: Minimal ad group context.
        country_or_region: groupBy dimension value.
        device_class: groupBy dimension value.
    """

    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    search_term_text: str | None = Field(default=None, alias="searchTermText")
    search_term_source: str | None = Field(default=None, alias="searchTermSource")
    keyword: ReportingKeyword | None = None
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    ad_group: ReportingAdGroupMin | None = Field(default=None, alias="adGroup")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")


# ---------------------------------------------------------------------------
# BRANDS report metadata
# ---------------------------------------------------------------------------


class BrandsReportingCampaign(V1Model):
    """Campaign metadata for BRANDS (Apple Maps) report rows.

    Attributes:
        id: The campaign's unique identifier.
        promoted_object: Promoted object details.
        promoted_object_type: ``BUSINESS_BRAND`` for Maps campaigns.
        promoted_object_id: Brand ID of the promoted Maps business.
        name: Campaign name at report time.
        status: Advertiser-configured run state.
        deleted: Whether the campaign has been soft-deleted.
        display_status: Rolled-up delivery state label.
        modification_time: Last modification timestamp.
        creation_time: Creation timestamp.
        ad_account_id: Owning ad account.
        system_status: System-evaluated delivery state.
        system_status_reasons: Reasons for the current system status.
        billing_event: The campaign's billing event.
        system_status_limiting_reasons: Reasons limiting delivery.
        targeting: Targeting projection.
        daily_budget: Daily budget.
        start_time: Campaign start time.
        end_time: Campaign end time.
        lifetime_budget: Lifetime budget.
        bid_strategy: Bid strategy configuration.
        ad_channel_type: Advertising channel type.
        device_class: groupBy dimension value.
        location_id: groupBy dimension value.
        supply_placement: groupBy dimension value.
    """

    id: int | None = None
    promoted_object: PromotedObject | None = Field(default=None, alias="promotedObject")
    promoted_object_type: str | None = Field(default=None, alias="promotedObjectType")
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    name: str | None = None
    status: ReportingStatus | None = None
    deleted: bool | None = None
    display_status: str | None = Field(default=None, alias="displayStatus")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    system_status: ReportingSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[CampaignSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    billing_event: ReportingBillingEvent | None = Field(default=None, alias="billingEvent")
    system_status_limiting_reasons: list[str] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    targeting: BrandsTargetingProjection | None = None
    daily_budget: ReportingMoney | None = Field(default=None, alias="dailyBudget")
    start_time: datetime.datetime | None = Field(default=None, alias="startTime")
    end_time: datetime.datetime | None = Field(default=None, alias="endTime")
    lifetime_budget: ReportingMoney | None = Field(default=None, alias="lifetimeBudget")
    bid_strategy: ReportingBidStrategy | None = Field(default=None, alias="bidStrategy")
    ad_channel_type: ReportingAdChannelType | None = Field(default=None, alias="adChannelType")
    device_class: str | None = Field(default=None, alias="deviceClass")
    location_id: str | None = Field(default=None, alias="locationId")
    supply_placement: str | None = Field(default=None, alias="supplyPlacement")


class BrandsReportingAdGroup(V1Model):
    """Ad group metadata for BRANDS report rows.

    Attributes:
        id: The ad group's unique identifier.
        campaign_id: Owning campaign.
        ad_account_id: Owning ad account.
        name: Ad group name at report time.
        status: Advertiser-configured serving state.
        deleted: Whether the ad group has been soft-deleted.
        system_status: System-evaluated delivery state.
        system_status_reasons: Reasons for the current system status.
        system_status_limiting_reasons: Reasons limiting delivery.
        automated_keywords_opt_in: Automated keywords opt-in flag.
        automated_keywords_required: Automated keywords required flag.
        pricing_model: The ad group's pricing model.
        display_status: Rolled-up delivery state label.
        modification_time: Last modification timestamp.
        creation_time: Creation timestamp.
        start_time: Ad group start time.
        end_time: Ad group end time.
        campaign: Minimal parent campaign context.
        bid_strategy: Bid strategy configuration.
        targeting: Targeting projection.
        device_class: groupBy dimension value.
        location_id: groupBy dimension value.
        supply_placement: groupBy dimension value.
    """

    id: int | None = None
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    name: str | None = None
    status: ReportingStatus | None = None
    deleted: bool | None = None
    system_status: ReportingSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[AdGroupSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    system_status_limiting_reasons: list[str] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    automated_keywords_opt_in: bool | None = Field(default=None, alias="automatedKeywordsOptIn")
    automated_keywords_required: bool | None = Field(
        default=None, alias="automatedKeywordsRequired"
    )
    pricing_model: ReportingPricingModel | None = Field(default=None, alias="pricingModel")
    display_status: str | None = Field(default=None, alias="displayStatus")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    start_time: datetime.datetime | None = Field(default=None, alias="startTime")
    end_time: datetime.datetime | None = Field(default=None, alias="endTime")
    campaign: ReportingCampaignMin | None = None
    bid_strategy: ReportingBidStrategy | None = Field(default=None, alias="bidStrategy")
    targeting: BrandsTargetingProjection | None = None
    device_class: str | None = Field(default=None, alias="deviceClass")
    location_id: str | None = Field(default=None, alias="locationId")
    supply_placement: str | None = Field(default=None, alias="supplyPlacement")


class BrandsReportingCreative(V1Model):
    """Creative metadata for BRANDS ads.

    Attributes:
        id: The creative's unique identifier.
        creative_type: Creative type at report time.
        system_status: System-evaluated validation state.
    """

    id: int | None = None
    creative_type: BrandsCreativeType | None = Field(default=None, alias="creativeType")
    system_status: ReportingCreativeSystemStatus | None = Field(default=None, alias="systemStatus")


class BrandsReportingAd(V1Model):
    """Ad metadata for BRANDS report rows.

    There is no flat ``creativeId`` field; the creative is the nested
    ``creative`` object.

    Attributes:
        id: The ad's unique identifier.
        name: Ad name at report time.
        deleted: Whether the ad has been soft-deleted.
        status: Advertiser-configured serving state.
        system_status: System-evaluated delivery state.
        system_status_reasons: Reasons for the current system status.
        system_status_limiting_reasons: Reasons limiting delivery.
        ad_account_id: Owning ad account.
        campaign_id: Owning campaign.
        ad_group_id: Owning ad group.
        creation_time: Creation timestamp.
        modification_time: Last modification timestamp.
        display_status: Rolled-up delivery state label.
        creative: Creative details for the ad.
        device_class: groupBy dimension value.
        location_id: groupBy dimension value.
        supply_placement: groupBy dimension value.
    """

    id: int | None = None
    name: str | None = None
    deleted: bool | None = None
    status: ReportingStatus | None = None
    system_status: ReportingSystemStatus | None = Field(default=None, alias="systemStatus")
    system_status_reasons: list[AdSystemStatusReason] | None = Field(
        default=None, alias="systemStatusReasons"
    )
    system_status_limiting_reasons: list[str] | None = Field(
        default=None, alias="systemStatusLimitingReasons"
    )
    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    campaign_id: int | None = Field(default=None, alias="campaignId")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    display_status: str | None = Field(default=None, alias="displayStatus")
    creative: BrandsReportingCreative | None = None
    device_class: str | None = Field(default=None, alias="deviceClass")
    location_id: str | None = Field(default=None, alias="locationId")
    supply_placement: str | None = Field(default=None, alias="supplyPlacement")


class BrandsReportingKeyword(V1Model):
    """Keyword metadata for BRANDS report rows.

    Attributes:
        ad_account_id: Owning ad account.
        ad_group: Minimal ad group context.
        ad_group_id: Owning ad group.
        bid: The keyword bid.
        campaign_id: Owning campaign.
        country_or_region: groupBy dimension value.
        creation_time: Creation timestamp.
        deleted: Whether the keyword has been deleted.
        device_class: groupBy dimension value.
        display_status: Computed display status.
        id: The keyword identifier.
        location_id: groupBy dimension value.
        match_type: Maps match type (``PHRASE`` or ``CATEGORY``).
        modification_time: Last modification timestamp.
        status: Keyword status.
        text: The keyword text.
    """

    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    ad_group: ReportingAdGroupMin | None = Field(default=None, alias="adGroup")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    bid: Money | None = None
    campaign_id: int | None = Field(default=None, alias="campaignId")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    creation_time: datetime.datetime | None = Field(default=None, alias="creationTime")
    deleted: bool | None = None
    device_class: str | None = Field(default=None, alias="deviceClass")
    display_status: str | None = Field(default=None, alias="displayStatus")
    id: int | None = None
    location_id: str | None = Field(default=None, alias="locationId")
    match_type: BrandsKeywordMatchType | None = Field(default=None, alias="matchType")
    modification_time: datetime.datetime | None = Field(default=None, alias="modificationTime")
    status: ReportingKeywordStatus | None = None
    text: str | None = None


class BrandsReportingSearchTerm(V1Model):
    """Search term metadata for BRANDS report rows.

    Attributes:
        ad_account_id: Owning ad account.
        ad_group: Minimal ad group context.
        ad_group_id: Owning ad group.
        campaign_id: Owning campaign.
        country_or_region: groupBy dimension value.
        device_class: groupBy dimension value.
        keyword: The matched Maps keyword.
        location_id: groupBy dimension value.
        search_term_source: Direct user search or auto-match source.
        search_term_text: The actual user-entered query string.
    """

    ad_account_id: int | None = Field(default=None, alias="adAccountId")
    ad_group: ReportingAdGroupMin | None = Field(default=None, alias="adGroup")
    ad_group_id: int | None = Field(default=None, alias="adGroupId")
    campaign_id: int | None = Field(default=None, alias="campaignId")
    country_or_region: str | None = Field(default=None, alias="countryOrRegion")
    device_class: str | None = Field(default=None, alias="deviceClass")
    keyword: BrandsReportingKeyword | None = None
    location_id: str | None = Field(default=None, alias="locationId")
    search_term_source: str | None = Field(default=None, alias="searchTermSource")
    search_term_text: str | None = Field(default=None, alias="searchTermText")


# ---------------------------------------------------------------------------
# APPS report rows, summaries, containers, responses
# ---------------------------------------------------------------------------


class AppsCampaignReportRow(V1Model):
    """A single row in an APPS campaign report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Campaign metadata for this row.
    """

    total_metrics: AppsCampaignMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[AppsCampaignMetrics] | None = Field(
        default=None, alias="granularMetrics"
    )
    metadata: AppsReportingCampaign | None = None


class AppsCampaignReportSummary(V1Model):
    """Grand-total metrics across all APPS campaign report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: AppsCampaignMetrics | None = Field(default=None, alias="grandTotal")


class AppsCampaignResultContainer(V1Model):
    """APPS campaign report rows plus an optional grand-total summary.

    Attributes:
        rows: The campaign report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[AppsCampaignReportRow] | None = None
    summary: AppsCampaignReportSummary | None = None


class AppsCampaignReportResponse(V1Model):
    """Response envelope for APPS campaign-level reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details; the transport raises before this is ever
            populated on returned instances.
    """

    result: AppsCampaignResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class AppsAdGroupReportRow(V1Model):
    """A single row in an APPS ad group report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Ad group metadata for this row.
    """

    total_metrics: AppsAdGroupMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[AppsAdGroupMetrics] | None = Field(default=None, alias="granularMetrics")
    metadata: AppsReportingAdGroup | None = None


class AppsAdGroupReportSummary(V1Model):
    """Grand-total metrics across all APPS ad group report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: AppsAdGroupMetrics | None = Field(default=None, alias="grandTotal")


class AppsAdGroupResultContainer(V1Model):
    """APPS ad group report rows plus an optional grand-total summary.

    Attributes:
        rows: The ad group report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[AppsAdGroupReportRow] | None = None
    summary: AppsAdGroupReportSummary | None = None


class AppsAdGroupReportResponse(V1Model):
    """Response envelope for APPS ad group reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: AppsAdGroupResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class AppsAdReportRow(V1Model):
    """A single row in an APPS ad-level report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Ad metadata for this row.
    """

    total_metrics: AppsMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[AppsMetrics] | None = Field(default=None, alias="granularMetrics")
    metadata: AppsReportingAd | None = None


class AppsAdReportSummary(V1Model):
    """Grand-total metrics across all APPS ad-level report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: AppsMetrics | None = Field(default=None, alias="grandTotal")


class AppsAdResultContainer(V1Model):
    """APPS ad-level report rows plus an optional grand-total summary.

    Attributes:
        rows: The ad-level report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[AppsAdReportRow] | None = None
    summary: AppsAdReportSummary | None = None


class AppsAdReportResponse(V1Model):
    """Response envelope for APPS ad-level reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: AppsAdResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class AppsKeywordReportRow(V1Model):
    """A single row in an APPS keyword report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Keyword metadata for this row.
        insights: Optional keyword insights (bid recommendation).
    """

    total_metrics: AppsMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[AppsMetrics] | None = Field(default=None, alias="granularMetrics")
    metadata: ReportingKeyword | None = None
    insights: KeywordInsights | None = None


class AppsKeywordReportSummary(V1Model):
    """Grand-total metrics across all APPS keyword report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: AppsMetrics | None = Field(default=None, alias="grandTotal")


class AppsKeywordResultContainer(V1Model):
    """APPS keyword report rows plus an optional grand-total summary.

    Attributes:
        rows: The keyword report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[AppsKeywordReportRow] | None = None
    summary: AppsKeywordReportSummary | None = None


class AppsKeywordReportResponse(V1Model):
    """Response envelope for APPS keyword-level reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: AppsKeywordResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class AppsSearchTermReportRow(V1Model):
    """A single row in an APPS search term report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Search term metadata for this row.
    """

    total_metrics: AppsMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[AppsMetrics] | None = Field(default=None, alias="granularMetrics")
    metadata: ReportingSearchTerm | None = None


class AppsSearchTermReportSummary(V1Model):
    """Grand-total metrics across all APPS search term report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: AppsMetrics | None = Field(default=None, alias="grandTotal")


class AppsSearchTermResultContainer(V1Model):
    """APPS search term report rows plus an optional grand-total summary.

    Attributes:
        rows: The search term report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[AppsSearchTermReportRow] | None = None
    summary: AppsSearchTermReportSummary | None = None


class AppsSearchTermReportResponse(V1Model):
    """Response envelope for APPS search term reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: AppsSearchTermResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


# ---------------------------------------------------------------------------
# BRANDS report rows, summaries, containers, responses
# ---------------------------------------------------------------------------


class BrandsCampaignReportRow(V1Model):
    """A single row in a BRANDS campaign report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Campaign metadata for this row.
    """

    total_metrics: BrandsCampaignMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[BrandsCampaignMetrics] | None = Field(
        default=None, alias="granularMetrics"
    )
    metadata: BrandsReportingCampaign | None = None


class BrandsCampaignReportSummary(V1Model):
    """Grand-total metrics across all BRANDS campaign report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: BrandsCampaignMetrics | None = Field(default=None, alias="grandTotal")


class BrandsCampaignResultContainer(V1Model):
    """BRANDS campaign report rows plus an optional grand-total summary.

    Attributes:
        rows: The campaign report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[BrandsCampaignReportRow] | None = None
    summary: BrandsCampaignReportSummary | None = None


class BrandsCampaignReportResponse(V1Model):
    """Response envelope for BRANDS campaign-level reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: BrandsCampaignResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class BrandsAdGroupReportRow(V1Model):
    """A single row in a BRANDS ad group report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Ad group metadata for this row.
    """

    total_metrics: BrandsAdGroupMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[BrandsAdGroupMetrics] | None = Field(
        default=None, alias="granularMetrics"
    )
    metadata: BrandsReportingAdGroup | None = None


class BrandsAdGroupReportSummary(V1Model):
    """Grand-total metrics across all BRANDS ad group report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: BrandsAdGroupMetrics | None = Field(default=None, alias="grandTotal")


class BrandsAdGroupResultContainer(V1Model):
    """BRANDS ad group report rows plus an optional grand-total summary.

    Attributes:
        rows: The ad group report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[BrandsAdGroupReportRow] | None = None
    summary: BrandsAdGroupReportSummary | None = None


class BrandsAdGroupReportResponse(V1Model):
    """Response envelope for BRANDS ad group reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: BrandsAdGroupResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class BrandsAdReportRow(V1Model):
    """A single row in a BRANDS ad-level report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Ad metadata for this row.
    """

    total_metrics: BrandsMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[BrandsMetrics] | None = Field(default=None, alias="granularMetrics")
    metadata: BrandsReportingAd | None = None


class BrandsAdReportSummary(V1Model):
    """Grand-total metrics across all BRANDS ad-level report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: BrandsMetrics | None = Field(default=None, alias="grandTotal")


class BrandsAdResultContainer(V1Model):
    """BRANDS ad-level report rows plus an optional grand-total summary.

    Attributes:
        rows: The ad-level report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[BrandsAdReportRow] | None = None
    summary: BrandsAdReportSummary | None = None


class BrandsAdReportResponse(V1Model):
    """Response envelope for BRANDS ad-level reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: BrandsAdResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class BrandsKeywordReportRow(V1Model):
    """A single row in a BRANDS keyword report.

    Attributes:
        metadata: Keyword metadata for this row.
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        insights: Optional keyword insights (bid recommendation).
    """

    metadata: BrandsReportingKeyword | None = None
    total_metrics: BrandsMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[BrandsMetrics] | None = Field(default=None, alias="granularMetrics")
    insights: KeywordInsights | None = None


class BrandsKeywordReportSummary(V1Model):
    """Grand-total metrics across all BRANDS keyword report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: BrandsMetrics | None = Field(default=None, alias="grandTotal")


class BrandsKeywordResultContainer(V1Model):
    """BRANDS keyword report rows plus an optional grand-total summary.

    Attributes:
        rows: The keyword report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[BrandsKeywordReportRow] | None = None
    summary: BrandsKeywordReportSummary | None = None


class BrandsKeywordReportResponse(V1Model):
    """Response envelope for BRANDS keyword-level reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: BrandsKeywordResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None


class BrandsSearchTermReportRow(V1Model):
    """A single row in a BRANDS search term report.

    Attributes:
        total_metrics: Metrics aggregated over the full date range.
        granular_metrics: Time-series metrics; present only when the
            request specifies a granularity.
        metadata: Search term metadata for this row.
    """

    total_metrics: BrandsMetrics | None = Field(default=None, alias="totalMetrics")
    granular_metrics: list[BrandsMetrics] | None = Field(default=None, alias="granularMetrics")
    metadata: BrandsReportingSearchTerm | None = None


class BrandsSearchTermReportSummary(V1Model):
    """Grand-total metrics across all BRANDS search term report rows.

    Attributes:
        grand_total: The aggregated metrics.
    """

    grand_total: BrandsMetrics | None = Field(default=None, alias="grandTotal")


class BrandsSearchTermResultContainer(V1Model):
    """BRANDS search term report rows plus an optional summary.

    Attributes:
        rows: The search term report rows.
        summary: Grand-total summary (when ``GRAND_TOTAL`` requested).
    """

    rows: list[BrandsSearchTermReportRow] | None = None
    summary: BrandsSearchTermReportSummary | None = None


class BrandsSearchTermReportResponse(V1Model):
    """Response envelope for BRANDS search term reports.

    Attributes:
        result: The result container with rows and summary.
        pagination: Pagination metadata.
        error: Error details (always None on returned instances).
    """

    result: BrandsSearchTermResultContainer | None = None
    pagination: V1Pagination | None = None
    error: V1Error | None = None
