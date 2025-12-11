"""Base models and common types for the Apple Search Ads API.

This module contains shared models used across the API, including
pagination, selectors for queries, and common data structures.
"""

from collections.abc import Iterator
from enum import StrEnum
from typing import Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class SortOrder(StrEnum):
    """Sort order for query results."""

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class ConditionOperator(StrEnum):
    """Operators for query conditions."""

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUALS = "LESS_THAN_OR_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUALS = "GREATER_THAN_OR_EQUALS"
    CONTAINS = "CONTAINS"
    CONTAINS_ANY = "CONTAINS_ANY"
    CONTAINS_ALL = "CONTAINS_ALL"
    STARTSWITH = "STARTSWITH"
    ENDSWITH = "ENDSWITH"
    IN = "IN"
    LIKE = "LIKE"
    IS = "IS"
    BETWEEN = "BETWEEN"


# Map Python operators to API operators for fluent interface
_OPERATOR_MAP: dict[str, ConditionOperator] = {
    "==": ConditionOperator.EQUALS,
    "!=": ConditionOperator.NOT_EQUALS,
    "<": ConditionOperator.LESS_THAN,
    "<=": ConditionOperator.LESS_THAN_OR_EQUALS,
    ">": ConditionOperator.GREATER_THAN,
    ">=": ConditionOperator.GREATER_THAN_OR_EQUALS,
    "contains": ConditionOperator.CONTAINS,
    "contains_any": ConditionOperator.CONTAINS_ANY,
    "contains_all": ConditionOperator.CONTAINS_ALL,
    "startswith": ConditionOperator.STARTSWITH,
    "endswith": ConditionOperator.ENDSWITH,
    "in": ConditionOperator.IN,
    "like": ConditionOperator.LIKE,
    "is": ConditionOperator.IS,
    "between": ConditionOperator.BETWEEN,
}


class Money(BaseModel):
    """Represents a monetary amount with currency.

    Attributes:
        amount: The monetary amount as a string to preserve precision.
        currency: The ISO 4217 currency code (e.g., "USD", "EUR").
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: str
    currency: str

    @classmethod
    def usd(cls, amount: float | int | str) -> Self:
        """Create a Money instance in USD.

        Args:
            amount: The amount in USD.

        Returns:
            A Money instance with USD currency.
        """
        return cls(amount=str(amount), currency="USD")


class Sorting(BaseModel):
    """Specifies sorting for query results.

    Attributes:
        field: The field to sort by.
        sort_order: The sort direction (ASCENDING or DESCENDING).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    field: str
    sort_order: SortOrder = Field(default=SortOrder.ASCENDING, alias="sortOrder")


class Condition(BaseModel):
    """A filter condition for queries.

    Conditions are used in Selectors to filter results based on
    field values.

    Attributes:
        field: The field to filter on.
        operator: The comparison operator.
        values: The values to compare against.

    Example:
        Filter for enabled campaigns::

            condition = Condition(
                field="status",
                operator=ConditionOperator.EQUALS,
                values=["ENABLED"]
            )
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    field: str
    operator: ConditionOperator
    values: list[str]


class Pagination(BaseModel):
    """Pagination parameters for list requests.

    Attributes:
        offset: The starting position (0-indexed).
        limit: The maximum number of results to return.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    offset: int = 0
    limit: int = 1000


class Selector(BaseModel):
    """A query selector for filtering and sorting results.

    Selectors provide a fluent interface for building complex queries
    with conditions, sorting, and pagination.

    Example:
        Build a selector with conditions::

            selector = (
                Selector()
                .where("status", "==", "ENABLED")
                .where("budgetAmount.amount", ">", "100")
                .order_by("modificationTime", descending=True)
                .limit(50)
            )

            campaigns = client.campaigns.find(selector)
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    conditions: list[Condition] = Field(default_factory=list)
    fields: list[str] | None = None
    order_by: list[Sorting] = Field(default_factory=list, alias="orderBy")
    pagination: Pagination = Field(default_factory=Pagination)

    def where(
        self,
        field: str,
        operator: str | ConditionOperator,
        values: str | list[str],
    ) -> Self:
        """Add a filter condition.

        Args:
            field: The field to filter on.
            operator: The comparison operator. Can be a Python operator
                string ("==", "!=", "<", etc.) or a ConditionOperator.
            values: The value(s) to compare against.

        Returns:
            Self for method chaining.

        Example:
            Filter enabled campaigns with budget > 100::

                selector = (
                    Selector()
                    .where("status", "==", "ENABLED")
                    .where("budgetAmount.amount", ">", "100")
                )
        """
        if isinstance(operator, str):
            op = _OPERATOR_MAP.get(operator)
            if op is None:
                # Try direct enum value
                try:
                    op = ConditionOperator(operator)
                except ValueError:
                    valid = ", ".join(list(_OPERATOR_MAP.keys()))
                    raise ValueError(
                        f"Unknown operator: {operator}. Valid operators: {valid}"
                    ) from None
        else:
            op = operator

        if isinstance(values, str):
            values = [values]

        self.conditions.append(Condition(field=field, operator=op, values=values))
        return self

    def select(self, *fields: str) -> Self:
        """Specify which fields to return.

        Args:
            *fields: The field names to include in the response.

        Returns:
            Self for method chaining.
        """
        self.fields = list(fields)
        return self

    def sort_by(self, field: str, *, descending: bool = False) -> Self:
        """Add a sort specification.

        Args:
            field: The field to sort by.
            descending: If True, sort in descending order.

        Returns:
            Self for method chaining.
        """
        order = SortOrder.DESCENDING if descending else SortOrder.ASCENDING
        self.order_by.append(Sorting(field=field, sort_order=order))
        return self

    def limit(self, count: int) -> Self:
        """Set the maximum number of results.

        Args:
            count: The maximum number of results to return.

        Returns:
            Self for method chaining.
        """
        self.pagination.limit = count
        return self

    def offset(self, start: int) -> Self:
        """Set the starting position for results.

        Args:
            start: The starting position (0-indexed).

        Returns:
            Self for method chaining.
        """
        self.pagination.offset = start
        return self


class PageDetail(BaseModel):
    """Pagination details in API responses.

    Attributes:
        total_results: Total number of results available.
        start_index: The starting index of the current page.
        items_per_page: Number of items in the current page.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    total_results: int = Field(alias="totalResults")
    start_index: int = Field(alias="startIndex")
    items_per_page: int = Field(alias="itemsPerPage")

    @property
    def has_more(self) -> bool:
        """Check if there are more results available.

        Returns:
            True if there are more results beyond the current page.
        """
        return self.start_index + self.items_per_page < self.total_results


T = TypeVar("T", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[T]):
    """A paginated API response containing multiple items.

    This is a generic model that wraps a list of items along with
    pagination metadata.

    Attributes:
        data: The list of items in this page.
        pagination: Pagination details including total count.
        error: Error information if the request partially failed.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    data: list[T] = Field(default_factory=list)
    pagination: PageDetail | None = None
    error: dict[str, Any] | None = None

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        """Iterate over the items in this page."""
        return iter(self.data)

    def __len__(self) -> int:
        """Return the number of items in this page."""
        return len(self.data)

    def __getitem__(self, index: int) -> T:
        """Get an item by index."""
        return self.data[index]

    @property
    def total_results(self) -> int:
        """Get the total number of results available.

        Returns:
            The total count, or the length of data if pagination is not available.
        """
        if self.pagination:
            return self.pagination.total_results
        return len(self.data)

    @property
    def has_more(self) -> bool:
        """Check if there are more results available.

        Returns:
            True if there are more pages to fetch.
        """
        if self.pagination:
            return self.pagination.has_more
        return False
