"""Apple Ads Platform API v1 client package.

Import the client and query builder from the package root::

    from asa_api_client import AppleAdsClient, Query
"""

from asa_api_client.v1.client import AppleAdsClient
from asa_api_client.v1.query import FilterOperator, Query, SortOrder

__all__ = ["AppleAdsClient", "FilterOperator", "Query", "SortOrder"]
