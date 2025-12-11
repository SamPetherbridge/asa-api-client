# Quick Start

## Basic Usage

```python
from asa_api_client import AppleSearchAdsClient

# Create client from environment variables
client = AppleSearchAdsClient.from_env()

# Use as context manager (recommended)
with client:
    # List campaigns
    campaigns = client.campaigns.list()

    for campaign in campaigns:
        print(f"{campaign.id}: {campaign.name} ({campaign.status})")
```

## Filtering Results

Use the `Selector` class to filter results:

```python
from asa_api_client.models import Selector

with client:
    # Find enabled campaigns
    selector = Selector().where("status", "==", "ENABLED")
    enabled = client.campaigns.find(selector)

    # Multiple conditions
    selector = (
        Selector()
        .where("status", "==", "ENABLED")
        .where("countriesOrRegions", "CONTAINS_ANY", ["US", "GB"])
    )
    campaigns = client.campaigns.find(selector)
```

## Pagination

For large result sets, use iteration:

```python
with client:
    # Automatic pagination
    for campaign in client.campaigns.iter_all():
        print(campaign.name)
```

## Resource Hierarchy

Access nested resources through their parents:

```python
with client:
    # Get ad groups for a campaign
    ad_groups = client.campaigns(campaign_id).ad_groups.list()

    # Get keywords for an ad group
    keywords = client.campaigns(campaign_id).ad_groups(ad_group_id).keywords.list()
```

## Error Handling

```python
from asa_api_client import (
    AppleSearchAdsError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

with client:
    try:
        campaign = client.campaigns.get(123)
    except NotFoundError:
        print("Campaign not found")
    except RateLimitError as e:
        print(f"Rate limited, retry after {e.retry_after}")
    except AuthenticationError:
        print("Invalid credentials")
    except AppleSearchAdsError as e:
        print(f"API error: {e}")
```
