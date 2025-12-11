"""Authentication handling for the Apple Search Ads API.

This module handles OAuth 2.0 authentication with the Apple Search Ads API,
including JWT token generation and access token management.

The authentication flow:
1. Generate a client secret (JWT) signed with your private key
2. Exchange the client secret for an access token
3. Use the access token for API requests
4. Automatically refresh when the token expires
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Self

import httpx
import jwt

from asa_api_client.exceptions import AuthenticationError, ConfigurationError, NetworkError
from asa_api_client.logging import get_logger

logger = get_logger(__name__)

# Apple's OAuth token endpoint
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"

# Apple Search Ads API audience
AUDIENCE = "https://appleid.apple.com"

# Scope for Search Ads API access
SCOPE = "searchadsorg"

# JWT algorithm
ALGORITHM = "ES256"

# Maximum lifetime for client secret (180 days per Apple's requirements)
MAX_CLIENT_SECRET_LIFETIME = timedelta(days=180)

# Default access token refresh buffer (refresh 5 minutes before expiry)
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class AccessToken:
    """Represents an OAuth access token.

    Attributes:
        token: The access token string.
        expires_at: When the token expires.
        token_type: The type of token (typically "Bearer").
    """

    token: str
    expires_at: datetime
    token_type: str = "Bearer"

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired or about to expire.

        Returns:
            True if the token is expired or will expire within
            the refresh buffer period.
        """
        return datetime.now(UTC) >= (self.expires_at - TOKEN_REFRESH_BUFFER)

    @property
    def authorization_header(self) -> str:
        """Get the Authorization header value.

        Returns:
            The full Authorization header value including token type.
        """
        return f"{self.token_type} {self.token}"


class Authenticator:
    """Handles authentication with the Apple Search Ads API.

    This class manages the OAuth 2.0 flow for the Apple Search Ads API,
    including JWT client secret generation and access token management.

    Attributes:
        client_id: Your Apple Search Ads API client ID.
        team_id: Your Apple Developer team ID.
        key_id: The key ID for your private key.
        org_id: Your Apple Search Ads organization ID.

    Example:
        Create an authenticator and get an access token::

            auth = Authenticator(
                client_id="SEARCHADS.abc123",
                team_id="TEAM123",
                key_id="KEY123",
                private_key_path=Path("private-key.pem"),
                org_id=123456,
            )

            token = auth.get_access_token()
            # Or async
            token = await auth.get_access_token_async()
    """

    def __init__(
        self,
        *,
        client_id: str,
        team_id: str,
        key_id: str,
        org_id: int,
        private_key: str | None = None,
        private_key_path: Path | str | None = None,
    ) -> None:
        """Initialize the authenticator.

        You must provide either `private_key` or `private_key_path`.

        Args:
            client_id: Your Apple Search Ads API client ID.
            team_id: Your Apple Developer team ID.
            key_id: The key ID for your private key.
            org_id: Your Apple Search Ads organization ID.
            private_key: The private key as a PEM-encoded string.
            private_key_path: Path to the private key PEM file.

        Raises:
            ConfigurationError: If neither or both private key options
                are provided, or if the key cannot be loaded.
        """
        self.client_id = client_id
        self.team_id = team_id
        self.key_id = key_id
        self.org_id = org_id

        self._private_key = self._load_private_key(private_key, private_key_path)
        self._access_token: AccessToken | None = None
        self._client_secret: str | None = None
        self._client_secret_expires_at: datetime | None = None

        logger.debug(
            "Authenticator initialized for client_id=%s, org_id=%d",
            self.client_id,
            self.org_id,
        )

    def _load_private_key(
        self,
        private_key: str | None,
        private_key_path: Path | str | None,
    ) -> str:
        """Load the private key from string or file.

        Args:
            private_key: The private key as a string.
            private_key_path: Path to the private key file.

        Returns:
            The private key as a PEM-encoded string.

        Raises:
            ConfigurationError: If the key cannot be loaded.
        """
        if private_key and private_key_path:
            raise ConfigurationError("Provide either 'private_key' or 'private_key_path', not both")

        if not private_key and not private_key_path:
            raise ConfigurationError("Must provide either 'private_key' or 'private_key_path'")

        if private_key:
            logger.debug("Using provided private key string")
            return private_key

        path = Path(private_key_path) if isinstance(private_key_path, str) else private_key_path
        assert path is not None  # For type checker

        try:
            key_content = path.read_text()
            logger.debug("Loaded private key from %s", path)
            return key_content
        except FileNotFoundError as e:
            raise ConfigurationError(f"Private key file not found: {path}") from e
        except PermissionError as e:
            raise ConfigurationError(f"Cannot read private key file: {path}") from e
        except OSError as e:
            raise ConfigurationError(f"Error reading private key file: {e}") from e

    def _generate_client_secret(self) -> str:
        """Generate a JWT client secret.

        The client secret is a JWT signed with your private key that
        Apple uses to verify your identity.

        Returns:
            The encoded JWT client secret.
        """
        now = datetime.now(UTC)
        expiration = now + MAX_CLIENT_SECRET_LIFETIME

        headers = {
            "alg": ALGORITHM,
            "kid": self.key_id,
        }

        payload = {
            "sub": self.client_id,
            "aud": AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp()),
            "iss": self.team_id,
        }

        try:
            client_secret = jwt.encode(
                payload,
                self._private_key,
                algorithm=ALGORITHM,
                headers=headers,
            )
        except jwt.exceptions.PyJWTError as e:
            raise AuthenticationError(f"Failed to generate client secret: {e}") from e

        self._client_secret = client_secret
        self._client_secret_expires_at = expiration

        logger.debug("Generated new client secret, expires at %s", expiration)
        return client_secret

    @property
    def client_secret(self) -> str:
        """Get or generate the client secret.

        Returns:
            The JWT client secret, generating a new one if needed.
        """
        now = datetime.now(UTC)

        if (
            self._client_secret is None
            or self._client_secret_expires_at is None
            or now >= self._client_secret_expires_at - timedelta(days=1)
        ):
            return self._generate_client_secret()

        return self._client_secret

    def _request_access_token(self, http_client: httpx.Client) -> AccessToken:
        """Request a new access token from Apple.

        Args:
            http_client: The HTTP client to use for the request.

        Returns:
            The new access token.

        Raises:
            AuthenticationError: If authentication fails.
            NetworkError: If there's a network problem.
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": SCOPE,
        }

        logger.debug("Requesting access token from %s", TOKEN_URL)

        try:
            response = http_client.post(
                TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to request access token: {e}") from e

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get(
                "error_description", error_data.get("error", "Unknown error")
            )
            raise AuthenticationError(
                f"Failed to obtain access token: {error_msg}",
                status_code=response.status_code,
                response_body=error_data,
            )

        token_data = response.json()
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        token = AccessToken(
            token=token_data["access_token"],
            expires_at=expires_at,
            token_type=token_data.get("token_type", "Bearer"),
        )

        logger.info("Obtained new access token, expires at %s", expires_at)
        return token

    async def _request_access_token_async(self, http_client: httpx.AsyncClient) -> AccessToken:
        """Request a new access token from Apple asynchronously.

        Args:
            http_client: The async HTTP client to use for the request.

        Returns:
            The new access token.

        Raises:
            AuthenticationError: If authentication fails.
            NetworkError: If there's a network problem.
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": SCOPE,
        }

        logger.debug("Requesting access token from %s (async)", TOKEN_URL)

        try:
            response = await http_client.post(
                TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to request access token: {e}") from e

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get(
                "error_description", error_data.get("error", "Unknown error")
            )
            raise AuthenticationError(
                f"Failed to obtain access token: {error_msg}",
                status_code=response.status_code,
                response_body=error_data,
            )

        token_data = response.json()
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        token = AccessToken(
            token=token_data["access_token"],
            expires_at=expires_at,
            token_type=token_data.get("token_type", "Bearer"),
        )

        logger.info("Obtained new access token (async), expires at %s", expires_at)
        return token

    def get_access_token(self, http_client: httpx.Client) -> AccessToken:
        """Get a valid access token, refreshing if necessary.

        Args:
            http_client: The HTTP client to use for token requests.

        Returns:
            A valid access token.
        """
        if self._access_token is None or self._access_token.is_expired:
            self._access_token = self._request_access_token(http_client)

        return self._access_token

    async def get_access_token_async(self, http_client: httpx.AsyncClient) -> AccessToken:
        """Get a valid access token asynchronously, refreshing if necessary.

        Args:
            http_client: The async HTTP client to use for token requests.

        Returns:
            A valid access token.
        """
        if self._access_token is None or self._access_token.is_expired:
            self._access_token = await self._request_access_token_async(http_client)

        return self._access_token

    def invalidate_token(self) -> None:
        """Invalidate the current access token.

        Call this if you receive an authentication error to force
        a new token to be obtained on the next request.
        """
        logger.debug("Invalidating current access token")
        self._access_token = None

    @classmethod
    def from_env(cls, env_file: str | Path | None = ".env") -> Self:
        """Create an Authenticator from environment variables and .env file.

        Loads configuration from environment variables and optionally from
        a `.env` file. Environment variables take precedence.

        Required settings (via env vars or .env file):
        - ASA_CLIENT_ID
        - ASA_TEAM_ID
        - ASA_KEY_ID
        - ASA_ORG_ID
        - ASA_PRIVATE_KEY or ASA_PRIVATE_KEY_PATH

        Args:
            env_file: Path to .env file to load. Set to None to skip
                loading from file and only use environment variables.
                Defaults to ".env".

        Returns:
            A configured Authenticator instance.

        Raises:
            ConfigurationError: If required settings are missing or invalid.

        Example:
            Load from environment and .env file::

                auth = Authenticator.from_env()

            Load from a specific env file::

                auth = Authenticator.from_env(".env.production")

            Only use environment variables (no file)::

                auth = Authenticator.from_env(env_file=None)
        """
        from pydantic import ValidationError

        from asa_api_client.settings import Settings

        try:
            if env_file is None:
                # Only load from environment variables
                settings = Settings(_env_file=None)
            else:
                settings = Settings(_env_file=env_file)
        except ValidationError as e:
            # Convert pydantic validation errors to ConfigurationError
            errors = e.errors()
            if errors:
                first_error = errors[0]
                field = first_error.get("loc", ["unknown"])[0]
                msg = first_error.get("msg", "validation error")
                raise ConfigurationError(
                    f"Configuration error for ASA_{str(field).upper()}: {msg}"
                ) from e
            raise ConfigurationError(f"Configuration error: {e}") from e

        return cls(
            client_id=settings.client_id,
            team_id=settings.team_id,
            key_id=settings.key_id,
            org_id=settings.org_id,
            private_key=settings.get_private_key(),
        )
