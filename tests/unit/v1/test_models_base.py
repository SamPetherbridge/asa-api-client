"""Tests for v1 base models: envelope, pagination, and Money."""

from asa_api_client.v1.models.base import (
    ErrorDetail,
    Money,
    V1Error,
    V1Page,
    V1Pagination,
)


class TestMoney:
    """Tests for the v1 Money model."""

    def test_usd_helper(self) -> None:
        """Test creating USD Money from a float."""
        money = Money.usd(9.99)
        assert money.amount == "9.99"
        assert money.currency == "USD"

    def test_of_helper(self) -> None:
        """Test creating Money in an arbitrary currency."""
        money = Money.of(15, "AUD")
        assert money.amount == "15"
        assert money.currency == "AUD"

    def test_parses_api_shape(self) -> None:
        """Test parsing the API's {amount, currency} shape."""
        money = Money.model_validate({"amount": "10.50", "currency": "EUR"})
        assert money.amount == "10.50"
        assert money.currency == "EUR"


class TestV1Pagination:
    """Tests for pagination metadata parsing."""

    def test_parses_camel_case_aliases(self) -> None:
        """Test that pageSize and totalCount aliases populate the model."""
        pagination = V1Pagination.model_validate({"offset": 0, "pageSize": 10, "totalCount": 12})
        assert pagination.offset == 0
        assert pagination.page_size == 10
        assert pagination.total_count == 12


class TestV1Page:
    """Tests for the paginated result container."""

    def test_parses_result_list(self) -> None:
        """Test parsing a result list into typed items."""
        page = V1Page[Money].model_validate(
            {
                "result": [{"amount": "1.00", "currency": "USD"}],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            }
        )
        assert len(page) == 1
        assert page[0].amount == "1.00"
        assert list(page) == [page[0]]

    def test_has_more_false_when_complete(self) -> None:
        """Test has_more is False when offset + items covers totalCount."""
        page = V1Page[Money].model_validate(
            {
                "result": [{"amount": "1.00", "currency": "USD"}],
                "pagination": {"offset": 0, "pageSize": 10, "totalCount": 1},
            }
        )
        assert page.has_more is False

    def test_has_more_true_when_partial(self) -> None:
        """Test has_more is True when more items remain server-side."""
        page = V1Page[Money].model_validate(
            {
                "result": [{"amount": "1.00", "currency": "USD"}],
                "pagination": {"offset": 0, "pageSize": 1, "totalCount": 3},
            }
        )
        assert page.has_more is True

    def test_has_more_false_without_pagination(self) -> None:
        """Test has_more is False when the server omits pagination."""
        page = V1Page[Money].model_validate({"result": [{"amount": "1.00", "currency": "USD"}]})
        assert page.has_more is False

    def test_has_more_true_on_full_page_without_total_count(self) -> None:
        """Test full page implies more when totalCount was not requested."""
        page = V1Page[Money].model_validate(
            {
                "result": [{"amount": "1.00", "currency": "USD"}],
                "pagination": {"offset": 0, "pageSize": 1},
            }
        )
        assert page.has_more is True

    def test_has_more_false_on_short_page_without_total_count(self) -> None:
        """Test short page implies exhaustion when totalCount is absent."""
        page = V1Page[Money].model_validate(
            {
                "result": [{"amount": "1.00", "currency": "USD"}],
                "pagination": {"offset": 0, "pageSize": 5},
            }
        )
        assert page.has_more is False

    def test_pagination_fields_all_optional(self) -> None:
        """Test pagination parses when the server echoes nothing back."""
        pagination = V1Pagination.model_validate({})
        assert pagination.offset is None
        assert pagination.page_size is None
        assert pagination.total_count is None


class TestV1Error:
    """Tests for the v1 error object."""

    def test_parses_error_with_details(self) -> None:
        """Test parsing the documented error shape."""
        error = V1Error.model_validate(
            {
                "code": "INVALID_REQUEST",
                "message": "The request is invalid",
                "details": [
                    {
                        "code": "UNRECOGNIZED_PROPERTY",
                        "message": "field is not recognized",
                        "info": {"field": "budget"},
                    }
                ],
            }
        )
        assert error.code == "INVALID_REQUEST"
        assert error.details is not None
        assert error.details[0].code == "UNRECOGNIZED_PROPERTY"
        assert error.details[0].info == {"field": "budget"}

    def test_parses_minimal_error(self) -> None:
        """Test parsing an error with only a message."""
        error = V1Error.model_validate({"message": "boom"})
        assert error.message == "boom"
        assert error.code is None
        assert error.details is None

    def test_error_detail_all_optional(self) -> None:
        """Test that every ErrorDetail field is optional."""
        detail = ErrorDetail.model_validate({})
        assert detail.code is None
        assert detail.message is None
        assert detail.info is None
