"""Tests for PricingInfo model formatters and calculations"""

import pytest
from src.models.instance_type import PricingInfo


class TestPricingInfoFormatters:
    """Test PricingInfo formatting methods"""

    def test_format_on_demand_price(self):
        """Test on-demand price formatting"""
        pricing = PricingInfo(on_demand_price=0.0960)
        assert pricing.format_on_demand() == "$0.0960/hr"

    def test_format_on_demand_price_none(self):
        """Test on-demand price formatting when None"""
        pricing = PricingInfo(on_demand_price=None)
        assert pricing.format_on_demand() == "N/A"

    def test_format_spot_price(self):
        """Test spot price formatting"""
        pricing = PricingInfo(spot_price=0.0288)
        assert pricing.format_spot() == "$0.0288/hr"

    def test_format_spot_price_none(self):
        """Test spot price formatting when None"""
        pricing = PricingInfo(spot_price=None)
        assert pricing.format_spot() == "N/A"

    def test_format_savings_plan_1yr(self):
        """Test 1-year savings plan price formatting"""
        pricing = PricingInfo(savings_plan_1yr_no_upfront=0.0600)
        assert pricing.format_savings_plan_1yr() == "$0.0600/hr"

    def test_format_savings_plan_1yr_none(self):
        """Test 1-year savings plan formatting when None"""
        pricing = PricingInfo(savings_plan_1yr_no_upfront=None)
        assert pricing.format_savings_plan_1yr() == "N/A"

    def test_format_savings_plan_3yr(self):
        """Test 3-year savings plan price formatting"""
        pricing = PricingInfo(savings_plan_3yr_no_upfront=0.0410)
        assert pricing.format_savings_plan_3yr() == "$0.0410/hr"

    def test_format_savings_plan_3yr_none(self):
        """Test 3-year savings plan formatting when None"""
        pricing = PricingInfo(savings_plan_3yr_no_upfront=None)
        assert pricing.format_savings_plan_3yr() == "N/A"


class TestRIPricingFormatters:
    """Test Reserved Instance pricing formatters"""

    def test_format_ri_1yr_no_upfront(self):
        """Test 1yr No Upfront RI price formatting"""
        pricing = PricingInfo(ri_1yr_no_upfront=0.0600)
        assert pricing.format_ri_1yr_no_upfront() == "$0.0600/hr"

    def test_format_ri_1yr_no_upfront_none(self):
        """Test 1yr No Upfront RI formatting when None"""
        pricing = PricingInfo(ri_1yr_no_upfront=None)
        assert pricing.format_ri_1yr_no_upfront() == "N/A"

    def test_format_ri_1yr_partial_upfront(self):
        """Test 1yr Partial Upfront RI price formatting"""
        pricing = PricingInfo(ri_1yr_partial_upfront=0.0290)
        assert pricing.format_ri_1yr_partial_upfront() == "$0.0290/hr"

    def test_format_ri_1yr_partial_upfront_none(self):
        """Test 1yr Partial Upfront RI formatting when None"""
        pricing = PricingInfo(ri_1yr_partial_upfront=None)
        assert pricing.format_ri_1yr_partial_upfront() == "N/A"

    def test_format_ri_1yr_all_upfront(self):
        """Test 1yr All Upfront RI price formatting"""
        pricing = PricingInfo(ri_1yr_all_upfront=0.0280)
        assert pricing.format_ri_1yr_all_upfront() == "$0.0280/hr"

    def test_format_ri_1yr_all_upfront_none(self):
        """Test 1yr All Upfront RI formatting when None"""
        pricing = PricingInfo(ri_1yr_all_upfront=None)
        assert pricing.format_ri_1yr_all_upfront() == "N/A"

    def test_format_ri_3yr_no_upfront(self):
        """Test 3yr No Upfront RI price formatting"""
        pricing = PricingInfo(ri_3yr_no_upfront=0.0410)
        assert pricing.format_ri_3yr_no_upfront() == "$0.0410/hr"

    def test_format_ri_3yr_no_upfront_none(self):
        """Test 3yr No Upfront RI formatting when None"""
        pricing = PricingInfo(ri_3yr_no_upfront=None)
        assert pricing.format_ri_3yr_no_upfront() == "N/A"

    def test_format_ri_3yr_partial_upfront(self):
        """Test 3yr Partial Upfront RI price formatting"""
        pricing = PricingInfo(ri_3yr_partial_upfront=0.0190)
        assert pricing.format_ri_3yr_partial_upfront() == "$0.0190/hr"

    def test_format_ri_3yr_partial_upfront_none(self):
        """Test 3yr Partial Upfront RI formatting when None"""
        pricing = PricingInfo(ri_3yr_partial_upfront=None)
        assert pricing.format_ri_3yr_partial_upfront() == "N/A"

    def test_format_ri_3yr_all_upfront(self):
        """Test 3yr All Upfront RI price formatting"""
        pricing = PricingInfo(ri_3yr_all_upfront=0.0180)
        assert pricing.format_ri_3yr_all_upfront() == "$0.0180/hr"

    def test_format_ri_3yr_all_upfront_none(self):
        """Test 3yr All Upfront RI formatting when None"""
        pricing = PricingInfo(ri_3yr_all_upfront=None)
        assert pricing.format_ri_3yr_all_upfront() == "N/A"


class TestSavingsCalculations:
    """Test savings percentage calculations"""

    def test_calculate_savings_spot_price(self):
        """Test spot price savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, spot_price=0.0288)
        savings = pricing.calculate_savings_percentage("spot")
        assert savings == 70.0

    def test_calculate_savings_spot_price_none(self):
        """Test spot price savings when spot price is None"""
        pricing = PricingInfo(on_demand_price=0.0960, spot_price=None)
        savings = pricing.calculate_savings_percentage("spot")
        assert savings is None

    def test_calculate_savings_1yr_no_upfront(self):
        """Test 1yr No Upfront RI savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, ri_1yr_no_upfront=0.0600)
        savings = pricing.calculate_savings_percentage("ri_1yr_no_upfront")
        assert abs(savings - 37.5) < 0.01

    def test_calculate_savings_1yr_partial_upfront(self):
        """Test 1yr Partial Upfront RI savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, ri_1yr_partial_upfront=0.0290)
        savings = pricing.calculate_savings_percentage("ri_1yr_partial_upfront")
        # 0.0290 is about 69.8% savings from 0.0960
        assert abs(savings - 69.79) < 0.01

    def test_calculate_savings_1yr_all_upfront(self):
        """Test 1yr All Upfront RI savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, ri_1yr_all_upfront=0.0280)
        savings = pricing.calculate_savings_percentage("ri_1yr_all_upfront")
        # 0.0280 is about 70.8% savings from 0.0960
        assert abs(savings - 70.83) < 0.01

    def test_calculate_savings_3yr_no_upfront(self):
        """Test 3yr No Upfront RI savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, ri_3yr_no_upfront=0.0410)
        savings = pricing.calculate_savings_percentage("ri_3yr_no_upfront")
        # 0.0410 is about 57.3% savings from 0.0960
        assert abs(savings - 57.29) < 0.01

    def test_calculate_savings_3yr_partial_upfront(self):
        """Test 3yr Partial Upfront RI savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, ri_3yr_partial_upfront=0.0190)
        savings = pricing.calculate_savings_percentage("ri_3yr_partial_upfront")
        # 0.0190 is about 80.2% savings from 0.0960
        assert abs(savings - 80.21) < 0.01

    def test_calculate_savings_3yr_all_upfront(self):
        """Test 3yr All Upfront RI savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, ri_3yr_all_upfront=0.0180)
        savings = pricing.calculate_savings_percentage("ri_3yr_all_upfront")
        # 0.0180 is 81.25% savings from 0.0960
        assert savings == 81.25

    def test_calculate_savings_ri_price_none(self):
        """Test RI savings calculation when RI price is None"""
        pricing = PricingInfo(on_demand_price=0.0960, ri_1yr_no_upfront=None)
        savings = pricing.calculate_savings_percentage("ri_1yr_no_upfront")
        assert savings is None

    def test_calculate_savings_on_demand_none(self):
        """Test savings calculation when on-demand price is None"""
        pricing = PricingInfo(on_demand_price=None, ri_1yr_no_upfront=0.0600)
        savings = pricing.calculate_savings_percentage("ri_1yr_no_upfront")
        assert savings is None

    def test_calculate_savings_1yr_savings_plan(self):
        """Test 1-year savings plan savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, savings_plan_1yr_no_upfront=0.0600)
        savings = pricing.calculate_savings_percentage("1yr")
        assert abs(savings - 37.5) < 0.01

    def test_calculate_savings_3yr_savings_plan(self):
        """Test 3-year savings plan savings calculation"""
        pricing = PricingInfo(on_demand_price=0.0960, savings_plan_3yr_no_upfront=0.0410)
        savings = pricing.calculate_savings_percentage("3yr")
        # 0.0410 is about 57.3% savings from 0.0960
        assert abs(savings - 57.29) < 0.01

    def test_calculate_savings_invalid_type(self):
        """Test savings calculation with invalid price type"""
        pricing = PricingInfo(on_demand_price=0.0960)
        savings = pricing.calculate_savings_percentage("invalid_type")
        assert savings is None


class TestPricingInfoCreation:
    """Test PricingInfo model creation with RI fields"""

    def test_create_pricing_info_all_ri_fields(self):
        """Test creating PricingInfo with all RI fields"""
        pricing = PricingInfo(
            on_demand_price=0.0960,
            spot_price=0.0288,
            ri_1yr_no_upfront=0.0600,
            ri_1yr_partial_upfront=0.0290,
            ri_1yr_all_upfront=0.0280,
            ri_3yr_no_upfront=0.0410,
            ri_3yr_partial_upfront=0.0190,
            ri_3yr_all_upfront=0.0180
        )

        assert pricing.on_demand_price == 0.0960
        assert pricing.spot_price == 0.0288
        assert pricing.ri_1yr_no_upfront == 0.0600
        assert pricing.ri_1yr_partial_upfront == 0.0290
        assert pricing.ri_1yr_all_upfront == 0.0280
        assert pricing.ri_3yr_no_upfront == 0.0410
        assert pricing.ri_3yr_partial_upfront == 0.0190
        assert pricing.ri_3yr_all_upfront == 0.0180

    def test_create_pricing_info_default_ri_fields(self):
        """Test creating PricingInfo with default (None) RI fields"""
        pricing = PricingInfo(on_demand_price=0.0960)

        assert pricing.on_demand_price == 0.0960
        assert pricing.ri_1yr_no_upfront is None
        assert pricing.ri_1yr_partial_upfront is None
        assert pricing.ri_1yr_all_upfront is None
        assert pricing.ri_3yr_no_upfront is None
        assert pricing.ri_3yr_partial_upfront is None
        assert pricing.ri_3yr_all_upfront is None
