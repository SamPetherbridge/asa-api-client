"""Models for the Apple Ads Platform API v1 recommendations group.

Covers system-generated optimization suggestions for campaigns: daily
budget recommendations (campaigns frequently hitting their spending
ceiling) and Target CPA recommendations (campaigns using a Maximize
Conversions bid strategy). Recommendations document their own query,
filter, sorting, and pagination request objects, which differ from the
generic v1 :class:`~asa_api_client.v1.query.Query` body: filter values
are always arrays of strings, query pagination has no
``fetchTotalCount``, and the operator set is narrower. Apply and
dismiss request bodies are bare JSON arrays of request objects.
"""

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import Field

from asa_api_client.v1.models.base import Money, V1Model


class RecommendationPromotedObjectType(StrEnum):
    """The type of promoted object a recommendation applies to.

    Attributes:
        APPSTORE_APP: The campaign promotes an iOS app;
            ``promotedObjectId`` is the app's adam ID.
        BUSINESS_BRAND: The campaign promotes a brand on Apple Maps;
            ``promotedObjectId`` is the brand identifier.
    """

    APPSTORE_APP = "APPSTORE_APP"
    BUSINESS_BRAND = "BUSINESS_BRAND"


class RecommendationState(StrEnum):
    """The lifecycle state of a recommendation (the advertiser's response).

    Only ``AVAILABLE`` recommendations can be applied or dismissed.

    Attributes:
        AVAILABLE: Active and not yet acted on; the initial state.
        APPLIED: Accepted; the suggested change was applied. Terminal.
        DISMISSED: Explicitly rejected; no change made. Terminal.
        DELETE: Archived by the system (the underlying entity was
            removed or the recommendation became irrelevant). Terminal.
            Note the documented value is ``DELETE``, not ``DELETED``.
    """

    AVAILABLE = "AVAILABLE"
    APPLIED = "APPLIED"
    DISMISSED = "DISMISSED"
    DELETE = "DELETE"


class RecommendationStatus(StrEnum):
    """System-level operational status of a recommendation record.

    Independent of :class:`RecommendationState` — a record can be
    ``ENABLED`` while ``APPLIED`` or ``DISMISSED``.

    Attributes:
        ENABLED: The record is active and operational. Default.
        DISABLED: Administratively disabled but not removed.
        DELETED: Permanently deleted; can no longer be retrieved.
    """

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    DELETED = "DELETED"


class RecommendationCategory(StrEnum):
    """Categorizes a recommendation by optimization area and origin.

    Each area has a merged category (no prefix) and a system-generated
    (``S``-prefixed) category. Use the merged value in query filters
    unless you specifically need algorithm-generated-only results.

    Attributes:
        KEYWORD: Merged view of all keyword recommendations.
        SKEYWORD: System-generated keyword recommendation.
        DAILYCAP: Merged view of all daily budget recommendations.
        SDAILYCAP: System-generated daily budget recommendation.
        TCPA: Merged view of all Target CPA recommendations.
        STCPA: System-generated Target CPA recommendation.
        BID: Merged view of all bid recommendations.
        SBID: System-generated bid recommendation.
    """

    KEYWORD = "KEYWORD"
    SKEYWORD = "SKEYWORD"
    DAILYCAP = "DAILYCAP"
    SDAILYCAP = "SDAILYCAP"
    TCPA = "TCPA"
    STCPA = "STCPA"
    BID = "BID"
    SBID = "SBID"


class RecommendationFilterOperator(StrEnum):
    """Comparison operators supported in recommendation query filters.

    Narrower than the generic v1 operator set; an operator incompatible
    with a field's type returns a 400 validation error.

    Attributes:
        EQUALS: Exact match against a single filter value.
        NOT_EQUALS: Excludes records matching the filter value.
        IN: Field value must match one of the filter values.
        CONTAINS_ANY: List field contains at least one filter value.
        CONTAINS_ALL: List field contains every filter value.
        LESS_THAN: Numeric or date comparison.
        LESS_THAN_OR_EQUAL_TO: Numeric or date comparison.
        GREATER_THAN: Numeric or date comparison.
        GREATER_THAN_OR_EQUAL_TO: Numeric or date comparison.
        BETWEEN: Inclusive range; supply exactly two values.
        STARTS_WITH: String prefix match.
        ENDS_WITH: String suffix match.
        LIKE: Pattern match supporting ``%`` as a wildcard.
    """

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"
    CONTAINS_ANY = "CONTAINS_ANY"
    CONTAINS_ALL = "CONTAINS_ALL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL_TO = "LESS_THAN_OR_EQUAL_TO"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL_TO = "GREATER_THAN_OR_EQUAL_TO"
    BETWEEN = "BETWEEN"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    LIKE = "LIKE"


class RecommendationSortingOrder(StrEnum):
    """Sort direction for recommendation query sorting entries.

    Attributes:
        ASC: Ascending order; the default when ``order`` is omitted.
        DESC: Descending order.
    """

    ASC = "ASC"
    DESC = "DESC"


class RecommendationFilterCondition(V1Model):
    """One filter condition in a recommendation query's ``filters`` array.

    All conditions combine with AND logic. ``value`` is always an array
    of strings, even for single or numeric values (e.g. a campaignId
    BETWEEN uses ``["10000", "20000"]``).

    Attributes:
        field: Field name on the recommendation object being queried,
            e.g. ``"state"``, ``"promotedObjectId"``, ``"campaignId"``.
        operator: Comparison operator; valid operators depend on the
            field's type.
        value: Filter values, always as an array of strings.
        ignore_case: Case-insensitive string matching when True.
            Defaults to False server-side; omitted when unset.
    """

    field: str
    operator: RecommendationFilterOperator
    value: list[str]
    ignore_case: bool | None = Field(default=None, alias="ignoreCase")


class RecommendationSorting(V1Model):
    """One sort dimension in a recommendation query's ``sorting`` array.

    Entries apply in order: the first is the primary sort, the second
    the tiebreaker, and so on.

    Attributes:
        field: Field name to sort by, e.g. ``"creationTime"``.
        order: Sort direction; the server defaults to ``ASC`` when
            omitted.
    """

    field: str
    order: RecommendationSortingOrder | None = None


class RecommendationQueryPagination(V1Model):
    """Pagination parameters in recommendation query requests.

    Unlike the generic v1 query pagination, there is no
    ``fetchTotalCount`` flag — responses always report ``totalCount``.

    Attributes:
        offset: Zero-based index of the first result. Default 0.
        page_size: Maximum results per page. Default 20, maximum 1000.
    """

    offset: int | None = None
    page_size: int | None = Field(default=None, alias="pageSize")


class RecommendationQueryRequest(V1Model):
    """Request body for the recommendation ``POST .../query`` endpoints.

    Sent unwrapped (no named key). Filters on ``promotedObjectId`` and
    ``promotedObjectType`` are mandatory on every request; omitting
    either returns a 400 with a ``MISSING_REQUIRED_FILTER`` detail.
    Use :meth:`for_promoted_object` to build a compliant query.

    Attributes:
        filters: Filter conditions combined with AND logic.
        sorting: Sort dimensions applied in order.
        pagination: Offset/pageSize paging controls.
    """

    filters: list[RecommendationFilterCondition] | None = None
    sorting: list[RecommendationSorting] | None = None
    pagination: RecommendationQueryPagination | None = None

    @classmethod
    def for_promoted_object(
        cls,
        promoted_object_id: str,
        promoted_object_type: RecommendationPromotedObjectType | str,
        *,
        filters: list[RecommendationFilterCondition] | None = None,
        sorting: list[RecommendationSorting] | None = None,
        pagination: RecommendationQueryPagination | None = None,
    ) -> Self:
        """Build a query with the mandatory promoted-object filters.

        Args:
            promoted_object_id: App adam ID (``APPSTORE_APP``) or brand
                ID (``BUSINESS_BRAND``) to fetch recommendations for.
            promoted_object_type: The promoted object type.
            filters: Additional filter conditions, appended after the
                two mandatory EQUALS filters.
            sorting: Optional sort dimensions.
            pagination: Optional paging controls.

        Returns:
            A query request carrying the required filters.
        """
        object_type = RecommendationPromotedObjectType(promoted_object_type)
        required = [
            RecommendationFilterCondition(
                field="promotedObjectId",
                operator=RecommendationFilterOperator.EQUALS,
                value=[promoted_object_id],
            ),
            RecommendationFilterCondition(
                field="promotedObjectType",
                operator=RecommendationFilterOperator.EQUALS,
                value=[object_type.value],
            ),
        ]
        return cls(
            filters=[*required, *(filters or [])],
            sorting=sorting,
            pagination=pagination,
        )


class RecommendationBidStrategy(V1Model):
    """Bid strategy context attached to a recommendation.

    Attributes:
        bid_strategy_type: Type of bid strategy, e.g.
            ``"MAX_CONVERSIONS"`` (see the campaigns group's
            BidStrategyType for values).
        bid_strategy_goal: Goal of the bid strategy, e.g. ``"INSTALL"``.
        bid_amount: Bid amount associated with the strategy.
    """

    bid_strategy_type: str | None = Field(default=None, alias="bidStrategyType")
    bid_strategy_goal: str | None = Field(default=None, alias="bidStrategyGoal")
    bid_amount: Money | None = Field(default=None, alias="bidAmount")


class TargetCpaRecommendation(V1Model):
    """A Target CPA recommendation (read object).

    Surfaced for campaigns using a Maximize Conversions bid strategy;
    carries ``recommendationType: "TCPA"``. All fields are read-only.

    Attributes:
        id: Unique identifier for the recommendation.
        recommendation_type: Always ``TCPA`` on this object.
        promoted_object_id: App adam ID or brand ID.
        promoted_object_type: ``APPSTORE_APP`` or ``BUSINESS_BRAND``.
        campaign_id: The campaign the recommendation is for.
        campaign_name: Display name of the campaign.
        state: Lifecycle state; only ``AVAILABLE`` can be acted on.
        status: System-level operational status.
        recommended_target_cpa: The suggested new Target CPA.
        bid_strategy: The campaign's current bid strategy.
        average_cpt: Historical average cost per tap.
        average_cpa: Historical average cost per acquisition.
        expected_taps: Expected taps if applied (7-day projection).
        expected_cpa: Estimated 7-day average CPA after applying
            (wire alias ``expectedCPA`` — capitalized, unlike the
            daily-budget objects' ``expectedCpa``).
        expected_installs: Estimated 7-day installs after applying.
        expected_spend: Estimated 7-day spend after applying.
        impression: Historical impression count (singular field name).
        installs: Historical install count.
        spend: Historical spend.
        taps: Historical tap count.
        ttr: Historical tap-through rate.
        creation_time: When the recommendation was created.
        modification_time: When the recommendation was last modified.
        expiration_time: When the recommendation expires.
    """

    id: str | None = None
    recommendation_type: RecommendationCategory | None = Field(
        default=None, alias="recommendationType"
    )
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    promoted_object_type: RecommendationPromotedObjectType | None = Field(
        default=None, alias="promotedObjectType"
    )
    campaign_id: int | None = Field(default=None, alias="campaignId")
    campaign_name: str | None = Field(default=None, alias="campaignName")
    state: RecommendationState | None = None
    status: RecommendationStatus | None = None
    recommended_target_cpa: Money | None = Field(default=None, alias="recommendedTargetCPA")
    bid_strategy: RecommendationBidStrategy | None = Field(default=None, alias="bidStrategy")
    average_cpt: Money | None = Field(default=None, alias="averageCPT")
    average_cpa: Money | None = Field(default=None, alias="averageCPA")
    expected_taps: int | None = Field(default=None, alias="expectedTaps")
    expected_cpa: Money | None = Field(default=None, alias="expectedCPA")
    expected_installs: int | None = Field(default=None, alias="expectedInstalls")
    expected_spend: Money | None = Field(default=None, alias="expectedSpend")
    impression: int | None = None
    installs: int | None = None
    spend: Money | None = None
    taps: int | None = None
    ttr: float | None = None
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    expiration_time: datetime | None = Field(default=None, alias="expirationTime")


class TargetCpaRecommendationHistory(V1Model):
    """Immutable record of an applied or dismissed Target CPA recommendation.

    Returned by the target-cpas apply and dismiss endpoints. Note the
    ID field is ``recommendationId``, not ``id``. All fields read-only.

    Attributes:
        recommendation_id: ID of the original recommendation.
        recommendation_type: Always ``TCPA``.
        promoted_object_id: App adam ID or brand ID.
        promoted_object_type: ``APPSTORE_APP`` or ``BUSINESS_BRAND``.
        campaign_id: Campaign ID.
        campaign_name: Campaign display name.
        state: Terminal state — ``APPLIED`` or ``DISMISSED``.
        status: System-level operational status.
        applied_target_cpa: The Target CPA actually applied; None on
            dismiss.
        recommended_target_cpa: The originally recommended Target CPA.
        rank: Rank at the time of the action.
        installs: Historical install count.
        spend: Historical spend.
        average_cpa: Historical average CPA.
        average_cpt: Historical average CPT.
        impression: Historical impression count.
        taps: Historical tap count.
        ttr: Historical tap-through rate.
        expected_installs: Expected installs from the original
            recommendation.
        expected_spend: Expected spend from the original
            recommendation.
        expected_taps: Expected taps from the original recommendation.
        expected_cpa: Expected CPA (wire alias ``expectedCPA``).
        creation_time: When the original recommendation was created.
        modification_time: When this history record was last modified.
        applied_time: When the apply/dismiss action was taken.
        expiration_time: When the original recommendation would have
            expired.
    """

    recommendation_id: str | None = Field(default=None, alias="recommendationId")
    recommendation_type: RecommendationCategory | None = Field(
        default=None, alias="recommendationType"
    )
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    promoted_object_type: RecommendationPromotedObjectType | None = Field(
        default=None, alias="promotedObjectType"
    )
    campaign_id: int | None = Field(default=None, alias="campaignId")
    campaign_name: str | None = Field(default=None, alias="campaignName")
    state: RecommendationState | None = None
    status: RecommendationStatus | None = None
    applied_target_cpa: Money | None = Field(default=None, alias="appliedTargetCPA")
    recommended_target_cpa: Money | None = Field(default=None, alias="recommendedTargetCPA")
    rank: int | None = None
    installs: int | None = None
    spend: Money | None = None
    average_cpa: Money | None = Field(default=None, alias="averageCPA")
    average_cpt: Money | None = Field(default=None, alias="averageCPT")
    impression: int | None = None
    taps: int | None = None
    ttr: float | None = None
    expected_installs: int | None = Field(default=None, alias="expectedInstalls")
    expected_spend: Money | None = Field(default=None, alias="expectedSpend")
    expected_taps: int | None = Field(default=None, alias="expectedTaps")
    expected_cpa: Money | None = Field(default=None, alias="expectedCPA")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    applied_time: datetime | None = Field(default=None, alias="appliedTime")
    expiration_time: datetime | None = Field(default=None, alias="expirationTime")


class DailyCapRecommendation(V1Model):
    """A daily budget recommendation (read object).

    Surfaced for campaigns frequently hitting their spending ceiling;
    carries ``recommendationType: "DAILYCAP"``. All fields read-only.

    Attributes:
        id: Unique identifier for the recommendation.
        recommendation_type: Always ``DAILYCAP`` on this object.
        promoted_object_id: App adam ID or brand ID.
        promoted_object_type: ``APPSTORE_APP`` or ``BUSINESS_BRAND``.
        campaign_id: The campaign the recommendation is for.
        campaign_name: Campaign display name.
        state: Lifecycle state; only ``AVAILABLE`` can be acted on.
        status: System-level operational status.
        suggested_daily_budget_amount: The recommended new daily
            budget.
        daily_budget: The campaign's current daily budget.
        bid_strategy: The campaign's current bid strategy.
        installs: Historical install count.
        spend: Historical spend.
        average_cpa: Historical average cost per acquisition.
        average_cpt: Historical average cost per tap.
        impression: Historical impression count (singular field name).
        taps: Historical tap count.
        ttr: Historical tap-through rate.
        expected_impressions: Estimated 7-day impressions after
            applying.
        expected_installs: Estimated 7-day installs after applying.
        expected_spend: Estimated 7-day spend after applying.
        expected_taps: Estimated 7-day taps after applying.
        expected_cpa: Estimated 7-day average CPA after applying (wire
            alias ``expectedCpa`` — lowercase, unlike the Target CPA
            objects' ``expectedCPA``).
        creation_time: When the recommendation was created.
        modification_time: When the recommendation was last modified.
        expiration_time: When the recommendation expires.
    """

    id: str | None = None
    recommendation_type: RecommendationCategory | None = Field(
        default=None, alias="recommendationType"
    )
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    promoted_object_type: RecommendationPromotedObjectType | None = Field(
        default=None, alias="promotedObjectType"
    )
    campaign_id: int | None = Field(default=None, alias="campaignId")
    campaign_name: str | None = Field(default=None, alias="campaignName")
    state: RecommendationState | None = None
    status: RecommendationStatus | None = None
    suggested_daily_budget_amount: Money | None = Field(
        default=None, alias="suggestedDailyBudgetAmount"
    )
    daily_budget: Money | None = Field(default=None, alias="dailyBudget")
    bid_strategy: RecommendationBidStrategy | None = Field(default=None, alias="bidStrategy")
    installs: int | None = None
    spend: Money | None = None
    average_cpa: Money | None = Field(default=None, alias="averageCPA")
    average_cpt: Money | None = Field(default=None, alias="averageCPT")
    impression: int | None = None
    taps: int | None = None
    ttr: float | None = None
    expected_impressions: int | None = Field(default=None, alias="expectedImpressions")
    expected_installs: int | None = Field(default=None, alias="expectedInstalls")
    expected_spend: Money | None = Field(default=None, alias="expectedSpend")
    expected_taps: int | None = Field(default=None, alias="expectedTaps")
    expected_cpa: Money | None = Field(default=None, alias="expectedCpa")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    expiration_time: datetime | None = Field(default=None, alias="expirationTime")


class DailyCapRecommendationHistory(V1Model):
    """Immutable record of an applied or dismissed daily budget recommendation.

    Returned by the daily-budgets apply and dismiss endpoints. Note the
    ID field is ``recommendationId``, not ``id``. Unlike the Target CPA
    history, this object has Low/High confidence-interval bounds on all
    expected metrics. All fields read-only.

    Attributes:
        recommendation_id: ID of the original recommendation.
        recommendation_type: Always ``DAILYCAP``.
        promoted_object_id: App adam ID or brand ID.
        promoted_object_type: ``APPSTORE_APP`` or ``BUSINESS_BRAND``.
        campaign_id: Campaign ID.
        campaign_name: Campaign display name.
        state: Terminal state — ``APPLIED`` or ``DISMISSED``.
        status: System-level operational status.
        applied_daily_budget_amount: The daily budget actually applied;
            None on dismiss.
        suggested_daily_budget_amount: The originally suggested daily
            budget.
        rank: Rank at the time of the action.
        installs: Historical install count at the time of the action.
        spend: Historical spend at the time of the action.
        average_cpa: Historical average CPA at the time of the action.
        average_cpt: Historical average CPT at the time of the action.
        impression: Historical impression count.
        taps: Historical tap count.
        ttr: Historical tap-through rate.
        expected_impressions: Expected impressions from the original
            recommendation.
        expected_impressions_low: Lower bound of the confidence
            interval.
        expected_impressions_high: Upper bound of the confidence
            interval.
        expected_installs: Expected installs.
        expected_installs_low: Lower bound.
        expected_installs_high: Upper bound.
        expected_spend: Expected spend.
        expected_spend_low: Lower bound.
        expected_spend_high: Upper bound.
        expected_taps: Expected taps.
        expected_taps_low: Lower bound.
        expected_taps_high: Upper bound.
        expected_cpa: Expected CPA (wire alias ``expectedCpa``).
        expected_cpa_low: Lower bound.
        expected_cpa_high: Upper bound.
        creation_time: When the original recommendation was created.
        modification_time: When this history record was last modified.
        applied_time: When the apply/dismiss action was taken.
        expiration_time: When the original recommendation would have
            expired.
    """

    recommendation_id: str | None = Field(default=None, alias="recommendationId")
    recommendation_type: RecommendationCategory | None = Field(
        default=None, alias="recommendationType"
    )
    promoted_object_id: str | None = Field(default=None, alias="promotedObjectId")
    promoted_object_type: RecommendationPromotedObjectType | None = Field(
        default=None, alias="promotedObjectType"
    )
    campaign_id: int | None = Field(default=None, alias="campaignId")
    campaign_name: str | None = Field(default=None, alias="campaignName")
    state: RecommendationState | None = None
    status: RecommendationStatus | None = None
    applied_daily_budget_amount: Money | None = Field(
        default=None, alias="appliedDailyBudgetAmount"
    )
    suggested_daily_budget_amount: Money | None = Field(
        default=None, alias="suggestedDailyBudgetAmount"
    )
    rank: int | None = None
    installs: int | None = None
    spend: Money | None = None
    average_cpa: Money | None = Field(default=None, alias="averageCPA")
    average_cpt: Money | None = Field(default=None, alias="averageCPT")
    impression: int | None = None
    taps: int | None = None
    ttr: float | None = None
    expected_impressions: int | None = Field(default=None, alias="expectedImpressions")
    expected_impressions_low: int | None = Field(default=None, alias="expectedImpressionsLow")
    expected_impressions_high: int | None = Field(default=None, alias="expectedImpressionsHigh")
    expected_installs: int | None = Field(default=None, alias="expectedInstalls")
    expected_installs_low: int | None = Field(default=None, alias="expectedInstallsLow")
    expected_installs_high: int | None = Field(default=None, alias="expectedInstallsHigh")
    expected_spend: Money | None = Field(default=None, alias="expectedSpend")
    expected_spend_low: Money | None = Field(default=None, alias="expectedSpendLow")
    expected_spend_high: Money | None = Field(default=None, alias="expectedSpendHigh")
    expected_taps: int | None = Field(default=None, alias="expectedTaps")
    expected_taps_low: int | None = Field(default=None, alias="expectedTapsLow")
    expected_taps_high: int | None = Field(default=None, alias="expectedTapsHigh")
    expected_cpa: Money | None = Field(default=None, alias="expectedCpa")
    expected_cpa_low: Money | None = Field(default=None, alias="expectedCpaLow")
    expected_cpa_high: Money | None = Field(default=None, alias="expectedCpaHigh")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    modification_time: datetime | None = Field(default=None, alias="modificationTime")
    applied_time: datetime | None = Field(default=None, alias="appliedTime")
    expiration_time: datetime | None = Field(default=None, alias="expirationTime")


class ApplyTargetCpaRecommendation(V1Model):
    """Request item for applying or dismissing a Target CPA recommendation.

    Apply and dismiss bodies are bare JSON arrays of these objects.
    All items in one request must share the same ``promotedObjectId``.

    Attributes:
        id: The recommendation ID to act on. Required.
        promoted_object_id: App adam ID (``APPSTORE_APP``) or brand ID
            (``BUSINESS_BRAND``). Required; identical across all items
            in one request.
        promoted_object_type: ``APPSTORE_APP`` or ``BUSINESS_BRAND``.
            Required.
        applied_target_cpa: Target CPA to apply, overriding the
            recommendation's ``recommendedTargetCPA``. Ignored on
            dismiss.
        history_id: Optional reference to a prior history record.
    """

    id: str
    promoted_object_id: str = Field(alias="promotedObjectId")
    promoted_object_type: RecommendationPromotedObjectType = Field(alias="promotedObjectType")
    applied_target_cpa: Money | None = Field(default=None, alias="appliedTargetCPA")
    history_id: str | None = Field(default=None, alias="historyId")


class ApplyDailyCapRecommendation(V1Model):
    """Request item for applying or dismissing a daily budget recommendation.

    Apply and dismiss bodies are bare JSON arrays of these objects.
    All items in one request must share the same ``promotedObjectId``.

    Attributes:
        id: The recommendation ID to act on. Required.
        promoted_object_id: App adam ID (``APPSTORE_APP``) or brand ID
            (``BUSINESS_BRAND``). Required; identical across all items
            in one request.
        promoted_object_type: ``APPSTORE_APP`` or ``BUSINESS_BRAND``.
            Required.
        applied_daily_budget: Daily budget to apply, overriding the
            recommendation's ``suggestedDailyBudgetAmount``. Ignored on
            dismiss.
        history_id: Optional reference to a prior history record.
    """

    id: str
    promoted_object_id: str = Field(alias="promotedObjectId")
    promoted_object_type: RecommendationPromotedObjectType = Field(alias="promotedObjectType")
    applied_daily_budget: Money | None = Field(default=None, alias="appliedDailyBudget")
    history_id: str | None = Field(default=None, alias="historyId")
