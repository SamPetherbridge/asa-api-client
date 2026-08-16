"""Tests for the v1 Query builder."""

import pytest

from asa_api_client.v1.query import FilterOperator, Query, SortOrder


class TestQueryPayload:
    """Tests for Query.to_payload() serialization."""

    def test_empty_query_serializes_to_empty_dict(self) -> None:
        """Test that an empty query produces an empty payload."""
        assert Query().to_payload() == {}

    def test_where_serializes_filter(self) -> None:
        """Test the documented keywords/query example body."""
        payload = Query().where("adGroupId", "EQUALS", 542317095).to_payload()
        assert payload == {
            "filters": [{"field": "adGroupId", "operator": "EQUALS", "value": 542317095}]
        }

    def test_chained_filters_sorting_pagination(self) -> None:
        """Test a fully-populated query matching the docs example."""
        payload = (
            Query()
            .where("name", "CONTAINS_ANY", ["AwayFinder", "AwayFinder Promo"], ignore_case=True)
            .order_by("id", "DESC")
            .page(size=25, offset=0, fetch_total_count=True)
            .to_payload()
        )
        assert payload == {
            "filters": [
                {
                    "field": "name",
                    "operator": "CONTAINS_ANY",
                    "value": ["AwayFinder", "AwayFinder Promo"],
                    "ignoreCase": True,
                }
            ],
            "sorting": [{"field": "id", "order": "DESC"}],
            "pagination": {"pageSize": 25, "offset": 0, "fetchTotalCount": True},
        }

    def test_null_operator_omits_value(self) -> None:
        """Test IS_NULL filters serialize without a value key."""
        payload = Query().where("deletionDate", FilterOperator.IS_NULL).to_payload()
        assert payload == {"filters": [{"field": "deletionDate", "operator": "IS_NULL"}]}

    def test_enum_operators_accepted(self) -> None:
        """Test enum members serialize to their string values."""
        payload = Query().where("status", FilterOperator.EQUALS, "ENABLED").to_payload()
        assert payload["filters"][0]["operator"] == "EQUALS"

    def test_invalid_operator_string_raises(self) -> None:
        """Test unknown operator strings are rejected eagerly."""
        with pytest.raises(ValueError, match="NOT_AN_OPERATOR"):
            Query().where("status", "NOT_AN_OPERATOR", "ENABLED")

    def test_invalid_sort_order_raises(self) -> None:
        """Test unknown sort orders are rejected eagerly."""
        with pytest.raises(ValueError, match="SIDEWAYS"):
            Query().order_by("id", "SIDEWAYS")

    def test_default_sort_order_is_asc(self) -> None:
        """Test order_by defaults to ascending."""
        payload = Query().order_by("name").to_payload()
        assert payload == {"sorting": [{"field": "name", "order": "ASC"}]}

    def test_page_partial_fields(self) -> None:
        """Test pagination only includes the fields that were set."""
        payload = Query().page(size=100).to_payload()
        assert payload == {"pagination": {"pageSize": 100}}

    def test_fluent_methods_return_same_query(self) -> None:
        """Test chaining mutates and returns the same instance."""
        query = Query()
        assert query.where("id", "EQUALS", 1) is query
        assert query.order_by("id") is query
        assert query.page(size=1) is query


class TestEnums:
    """Tests for query enum completeness."""

    def test_operator_values_match_docs(self) -> None:
        """Test the operator enum carries the full documented value list."""
        documented = {
            "BETWEEN",
            "CONTAINS_ANY",
            "CONTAINS_ALL",
            "ENDS_WITH",
            "EQUALS",
            "GREATER_THAN",
            "GREATER_THAN_OR_EQUAL_TO",
            "IN",
            "INCLUDE",
            "IS_NULL",
            "IS_NOT_NULL",
            "LESS_THAN",
            "LESS_THAN_OR_EQUAL_TO",
            "LIKE",
            "NOT_CONTAINS_ALL",
            "NOT_CONTAINS_ANY",
            "NOT_EQUALS",
            "NOT_IN",
            "NOT_LIKE",
            "STARTS_WITH",
        }
        assert {op.value for op in FilterOperator} == documented

    def test_sort_orders(self) -> None:
        """Test sort order enum values."""
        assert {order.value for order in SortOrder} == {"ASC", "DESC"}
