"""Apple Ads Platform API v1 client package.

This subpackage contains the client for the Apple Ads Platform API v1
(``https://api.ads.apple.com/v1``), which replaces the Campaign
Management API v5. It is self-contained: it shares only authentication,
exceptions, and logging with the v5 client.

Import the client from the package root::

    from asa_api_client import AppleAdsClient
"""

from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.query import FilterOperator, Query, SortOrder

__all__ = ["AppleAdsClient", "FilterOperator", "Query", "SortOrder"]
