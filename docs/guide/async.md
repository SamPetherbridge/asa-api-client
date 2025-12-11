# Async Usage

The client supports both synchronous and asynchronous operations.

## Async Context Manager

```python
import asyncio
from asa_api_client import AppleSearchAdsClient

async def main():
    client = AppleSearchAdsClient.from_env()

    async with client:
        campaigns = await client.campaigns.list_async()
        print(f"Found {len(campaigns)} campaigns")

asyncio.run(main())
```

## Async Methods

All resource methods have async variants with `_async` suffix:

```python
# Sync
campaigns = client.campaigns.list()

# Async
campaigns = await client.campaigns.list_async()
```

```python
# Sync
campaign = client.campaigns.get(campaign_id)

# Async
campaign = await client.campaigns.get_async(campaign_id)
```

## Async Iteration

```python
async with client:
    async for campaign in client.campaigns.iter_all_async():
        print(campaign.name)
```

## Concurrent Requests

Use `asyncio.gather` for concurrent operations:

```python
async def get_campaigns_and_reports():
    client = AppleSearchAdsClient.from_env()

    async with client:
        campaigns, report = await asyncio.gather(
            client.campaigns.list_async(),
            client.reports.campaigns_async(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            ),
        )

        return campaigns, report
```

## Mixed Sync/Async

You can use sync methods from async code, but it's not recommended as it blocks the event loop:

```python
async with client:
    # This blocks - avoid in async code
    campaigns = client.campaigns.list()

    # Prefer async methods
    campaigns = await client.campaigns.list_async()
```
