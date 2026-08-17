"""Tests for the v5 client deprecation warning."""

import warnings

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from asa_api_client import AppleAdsClient, AppleSearchAdsClient


@pytest.fixture(scope="module")
def pem() -> str:
    """Generate a throwaway EC P-256 private key in PEM format."""
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def test_v5_client_warns_deprecation(pem: str) -> None:
    """Test constructing the v5 client emits a DeprecationWarning."""
    with pytest.warns(DeprecationWarning, match="2027-01-26"):
        AppleSearchAdsClient(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            org_id=123,
            private_key=pem,
        )


def test_v1_client_does_not_warn(pem: str) -> None:
    """Test the v1 client constructs without any deprecation warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        AppleAdsClient(
            client_id="SEARCHADS.test",
            team_id="TEAM123",
            key_id="KEY123",
            private_key=pem,
        )
