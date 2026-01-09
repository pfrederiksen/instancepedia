"""Tests for PricingService"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

from src.services.pricing_service import PricingService
from src.services.aws_client import AWSClient


@pytest.fixture
def mock_aws_client():
    """Create mock AWS client"""
    client = Mock(spec=AWSClient)
    client.region = "us-east-1"
    return client


@pytest.fixture
def mock_pricing_cache():
    """Create mock pricing cache"""
    cache = Mock()
    cache.get = Mock(return_value=None)  # Default: cache miss
    cache.set = Mock()
    return cache


@pytest.fixture
def pricing_service(mock_aws_client):
    """Create PricingService with mocked dependencies"""
    with patch('src.services.pricing_service.get_pricing_cache') as mock_get_cache:
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)
        mock_cache.set = Mock()
        mock_get_cache.return_value = mock_cache

        service = PricingService(mock_aws_client, use_cache=True)
        service.cache = mock_cache  # Store reference for assertions
        return service


class TestPricingServiceInit:
    """Test PricingService initialization"""

    def test_init_with_cache_enabled(self, mock_aws_client):
        """Test initialization with caching enabled"""
        with patch('src.services.pricing_service.get_pricing_cache') as mock_get_cache:
            mock_cache = Mock()
            mock_get_cache.return_value = mock_cache

            service = PricingService(mock_aws_client, use_cache=True)

            assert service.aws_client == mock_aws_client
            assert service.use_cache is True
            assert service.cache == mock_cache

    def test_init_with_cache_disabled(self, mock_aws_client):
        """Test initialization with caching disabled"""
        service = PricingService(mock_aws_client, use_cache=False)

        assert service.aws_client == mock_aws_client
        assert service.use_cache is False
        assert service.cache is None

    def test_init_default_cache_enabled(self, mock_aws_client):
        """Test initialization defaults to cache enabled"""
        with patch('src.services.pricing_service.get_pricing_cache') as mock_get_cache:
            mock_cache = Mock()
            mock_get_cache.return_value = mock_cache

            service = PricingService(mock_aws_client)  # No use_cache arg

            assert service.use_cache is True
            assert service.cache == mock_cache


class TestGetOnDemandPrice:
    """Test get_on_demand_price method"""

    def test_get_on_demand_price_cache_hit(self, pricing_service, mock_aws_client):
        """Test getting price from cache"""
        pricing_service.cache.get.return_value = 0.0104

        price = pricing_service.get_on_demand_price("t3.micro", "us-east-1")

        assert price == 0.0104
        pricing_service.cache.get.assert_called_once_with("us-east-1", "t3.micro", "on_demand")
        # Cache set should not be called on cache hit
        pricing_service.cache.set.assert_not_called()

    def test_get_on_demand_price_cache_miss(self, pricing_service, mock_aws_client):
        """Test fetching price from AWS on cache miss"""
        pricing_service.cache.get.return_value = None  # Cache miss

        # Mock pricing client
        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_price_item(instance_type="t3.micro", price="0.0104")
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_on_demand_price("t3.micro", "us-east-1")

        assert price == 0.0104
        pricing_service.cache.set.assert_called_once_with("us-east-1", "t3.micro", "on_demand", 0.0104)

    @patch('src.services.pricing_service.DebugLog')
    def test_get_on_demand_price_region_not_in_map(self, mock_debug, pricing_service, mock_aws_client):
        """Test handling of unmapped region (uses region code directly)"""
        pricing_service.cache.get.return_value = None

        # Mock pricing client to return no results for unknown region
        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {'PriceList': []}
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_on_demand_price("t3.micro", "unknown-region-1")

        # Should attempt to fetch using region code directly and return None
        assert price is None

    def test_get_on_demand_price_no_results(self, pricing_service, mock_aws_client):
        """Test when pricing API returns no results"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {'PriceList': []}
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_on_demand_price("nonexistent.type", "us-east-1")

        assert price is None

    def test_get_on_demand_price_with_retries(self, pricing_service, mock_aws_client):
        """Test retry logic on throttling"""
        pricing_service.cache.get.return_value = None

        from botocore.exceptions import ClientError
        mock_pricing_client = MagicMock()
        # First call throttles, second succeeds
        mock_pricing_client.get_products.side_effect = [
            ClientError({'Error': {'Code': 'Throttling'}}, 'GetProducts'),
            {'PriceList': [json_price_item(instance_type="t3.micro", price="0.0104")]}
        ]
        mock_aws_client.pricing_client = mock_pricing_client

        with patch('time.sleep'):  # Don't actually sleep in tests
            price = pricing_service.get_on_demand_price("t3.micro", "us-east-1", max_retries=3)

        assert price == 0.0104
        assert mock_pricing_client.get_products.call_count == 2


class TestGetSpotPrice:
    """Test get_spot_price method"""

    def test_get_spot_price_cache_hit(self, pricing_service, mock_aws_client):
        """Test getting spot price from cache"""
        pricing_service.cache.get.return_value = 0.0036

        price = pricing_service.get_spot_price("t3.micro", "us-east-1")

        assert price == 0.0036
        pricing_service.cache.get.assert_called_once_with("us-east-1", "t3.micro", "spot")

    def test_get_spot_price_cache_miss(self, pricing_service, mock_aws_client):
        """Test fetching spot price from AWS"""
        pricing_service.cache.get.return_value = None

        mock_ec2_client = MagicMock()
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'SpotPrice': '0.0036', 'Timestamp': '2025-01-01', 'InstanceType': 't3.micro'}
            ]
        }
        mock_aws_client.ec2_client = mock_ec2_client

        price = pricing_service.get_spot_price("t3.micro", "us-east-1")

        assert price == 0.0036
        pricing_service.cache.set.assert_called_once_with("us-east-1", "t3.micro", "spot", 0.0036)

    def test_get_spot_price_no_history(self, pricing_service, mock_aws_client):
        """Test when no spot price history exists"""
        pricing_service.cache.get.return_value = None

        mock_ec2_client = MagicMock()
        mock_ec2_client.describe_spot_price_history.return_value = {'SpotPriceHistory': []}
        mock_aws_client.ec2_client = mock_ec2_client

        price = pricing_service.get_spot_price("t3.micro", "us-east-1")

        assert price is None
        pricing_service.cache.set.assert_called_once_with("us-east-1", "t3.micro", "spot", None)

    def test_get_spot_price_api_error(self, pricing_service, mock_aws_client):
        """Test handling of API errors"""
        pricing_service.cache.get.return_value = None

        mock_ec2_client = MagicMock()
        mock_ec2_client.describe_spot_price_history.side_effect = Exception("API Error")
        mock_aws_client.ec2_client = mock_ec2_client

        price = pricing_service.get_spot_price("t3.micro", "us-east-1")

        assert price is None
        pricing_service.cache.set.assert_called_once_with("us-east-1", "t3.micro", "spot", None)




def json_price_item(instance_type: str, price: str) -> str:
    """Helper to create JSON price list item"""
    import json
    return json.dumps({
        'product': {
            'attributes': {
                'location': 'US East (N. Virginia)',
                'instanceType': instance_type
            }
        },
        'terms': {
            'OnDemand': {
                'TERM123': {
                    'priceDimensions': {
                        'DIM123': {
                            'unit': 'Hrs',
                            'pricePerUnit': {'USD': price}
                        }
                    }
                }
            }
        }
    })


def json_reserved_price_item(
    instance_type: str,
    lease_length: str,
    payment_option: str,
    price: str,
    offering_class: str = "standard"
) -> str:
    """Helper to create JSON Reserved Instance price list item"""
    import json
    return json.dumps({
        'product': {
            'attributes': {
                'location': 'US East (N. Virginia)',
                'instanceType': instance_type
            }
        },
        'terms': {
            'Reserved': {
                'TERM456': {
                    'termAttributes': {
                        'LeaseContractLength': lease_length,
                        'PurchaseOption': payment_option,
                        'OfferingClass': offering_class
                    },
                    'priceDimensions': {
                        'DIM456': {
                            'unit': 'Hrs',
                            'pricePerUnit': {'USD': price}
                        }
                    }
                }
            }
        }
    })


class TestGetReservedInstancePrice:
    """Test get_reserved_instance_price method"""

    def test_get_ri_price_cache_hit(self, pricing_service, mock_aws_client):
        """Test getting RI price from cache"""
        pricing_service.cache.get.return_value = 0.0290

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="1yr", payment_option="partial_upfront"
        )

        assert price == 0.0290
        pricing_service.cache.get.assert_called_once_with(
            "us-east-1", "m5.large", "ri_1yr_partial_upfront"
        )
        pricing_service.cache.set.assert_not_called()

    def test_get_ri_price_cache_miss_1yr_no_upfront(self, pricing_service, mock_aws_client):
        """Test fetching 1yr No Upfront RI price from AWS"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="1yr",
                    payment_option="No Upfront",
                    price="0.0600"
                )
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="1yr", payment_option="no_upfront"
        )

        assert price == 0.0600
        pricing_service.cache.set.assert_called_once_with(
            "us-east-1", "m5.large", "ri_1yr_no_upfront", 0.0600
        )

    def test_get_ri_price_cache_miss_1yr_partial_upfront(self, pricing_service, mock_aws_client):
        """Test fetching 1yr Partial Upfront RI price from AWS"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="1yr",
                    payment_option="Partial Upfront",
                    price="0.0290"
                )
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="1yr", payment_option="partial_upfront"
        )

        assert price == 0.0290
        pricing_service.cache.set.assert_called_once_with(
            "us-east-1", "m5.large", "ri_1yr_partial_upfront", 0.0290
        )

    def test_get_ri_price_cache_miss_1yr_all_upfront(self, pricing_service, mock_aws_client):
        """Test fetching 1yr All Upfront RI price from AWS"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="1yr",
                    payment_option="All Upfront",
                    price="0.0280"
                )
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="1yr", payment_option="all_upfront"
        )

        assert price == 0.0280
        pricing_service.cache.set.assert_called_once_with(
            "us-east-1", "m5.large", "ri_1yr_all_upfront", 0.0280
        )

    def test_get_ri_price_cache_miss_3yr_no_upfront(self, pricing_service, mock_aws_client):
        """Test fetching 3yr No Upfront RI price from AWS"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="3yr",
                    payment_option="No Upfront",
                    price="0.0410"
                )
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="3yr", payment_option="no_upfront"
        )

        assert price == 0.0410
        pricing_service.cache.set.assert_called_once_with(
            "us-east-1", "m5.large", "ri_3yr_no_upfront", 0.0410
        )

    def test_get_ri_price_cache_miss_3yr_partial_upfront(self, pricing_service, mock_aws_client):
        """Test fetching 3yr Partial Upfront RI price from AWS"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="3yr",
                    payment_option="Partial Upfront",
                    price="0.0190"
                )
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="3yr", payment_option="partial_upfront"
        )

        assert price == 0.0190
        pricing_service.cache.set.assert_called_once_with(
            "us-east-1", "m5.large", "ri_3yr_partial_upfront", 0.0190
        )

    def test_get_ri_price_cache_miss_3yr_all_upfront(self, pricing_service, mock_aws_client):
        """Test fetching 3yr All Upfront RI price from AWS"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="3yr",
                    payment_option="All Upfront",
                    price="0.0180"
                )
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="3yr", payment_option="all_upfront"
        )

        assert price == 0.0180
        pricing_service.cache.set.assert_called_once_with(
            "us-east-1", "m5.large", "ri_3yr_all_upfront", 0.0180
        )

    def test_get_ri_price_filters_convertible(self, pricing_service, mock_aws_client):
        """Test that Convertible RIs are excluded (only Standard returned)"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        # Return both standard and convertible, should only use standard
        mock_pricing_client.get_products.return_value = {
            'PriceList': [
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="1yr",
                    payment_option="No Upfront",
                    price="0.0700",
                    offering_class="convertible"  # Should be filtered out
                ),
                json_reserved_price_item(
                    instance_type="m5.large",
                    lease_length="1yr",
                    payment_option="No Upfront",
                    price="0.0600",
                    offering_class="standard"  # Should be used
                )
            ]
        }
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "m5.large", "us-east-1", lease_length="1yr", payment_option="no_upfront"
        )

        # Should return standard RI price, not convertible
        assert price == 0.0600

    def test_get_ri_price_no_results(self, pricing_service, mock_aws_client):
        """Test when pricing API returns no RI results"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.return_value = {'PriceList': []}
        mock_aws_client.pricing_client = mock_pricing_client

        price = pricing_service.get_reserved_instance_price(
            "nonexistent.type", "us-east-1", lease_length="1yr", payment_option="no_upfront"
        )

        assert price is None
        # None should be cached to avoid repeated API calls
        pricing_service.cache.set.assert_called_once_with(
            "us-east-1", "nonexistent.type", "ri_1yr_no_upfront", None
        )

    def test_get_ri_price_with_retries(self, pricing_service, mock_aws_client):
        """Test retry logic on throttling for RI pricing"""
        pricing_service.cache.get.return_value = None

        from botocore.exceptions import ClientError
        mock_pricing_client = MagicMock()
        # First call throttles, second succeeds
        mock_pricing_client.get_products.side_effect = [
            ClientError({'Error': {'Code': 'Throttling'}}, 'GetProducts'),
            {
                'PriceList': [
                    json_reserved_price_item(
                        instance_type="m5.large",
                        lease_length="1yr",
                        payment_option="Partial Upfront",
                        price="0.0290"
                    )
                ]
            }
        ]
        mock_aws_client.pricing_client = mock_pricing_client

        with patch('time.sleep'):  # Don't actually sleep in tests
            price = pricing_service.get_reserved_instance_price(
                "m5.large", "us-east-1",
                lease_length="1yr",
                payment_option="partial_upfront",
                max_retries=3
            )

        assert price == 0.0290
        assert mock_pricing_client.get_products.call_count == 2

    def test_get_ri_price_api_error(self, pricing_service, mock_aws_client):
        """Test handling of API errors for RI pricing"""
        pricing_service.cache.get.return_value = None

        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.side_effect = Exception("API Error")
        mock_aws_client.pricing_client = mock_pricing_client

        with patch('time.sleep'):  # Don't actually sleep in tests
            price = pricing_service.get_reserved_instance_price(
                "m5.large", "us-east-1", lease_length="1yr", payment_option="no_upfront", max_retries=2
            )

        assert price is None
        # On API error after retries, None is NOT cached (allows retry on next request)
        pricing_service.cache.set.assert_not_called()
