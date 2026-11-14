# Quick Start

## Basic Usage

```python
from asa_api_client import AppleAdsClient

# Load credentials from environment variables or .env
client = AppleAdsClient.from_env()

with client:
    for campaign in client.campaigns.iter_all():
        print(f"{campaign.id}: {campaign.name} ({campaign.display_status})")
```

## Filtering & Sorting with `Query`

Platform API v1 resources expose a `POST .../query` endpoint backed by the fluent `Query` builder:

```python
from asa_api_client.v1 import Query

with client:
    enabled = client.campaigns.query(
        Query()
        .where("status", "EQUALS", "ENABLED")
        .where("name", "CONTAINS_ANY", ["Brand", "Core"], ignore_case=True)
        .order_by("id", "DESC")
        .page(size=100, fetch_total_count=True)
    )
    for campaign in enabled:
        print(campaign.name)
```

## Flat Resource Layout

In Platform API v1, resources live directly on `client` and filter by parent IDs using `Query`:

```python
with client:
    ad_groups = client.ad_groups.query(Query().where("campaignId", "EQUALS", str(campaign_id)))
    keywords = client.keywords.query(Query().where("adGroupId", "EQUALS", str(ad_group_id)))
```

## Error Handling

```python
from asa_api_client import (
    AppleSearchAdsError,
    AuthenticationError,
    NotFoundError,
    PartialFailureError,
    RateLimitError,
)

with client:
    try:
        campaign = client.campaigns.get(123)
    except NotFoundError:
        print("Campaign not found")
    except PartialFailureError as exc:
        print(f"Partial failure: {exc.details}")
    except RateLimitError as exc:
        print(f"Rate limited, retry after {exc.retry_after}")
    except AuthenticationError:
        print("Invalid credentials")
    except AppleSearchAdsError as exc:
        print(f"API error: {exc}")
```
