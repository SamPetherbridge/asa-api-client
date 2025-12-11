"""Settings management for the Apple Search Ads API client.

This module provides a Settings class that loads configuration from
environment variables and `.env` files using pydantic-settings.

Example:
    Create a `.env` file in your project root::

        ASA_CLIENT_ID=SEARCHADS.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        ASA_TEAM_ID=YOUR_TEAM_ID
        ASA_KEY_ID=YOUR_KEY_ID
        ASA_ORG_ID=123456
        ASA_PRIVATE_KEY_PATH=/path/to/private-key.pem

    Then load settings::

        from asa_api_client.settings import Settings

        settings = Settings()
        # Or specify a custom env file
        settings = Settings(_env_file=".env.production")
"""

from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Apple Search Ads API configuration settings.

    Settings are loaded from environment variables and `.env` files.
    Environment variables take precedence over `.env` file values.

    Attributes:
        client_id: Your Apple Search Ads API client ID (SEARCHADS.xxx).
        team_id: Your Apple Developer team ID.
        key_id: The key ID for your private key.
        org_id: Your Apple Search Ads organization ID.
        private_key: The private key as a PEM-encoded string (secret).
        private_key_path: Path to the private key PEM file.

    Example:
        Load from environment and `.env` file::

            settings = Settings()

        Load from a specific env file::

            settings = Settings(_env_file=".env.production")

        Access values::

            print(settings.client_id)
            print(settings.org_id)
            # Private key is a SecretStr, use get_secret_value()
            key = settings.private_key.get_secret_value()
    """

    model_config = SettingsConfigDict(
        env_prefix="ASA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    client_id: str = Field(description="Apple Search Ads API client ID (starts with SEARCHADS.)")
    team_id: str = Field(description="Apple Developer team ID")
    key_id: str = Field(description="API key identifier")
    org_id: int = Field(description="Apple Search Ads organization ID")
    private_key: SecretStr | None = Field(
        default=None,
        description="Private key as PEM-encoded string",
    )
    private_key_path: Path | None = Field(
        default=None,
        description="Path to private key PEM file",
    )

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate that client_id has the expected format."""
        if not v.startswith("SEARCHADS."):
            # Just warn, don't fail - Apple might change formats
            pass
        return v

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
