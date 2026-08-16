"""Shared fixtures for v1 client tests."""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from asa_api_client.v1.client import AppleAdsClient


@pytest.fixture(scope="session")
def ec_private_key_pem() -> str:
    """Generate a throwaway EC P-256 private key in PEM format."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode()


@pytest.fixture
def v1_client(ec_private_key_pem: str) -> AppleAdsClient:
    """Build a real AppleAdsClient with dummy credentials."""
    return AppleAdsClient(
        client_id="SEARCHADS.test",
        team_id="TEAM123",
        key_id="KEY123",
        ad_account_id="12345",
        private_key=ec_private_key_pem,
    )
