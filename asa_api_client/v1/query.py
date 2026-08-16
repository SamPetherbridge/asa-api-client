"""Query builder for Apple Ads Platform API v1 query endpoints.

All v1 querying happens via ``POST <resource>/query`` with a body of
``{"filters": [...], "sorting": [...], "pagination": {...}}``. This
module provides a fluent builder for that body.

Example:
    Find enabled campaigns, newest first::

        from asa_api_client.v1.query import Query

        query = (
            Query()
            .where("status", "EQUALS", "ENABLED")
            .order_by("id", "DESC")
            .page(size=100)
        )
        campaigns = client.campaigns.query(query)
"""

from enum import StrEnum
from typing import Any, Self

# Operators whose filters carry no value.
_VALUELESS_OPERATORS = frozenset({"IS_NULL", "IS_NOT_NULL"})


class FilterOperator(StrEnum):
    """Comparison operators for query filters.

    Not every endpoint supports every operator; per-field support is
    listed in each entity's documentation.
    """

    BETWEEN = "BETWEEN"
    CONTAINS_ANY = "CONTAINS_ANY"
    CONTAINS_ALL = "CONTAINS_ALL"
    ENDS_WITH = "ENDS_WITH"
    EQUALS = "EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL_TO = "GREATER_THAN_OR_EQUAL_TO"
    IN = "IN"
    INCLUDE = "INCLUDE"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL_TO = "LESS_THAN_OR_EQUAL_TO"
    LIKE = "LIKE"
    NOT_CONTAINS_ALL = "NOT_CONTAINS_ALL"
    NOT_CONTAINS_ANY = "NOT_CONTAINS_ANY"
    NOT_EQUALS = "NOT_EQUALS"
    NOT_IN = "NOT_IN"
    NOT_LIKE = "NOT_LIKE"
    STARTS_WITH = "STARTS_WITH"


class SortOrder(StrEnum):
    """Sort direction for query sorting entries."""

    ASC = "ASC"
    DESC = "DESC"


class Query:
    """Fluent builder for v1 query request bodies.

    Multiple ``where()`` filters combine with logical AND. Multiple
    ``order_by()`` entries apply in order (primary sort first). An
    empty query returns all non-deleted records in the account scope.
    """

    def __init__(self) -> None:
        """Initialize an empty query."""
        self._filters: list[dict[str, Any]] = []
        self._sorting: list[dict[str, str]] = []
        self._pagination: dict[str, Any] = {}

    def where(
        self,
        field: str,
        operator: FilterOperator | str,
        value: Any = None,
        *,
        ignore_case: bool | None = None,
    ) -> Self:
        """Add a filter condition (AND semantics).

        Args:
            field: Field name to filter on (e.g. ``"adGroupId"``).
            operator: Comparison operator, as a
                :class:`FilterOperator` or its string value.
            value: Comparison value. Use a list for multi-value
                operators (``IN``, ``CONTAINS_ANY``, ...), a two-item
                ``[minimum, maximum]`` list for ``BETWEEN``, and omit
                for ``IS_NULL`` / ``IS_NOT_NULL``.
            ignore_case: When True, string comparison is
                case-insensitive.

        Returns:
            This query, for chaining.

        Raises:
            ValueError: If ``operator`` is not a documented operator.
        """
        op = FilterOperator(operator)
        condition: dict[str, Any] = {"field": field, "operator": op.value}
        if op.value not in _VALUELESS_OPERATORS:
            condition["value"] = value
        if ignore_case is not None:
            condition["ignoreCase"] = ignore_case
        self._filters.append(condition)
        return self

    def order_by(self, field: str, order: SortOrder | str = SortOrder.ASC) -> Self:
        """Add a sorting entry.

        Args:
            field: Field name to sort by.
            order: Sort direction, ``"ASC"`` (default) or ``"DESC"``.

        Returns:
            This query, for chaining.

        Raises:
            ValueError: If ``order`` is not ``ASC`` or ``DESC``.
        """
        self._sorting.append({"field": field, "order": SortOrder(order).value})
        return self

    def page(
        self,
        *,
        size: int | None = None,
        offset: int | None = None,
        fetch_total_count: bool | None = None,
    ) -> Self:
        """Set pagination controls.

        Args:
            size: Items per page (``pageSize``).
            offset: Zero-based starting position.
            fetch_total_count: When True, the response's pagination
                includes ``totalCount``.

        Returns:
            This query, for chaining.
        """
        if size is not None:
            self._pagination["pageSize"] = size
        if offset is not None:
            self._pagination["offset"] = offset
        if fetch_total_count is not None:
            self._pagination["fetchTotalCount"] = fetch_total_count
        return self

    def to_payload(self) -> dict[str, Any]:
        """Serialize to the v1 query request body.

        Returns:
            The ``{filters, sorting, pagination}`` dict, omitting
            sections that were never populated.
        """
        payload: dict[str, Any] = {}
        if self._filters:
            payload["filters"] = self._filters
        if self._sorting:
            payload["sorting"] = self._sorting
        if self._pagination:
            payload["pagination"] = self._pagination
        return payload

    def __repr__(self) -> str:
        """Return a string representation of the query."""
        return (
            f"Query(filters={len(self._filters)}, sorting={len(self._sorting)}, "
            f"pagination={self._pagination or None})"
        )
