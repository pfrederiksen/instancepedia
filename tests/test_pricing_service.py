"""Tests for PricingService"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from botocore.exceptions import ClientError, BotoCoreError

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


class TestSpotPriceHistory:
    """Test get_spot_price_history method"""

    def test_get_spot_price_history_success(self, pricing_service, mock_aws_client):
        """Test successful spot price history fetch with statistics"""
        from datetime import datetime, timezone

        # Mock EC2 response with multiple price points
        now = datetime.now(timezone.utc)
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'Timestamp': now, 'SpotPrice': '0.0104'},
                {'Timestamp': now, 'SpotPrice': '0.0120'},
                {'Timestamp': now, 'SpotPrice': '0.0095'},
                {'Timestamp': now, 'SpotPrice': '0.0110'},
                {'Timestamp': now, 'SpotPrice': '0.0100'},
            ]
        }
        mock_aws_client.ec2_client = mock_ec2_client

        # Call method
        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1", days=30)

        # Verify result
        assert history is not None
        assert history.instance_type == "t3.micro"
        assert history.region == "us-east-1"
        assert history.days == 30
        assert history.current_price == 0.0100  # Last price in list
        assert history.min_price == 0.0095
        assert history.max_price == 0.0120
        assert abs(history.avg_price - 0.01058) < 0.0001  # Mean of prices
        assert history.median_price == 0.0104
        assert history.std_dev is not None
        assert len(history.price_points) == 5

    def test_get_spot_price_history_single_price_point(self, pricing_service, mock_aws_client):
        """Test spot price history with single price point (std_dev should be None)"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'Timestamp': now, 'SpotPrice': '0.0104'},
            ]
        }
        mock_aws_client.ec2_client = mock_ec2_client

        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1")

        assert history is not None
        assert history.current_price == 0.0104
        assert history.min_price == 0.0104
        assert history.max_price == 0.0104
        assert history.avg_price == 0.0104
        assert history.median_price == 0.0104
        assert history.std_dev is None  # Cannot calculate std_dev with 1 point
        assert len(history.price_points) == 1

    def test_get_spot_price_history_empty_response(self, pricing_service, mock_aws_client):
        """Test spot price history with empty response"""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': []
        }
        mock_aws_client.ec2_client = mock_ec2_client

        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1")

        assert history is None

    def test_get_spot_price_history_no_key(self, pricing_service, mock_aws_client):
        """Test spot price history with missing SpotPriceHistory key"""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.return_value = {}
        mock_aws_client.ec2_client = mock_ec2_client

        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1")

        assert history is None

    def test_get_spot_price_history_sorting(self, pricing_service, mock_aws_client):
        """Test that price points are sorted oldest first"""
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        older = now - timedelta(hours=2)
        oldest = now - timedelta(hours=4)

        # Provide prices in random order
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'Timestamp': now, 'SpotPrice': '0.0104'},
                {'Timestamp': oldest, 'SpotPrice': '0.0095'},
                {'Timestamp': older, 'SpotPrice': '0.0110'},
            ]
        }
        mock_aws_client.ec2_client = mock_ec2_client

        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1")

        assert history is not None
        # Verify sorted order (oldest first)
        assert history.price_points[0][0] == oldest
        assert history.price_points[1][0] == older
        assert history.price_points[2][0] == now
        # Current price should be the last (most recent)
        assert history.current_price == 0.0104

    def test_get_spot_price_history_client_error(self, pricing_service, mock_aws_client):
        """Test spot price history handles ClientError gracefully"""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.side_effect = ClientError(
            {'Error': {'Code': 'RequestLimitExceeded'}}, 'describe_spot_price_history'
        )
        mock_aws_client.ec2_client = mock_ec2_client

        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1")

        assert history is None

    def test_get_spot_price_history_botocore_error(self, pricing_service, mock_aws_client):
        """Test spot price history handles BotoCoreError gracefully"""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.side_effect = BotoCoreError()
        mock_aws_client.ec2_client = mock_ec2_client

        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1")

        assert history is None

    def test_get_spot_price_history_generic_exception(self, pricing_service, mock_aws_client):
        """Test spot price history handles generic exception gracefully"""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.side_effect = Exception("Unexpected error")
        mock_aws_client.ec2_client = mock_ec2_client

        history = pricing_service.get_spot_price_history("t3.micro", "us-east-1")

        assert history is None


class TestSpotPriceHistoryProperties:
    """Test SpotPriceHistory dataclass properties"""

    def test_volatility_percentage_normal(self):
        """Test volatility percentage calculation with normal values"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=0.0104,
            min_price=0.0095,
            max_price=0.0120,
            avg_price=0.0105,
            median_price=0.0104,
            std_dev=0.0010,
            price_points=[(now, 0.0104)]
        )

        volatility = history.volatility_percentage
        # std_dev / avg_price * 100 = 0.0010 / 0.0105 * 100 ≈ 9.52%
        assert volatility is not None
        assert abs(volatility - 9.52) < 0.1

    def test_volatility_percentage_none_std_dev(self):
        """Test volatility percentage with None std_dev"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=0.0104,
            min_price=0.0104,
            max_price=0.0104,
            avg_price=0.0104,
            median_price=0.0104,
            std_dev=None,  # Single price point
            price_points=[(now, 0.0104)]
        )

        volatility = history.volatility_percentage
        assert volatility is None

    def test_volatility_percentage_zero_avg_price(self):
        """Test volatility percentage with zero average price"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=0.0,
            min_price=0.0,
            max_price=0.0,
            avg_price=0.0,  # Zero average
            median_price=0.0,
            std_dev=0.0,
            price_points=[(now, 0.0)]
        )

        volatility = history.volatility_percentage
        assert volatility is None  # Cannot divide by zero

    def test_price_range_normal(self):
        """Test price range calculation with normal values"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=0.0104,
            min_price=0.0095,
            max_price=0.0120,
            avg_price=0.0105,
            median_price=0.0104,
            std_dev=0.0010,
            price_points=[(now, 0.0104)]
        )

        price_range = history.price_range
        # max_price - min_price = 0.0120 - 0.0095 = 0.0025
        assert price_range is not None
        assert abs(price_range - 0.0025) < 0.0001

    def test_price_range_none_values(self):
        """Test price range with None min/max prices"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=None,
            min_price=None,
            max_price=None,
            avg_price=None,
            median_price=None,
            std_dev=None,
            price_points=[]
        )

        price_range = history.price_range
        assert price_range is None

    def test_savings_vs_current_normal(self):
        """Test savings vs current price calculation with normal values"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=0.0120,
            min_price=0.0095,
            max_price=0.0120,
            avg_price=0.0105,
            median_price=0.0104,
            std_dev=0.0010,
            price_points=[(now, 0.0120)]
        )

        savings = history.savings_vs_current
        # (current - min) / current * 100 = (0.0120 - 0.0095) / 0.0120 * 100 ≈ 20.83%
        assert savings is not None
        assert abs(savings - 20.83) < 0.1

    def test_savings_vs_current_none_values(self):
        """Test savings vs current with None values"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=None,
            min_price=None,
            max_price=None,
            avg_price=None,
            median_price=None,
            std_dev=None,
            price_points=[]
        )

        savings = history.savings_vs_current
        assert savings is None

    def test_savings_vs_current_zero_current_price(self):
        """Test savings vs current with zero current price"""
        from datetime import datetime, timezone
        from src.services.pricing_service import SpotPriceHistory

        now = datetime.now(timezone.utc)
        history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            current_price=0.0,  # Zero current price
            min_price=0.0095,
            max_price=0.0120,
            avg_price=0.0105,
            median_price=0.0104,
            std_dev=0.0010,
            price_points=[(now, 0.0)]
        )

        savings = history.savings_vs_current
        assert savings is None  # Cannot divide by zero


class TestGetSpotPricesBatch:
    """Tests for get_spot_prices_batch method"""

    def test_get_spot_prices_batch_single_chunk(self, pricing_service, mock_aws_client):
        """Test batch fetch with single chunk (< 50 instances)"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'InstanceType': 't3.micro', 'SpotPrice': '0.0104', 'Timestamp': now},
                {'InstanceType': 't3.small', 'SpotPrice': '0.0208', 'Timestamp': now},
                {'InstanceType': 't3.medium', 'SpotPrice': '0.0416', 'Timestamp': now},
            ]
        }
        mock_aws_client.ec2_client = mock_ec2_client

        # Call with 3 instance types (single chunk)
        result = pricing_service.get_spot_prices_batch(
            ['t3.micro', 't3.small', 't3.medium'],
            'us-east-1'
        )

        # Verify results
        assert result == {
            't3.micro': 0.0104,
            't3.small': 0.0208,
            't3.medium': 0.0416
        }
        # Verify single API call (no chunking needed)
        assert mock_ec2_client.describe_spot_price_history.call_count == 1

    def test_get_spot_prices_batch_multiple_chunks(self, pricing_service, mock_aws_client):
        """Test batch fetch with multiple chunks (> 50 instances)"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        mock_ec2_client = Mock()

        # Create 75 instance types (should trigger 2 chunks: 50 + 25)
        instance_types = [f't3.type{i}' for i in range(75)]

        # Mock responses for each chunk
        def mock_response(InstanceTypes, **kwargs):
            return {
                'SpotPriceHistory': [
                    {'InstanceType': inst_type, 'SpotPrice': f'0.{i:04d}', 'Timestamp': now}
                    for i, inst_type in enumerate(InstanceTypes)
                ]
            }

        mock_ec2_client.describe_spot_price_history.side_effect = mock_response
        mock_aws_client.ec2_client = mock_ec2_client

        # Call with 75 instance types
        result = pricing_service.get_spot_prices_batch(instance_types, 'us-east-1')

        # Verify all 75 instances have prices
        assert len(result) == 75
        # Verify 2 API calls (2 chunks: 50 + 25)
        assert mock_ec2_client.describe_spot_price_history.call_count == 2

    def test_get_spot_prices_batch_with_pagination(self, pricing_service, mock_aws_client):
        """Test batch fetch with NextToken pagination"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        mock_ec2_client = Mock()

        # Mock paginated responses
        mock_ec2_client.describe_spot_price_history.side_effect = [
            {
                'SpotPriceHistory': [
                    {'InstanceType': 't3.micro', 'SpotPrice': '0.0104', 'Timestamp': now},
                ],
                'NextToken': 'token123'
            },
            {
                'SpotPriceHistory': [
                    {'InstanceType': 't3.small', 'SpotPrice': '0.0208', 'Timestamp': now},
                ]
                # No NextToken - last page
            }
        ]
        mock_aws_client.ec2_client = mock_ec2_client

        # Call batch method
        result = pricing_service.get_spot_prices_batch(['t3.micro', 't3.small'], 'us-east-1')

        # Verify both prices collected from paginated results
        assert result == {
            't3.micro': 0.0104,
            't3.small': 0.0208
        }
        # Verify 2 API calls (pagination)
        assert mock_ec2_client.describe_spot_price_history.call_count == 2
        # Verify second call included NextToken
        second_call_kwargs = mock_ec2_client.describe_spot_price_history.call_args_list[1][1]
        assert second_call_kwargs['NextToken'] == 'token123'

    def test_get_spot_prices_batch_most_recent_price(self, pricing_service, mock_aws_client):
        """Test batch fetch keeps most recent price per instance type"""
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=1)

        mock_ec2_client = Mock()
        # Return multiple prices for same instance type with different timestamps
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'InstanceType': 't3.micro', 'SpotPrice': '0.0100', 'Timestamp': old_time},  # Older
                {'InstanceType': 't3.micro', 'SpotPrice': '0.0104', 'Timestamp': now},  # Most recent
                {'InstanceType': 't3.micro', 'SpotPrice': '0.0095', 'Timestamp': old_time - timedelta(hours=1)},  # Oldest
            ]
        }
        mock_aws_client.ec2_client = mock_ec2_client

        # Call batch method
        result = pricing_service.get_spot_prices_batch(['t3.micro'], 'us-east-1')

        # Verify only most recent price kept
        assert result == {'t3.micro': 0.0104}

    def test_get_spot_prices_batch_client_error_no_retry(self, pricing_service, mock_aws_client):
        """Test batch fetch doesn't retry non-rate-limit ClientErrors"""
        mock_ec2_client = Mock()

        # Non-rate-limit error (should not retry)
        mock_ec2_client.describe_spot_price_history.side_effect = ClientError(
            {'Error': {'Code': 'InvalidParameterValue'}},
            'describe_spot_price_history'
        )
        mock_aws_client.ec2_client = mock_ec2_client

        result = pricing_service.get_spot_prices_batch(['t3.micro'], 'us-east-1', max_retries=3)

        # Verify marked as None (no retries for non-rate-limit errors)
        assert result == {'t3.micro': None}
        # Verify only 1 API call (no retries)
        assert mock_ec2_client.describe_spot_price_history.call_count == 1

    def test_get_spot_prices_batch_pagination_error(self, pricing_service, mock_aws_client):
        """Test batch fetch handles pagination errors gracefully"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        mock_ec2_client = Mock()

        # First page succeeds, second page fails
        mock_ec2_client.describe_spot_price_history.side_effect = [
            {
                'SpotPriceHistory': [
                    {'InstanceType': 't3.micro', 'SpotPrice': '0.0104', 'Timestamp': now},
                ],
                'NextToken': 'token123'
            },
            Exception("Connection timeout")
        ]
        mock_aws_client.ec2_client = mock_ec2_client

        result = pricing_service.get_spot_prices_batch(['t3.micro'], 'us-east-1')

        # Verify first page data was kept despite second page error
        assert result == {'t3.micro': 0.0104}

    def test_get_spot_prices_batch_empty_list(self, pricing_service, mock_aws_client):
        """Test batch fetch with empty instance list"""
        result = pricing_service.get_spot_prices_batch([], 'us-east-1')

        # Verify empty result
        assert result == {}

    def test_get_spot_prices_batch_generic_exception(self, pricing_service, mock_aws_client):
        """Test batch fetch handles generic exceptions"""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_spot_price_history.side_effect = Exception("Network error")
        mock_aws_client.ec2_client = mock_ec2_client

        result = pricing_service.get_spot_prices_batch(['t3.micro', 't3.small'], 'us-east-1', max_retries=1)

        # Verify all marked as None after retries exhausted
        assert result == {'t3.micro': None, 't3.small': None}

    def test_get_spot_prices_batch_mixed_success_failure(self, pricing_service, mock_aws_client):
        """Test batch fetch with mixed chunk success/failure"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        mock_ec2_client = Mock()

        # Create 75 instance types (2 chunks: 50 + 25)
        instance_types = [f't3.type{i}' for i in range(75)]

        # First chunk succeeds, second chunk fails
        def mock_response(InstanceTypes, **kwargs):
            if len(InstanceTypes) == 50:  # First chunk
                return {
                    'SpotPriceHistory': [
                        {'InstanceType': inst_type, 'SpotPrice': '0.0100', 'Timestamp': now}
                        for inst_type in InstanceTypes
                    ]
                }
            else:  # Second chunk
                raise ClientError(
                    {'Error': {'Code': 'InvalidParameterValue'}},
                    'describe_spot_price_history'
                )

        mock_ec2_client.describe_spot_price_history.side_effect = mock_response
        mock_aws_client.ec2_client = mock_ec2_client

        result = pricing_service.get_spot_prices_batch(instance_types, 'us-east-1')

        # Verify first 50 have prices, last 25 are None
        for i in range(50):
            assert result[f't3.type{i}'] == 0.0100
        for i in range(50, 75):
            assert result[f't3.type{i}'] is None
