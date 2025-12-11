"""Resource classes for the Apple Search Ads API.

Resources provide a structured interface for interacting with
different API endpoints. Each resource handles a specific entity
type (campaigns, ad groups, keywords, etc.).
"""

from asa_api_client.resources.ad_groups import AdGroupResource
from asa_api_client.resources.campaigns import CampaignResource
from asa_api_client.resources.keywords import KeywordResource, NegativeKeywordResource
from asa_api_client.resources.reports import ReportResource

__all__ = [
    "AdGroupResource",
    "CampaignResource",
    "KeywordResource",
    "NegativeKeywordResource",
    "ReportResource",
]
