# Authentication

The Apple Search Ads API uses OAuth 2.0 with JWT tokens signed using ES256 (ECDSA).

## Getting API Credentials

1. Go to [Apple Search Ads](https://searchads.apple.com)
2. Navigate to **Settings** > **API**
3. Create a new API key
4. Download your private key (`.pem` file)
5. Note your Client ID, Team ID, and Key ID

## Configuration

### Environment Variables

Set the following environment variables:

```bash
export ASA_CLIENT_ID="SEARCHADS.your-client-id"
export ASA_TEAM_ID="SEARCHADS.your-team-id"
export ASA_KEY_ID="your-key-id"
export ASA_ORG_ID="123456"
export ASA_PRIVATE_KEY_PATH="/path/to/private-key.pem"
```

### Using a .env File

Create a `.env` file in your project:

```bash
ASA_CLIENT_ID=SEARCHADS.your-client-id
ASA_TEAM_ID=SEARCHADS.your-team-id
ASA_KEY_ID=your-key-id
ASA_ORG_ID=123456
ASA_PRIVATE_KEY_PATH=private-key.pem
```

### Direct Configuration

You can also pass credentials directly:

```python
from asa_api_client import AppleSearchAdsClient

client = AppleSearchAdsClient(
    client_id="SEARCHADS.xxx",
    team_id="SEARCHADS.xxx",
    key_id="xxx",
    org_id=123456,
    private_key_path="private-key.pem",
)
```

Or with the private key content:

```python
client = AppleSearchAdsClient(
    client_id="SEARCHADS.xxx",
    team_id="SEARCHADS.xxx",
    key_id="xxx",
    org_id=123456,
    private_key="-----BEGIN EC PRIVATE KEY-----\n...",
)
```

## Token Management

The client automatically handles:

- JWT creation and signing
- Token refresh when expired
- Request authentication headers

You don't need to manage tokens manually.
