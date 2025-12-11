"""Tests for the Pydantic models."""

from asa_api_client.models import (
    CampaignCreate,
    CampaignStatus,
    CampaignSupplySource,
    Money,
    Selector,
)


class TestMoney:
    """Tests for the Money model."""

    def test_create_money(self) -> None:
        """Test creating a Money instance."""
        money = Money(amount="100.50", currency="USD")
        assert money.amount == "100.50"
        assert money.currency == "USD"

    def test_money_usd_helper(self) -> None:
        """Test the USD helper method."""
        money = Money.usd(100)
        assert money.amount == "100"
        assert money.currency == "USD"

    def test_money_usd_with_decimals(self) -> None:
        """Test USD helper with decimal amount."""
        money = Money.usd(100.50)
        assert money.amount == "100.5"
        assert money.currency == "USD"


class TestSelector:
    """Tests for the Selector model."""

    def test_empty_selector(self) -> None:
        """Test creating an empty selector with defaults."""
        selector = Selector()
        data = selector.model_dump(by_alias=True, exclude_none=True)
        assert data["conditions"] == []
        assert data["orderBy"] == []
        assert data["pagination"]["limit"] == 1000
        assert data["pagination"]["offset"] == 0

    def test_selector_with_condition(self) -> None:
        """Test creating a selector with a condition."""
        selector = Selector().where("status", "==", "ENABLED")
        data = selector.model_dump(by_alias=True, exclude_none=True)
        assert "conditions" in data
        assert len(data["conditions"]) == 1
        assert data["conditions"][0]["field"] == "status"
        assert data["conditions"][0]["operator"] == "EQUALS"
        assert data["conditions"][0]["values"] == ["ENABLED"]

    def test_selector_with_pagination(self) -> None:
        """Test creating a selector with pagination."""
        selector = Selector().limit(50).offset(100)
        data = selector.model_dump(by_alias=True, exclude_none=True)
        assert "pagination" in data
        assert data["pagination"]["limit"] == 50
        assert data["pagination"]["offset"] == 100


class TestCampaignCreate:
    """Tests for campaign creation models."""

    def test_create_campaign_model(self) -> None:
        """Test creating a CampaignCreate instance."""
        campaign = CampaignCreate(
            name="Test Campaign",
            adam_id=123456789,
            countries_or_regions=["US"],
            supply_sources=[CampaignSupplySource.APPSTORE_SEARCH_RESULTS],
            daily_budget_amount=Money.usd(100),
        )
        assert campaign.name == "Test Campaign"
        assert campaign.adam_id == 123456789
        assert campaign.countries_or_regions == ["US"]
        assert campaign.status == CampaignStatus.ENABLED

    def test_campaign_serialization(self) -> None:
        """Test that campaign serializes with correct aliases."""
        campaign = CampaignCreate(
            name="Test Campaign",
            adam_id=123456789,
            countries_or_regions=["US"],
            supply_sources=[CampaignSupplySource.APPSTORE_SEARCH_RESULTS],
        )
        data = campaign.model_dump(by_alias=True, exclude_none=True)
        assert "adamId" in data
        assert "countriesOrRegions" in data
        assert "supplySources" in data
