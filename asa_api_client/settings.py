"""Settings management for the Apple Ads API client.

This module provides a ``Settings`` class that loads configuration from
environment variables and ``.env`` files using ``pydantic-settings``.

Example:
    Create a ``.env`` file in your project root::

        ASA_CLIENT_ID=SEARCHADS.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        ASA_TEAM_ID=YOUR_TEAM_ID
        ASA_KEY_ID=YOUR_KEY_ID
        ASA_AD_ACCOUNT_ID=123456
        ASA_PRIVATE_KEY_PATH=/path/to/private-key.pem

    Then load settings::

        from asa_api_client import AppleAdsClient, Settings

        settings = Settings()
        client = AppleAdsClient.from_settings(settings)
"""

from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Apple Ads Platform API v1 configuration settings.

    Settings are loaded from environment variables and ``.env`` files.
    Environment variables take precedence over ``.env`` file values.

    Attributes:
        client_id: Your Apple Ads API client ID (``SEARCHADS.xxx``).
        team_id: Your Apple Developer team ID.
        key_id: The key ID for your private key.
        ad_account_id: Optional Apple Ads ad account ID for request scoping
            (may be omitted at bootstrap and resolved via ``/v1/acls``).
        org_id: Optional organization ID (used as a preference hint during
            account discovery when ``ad_account_id`` is unset).
        private_key: The private key as a PEM-encoded string (secret).
        private_key_path: Path to the private key PEM file.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    client_id: str = Field(description="Apple Ads API client ID (starts with SEARCHADS.)")
    team_id: str = Field(description="Apple Developer team ID")
    key_id: str = Field(description="API key identifier")
    ad_account_id: str | None = Field(
        default=None,
        description="Apple Ads ad account ID for X-AP-Context scoping",
    )
    org_id: int | None = Field(
        default=None,
        description="Optional organization ID (fallback preference for account discovery)",
    )
    private_key: SecretStr | None = Field(
        default=None,
        description="Private key as PEM-encoded string",
    )
    private_key_path: Path | None = Field(
        default=None,
        description="Path to private key PEM file",
    )

    @field_validator("ad_account_id", mode="before")
    @classmethod
    def normalize_ad_account_id(cls, v: object) -> str | None:
        """Normalize numeric or whitespace-padded account IDs to clean strings."""
        if v is None:
            return None
        text = str(v).strip()
        return text or None

    @model_validator(mode="after")
    def validate_private_key_source(self) -> Self:
        """Ensure exactly one private key source is provided."""
        has_key = self.private_key is not None
        has_path = self.private_key_path is not None

        if has_key and has_path:
            raise ValueError("Provide either 'private_key' or 'private_key_path', not both")

        if not has_key and not has_path:
            raise ValueError("Must provide either 'private_key' or 'private_key_path'")

        return self

    def get_private_key(self) -> str:
        """Get the private key content.

        Returns:
            The private key as a PEM-encoded string.

        Raises:
            ValueError: If the private key cannot be loaded.
        """
        if self.private_key is not None:
            return self.private_key.get_secret_value()

        if self.private_key_path is not None:
            try:
                return self.private_key_path.read_text()
            except FileNotFoundError as e:
                raise ValueError(f"Private key file not found: {self.private_key_path}") from e
            except PermissionError as e:
                raise ValueError(f"Cannot read private key file: {self.private_key_path}") from e

        raise ValueError("No private key configured")
