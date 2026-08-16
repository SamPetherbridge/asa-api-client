"""Tests for v1-specific exceptions."""

from asa_api_client.exceptions import AppleSearchAdsError, PartialFailureError


def test_partial_failure_error_carries_details() -> None:
    """Test that details and status_code are exposed as attributes."""
    details = [{"code": "NOT_SAME_CURRENCY_AS_ORG_CURRENCY", "message": "bad", "info": {}}]
    err = PartialFailureError("partial failure", status_code=200, details=details)
    assert isinstance(err, AppleSearchAdsError)
    assert err.details == details
    assert err.status_code == 200


def test_partial_failure_error_defaults_empty_details() -> None:
    """Test that details defaults to an empty list."""
    err = PartialFailureError("partial failure")
    assert err.details == []
