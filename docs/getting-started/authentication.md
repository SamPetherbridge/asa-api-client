# Authentication

The Apple Ads API uses OAuth 2.0 client credentials signed with an ES256 (ECDSA P-256) private key. Both `AppleAdsClient` (Platform API v1) and legacy `AppleSearchAdsClient` (v5) share the exact same OAuth key pair.

## Getting API Credentials

1. Sign in to [Apple Ads](https://ads.apple.com)
2. Navigate to **Account Settings** > **API**
3. Upload your public key or generate an API key pair and download the `.pem` private key
4. Copy your **Client ID**, **Team ID**, and **Key ID**

## Configuration

### Environment Variables

```bash
export ASA_CLIENT_ID="SEARCHADS.your-client-id"
export ASA_TEAM_ID="your-team-id"
export ASA_KEY_ID="your-key-id"
export ASA_AD_ACCOUNT_ID="123456"
export ASA_PRIVATE_KEY_PATH="/path/to/private-key.pem"
```

### Using a `.env` File

Create a `.env` file in your working directory:

```bash
ASA_CLIENT_ID=SEARCHADS.your-client-id
ASA_TEAM_ID=your-team-id
ASA_KEY_ID=your-key-id
ASA_AD_ACCOUNT_ID=123456
ASA_PRIVATE_KEY_PATH=private-key.pem
```

Then construct the client with:

```python
from asa_api_client import AppleAdsClient

client = AppleAdsClient.from_env()
```

### Discovering Your Ad Account ID

`ASA_AD_ACCOUNT_ID` may be omitted at startup to discover accessible ad accounts via `/v1/acls`:

```python
from asa_api_client import AppleAdsClient

with AppleAdsClient.from_env() as client:
    for acl in client.acls.list():
        if acl.ad_account:
            print(acl.ad_account.id, acl.ad_account.name)

    client.ad_account_id = "123456"
```

Or run `asa v1-smoke` from the CLI (`pip install "asa-api-client[cli]"`), which lists accessible accounts and runs a read-only smoke test.

### Direct Configuration

Pass credentials directly in code using either a key file path or raw PEM string:

```python
from asa_api_client import AppleAdsClient

client = AppleAdsClient(
    client_id="SEARCHADS.xxx",
    team_id="TEAM123",
    key_id="KEY123",
    ad_account_id="123456",
    private_key_path="private-key.pem",
)
```

```python
client = AppleAdsClient(
    client_id="SEARCHADS.xxx",
    team_id="TEAM123",
    key_id="KEY123",
    ad_account_id="123456",
    private_key="-----BEGIN EC PRIVATE KEY-----\n...",
)
```

## Token Management

The client automatically handles ES256 JWT creation, OAuth access-token caching, proactive token refresh before expiry, and `X-AP-Context` header injection.
