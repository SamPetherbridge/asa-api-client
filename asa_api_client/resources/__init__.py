"""Resource classes for the Apple Search Ads API.

Resources provide a structured interface for interacting with
different API endpoints. Each resource handles a specific entity
type (campaigns, ad groups, keywords, etc.).
"""

from asa_api_client.resources.acls import ACLResource
from asa_api_client.resources.ad_groups import AdGroupResource
from asa_api_client.resources.ads import AdResource
from asa_api_client.resources.apps import AppResource
from asa_api_client.resources.budget_orders import BudgetOrderResource
from asa_api_client.resources.campaigns import CampaignResource
from asa_api_client.resources.countries import CountryOrRegionResource
from asa_api_client.resources.custom_reports import CustomReportResource
from asa_api_client.resources.geo import GeoResource
from asa_api_client.resources.keywords import KeywordResource, NegativeKeywordResource
from asa_api_client.resources.product_pages import ProductPageResource
from asa_api_client.resources.reports import ReportResource

__all__ = [
    "ACLResource",
    "AdGroupResource",
    "AdResource",
    "AppResource",
    "BudgetOrderResource",
    "CampaignResource",
    "CountryOrRegionResource",
    "CustomReportResource",
    "GeoResource",
    "KeywordResource",
    "NegativeKeywordResource",
    "ProductPageResource",
    "ReportResource",
]
