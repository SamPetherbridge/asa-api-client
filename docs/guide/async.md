# Async Usage

`AppleAdsClient` provides both synchronous and asynchronous methods on the same client instance.

## Async Context Manager

```python
import asyncio

from asa_api_client import AppleAdsClient


async def main() -> None:
    async with AppleAdsClient.from_env() as client:
        page = await client.campaigns.query_async()
        print(f"Fetched {len(page)} campaigns")


asyncio.run(main())
```

## Sync vs Async Method Pairs

Every resource method has an `_async` twin:

```python
# Sync
campaign = client.campaigns.get(campaign_id)
page = client.campaigns.query()

# Async
campaign = await client.campaigns.get_async(campaign_id)
page = await client.campaigns.query_async()
```

## Async Pagination

```python
async with client:
    async for campaign in client.campaigns.iter_all_async():
        print(campaign.name)
```

## Concurrent Requests & Multi-Account Scoping

Use `asyncio.gather` to fetch multiple endpoints (or multiple ad accounts via `client.with_account(...)`) concurrently over a shared OAuth token cache and HTTP connection pool:

```python
from datetime import date

from asa_api_client.v1.models.reports import AppsReportingRequest, ReportTimeRange


async def snapshot(client: AppleAdsClient):
    request = AppsReportingRequest(
        time_range=ReportTimeRange(
            start=date(2026, 8, 1),
            end=date(2026, 8, 31),
        )
    )
    campaigns_page, report = await asyncio.gather(
        client.campaigns.query_async(),
        client.reports.campaigns_async(request),
    )
    return campaigns_page, report
```
