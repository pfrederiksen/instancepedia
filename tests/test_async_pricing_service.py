"""Tests for async pricing service error scenarios"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from src.services.async_pricing_service import AsyncPricingService


@pytest.fixture
def mock_async_client():
    """Create a mock async AWS client"""
    client = Mock()
    client.region = "us-east-1"
    client.profile = None
    return client


@pytest.fixture
def mock_cache():
    """Create a mock cache that misses by default"""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    return cache


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    settings = Mock()
    settings.pricing_request_delay_ms = 0  # No delay for tests
    settings.spot_batch_size = 50
    return settings


class TestAsyncPricingServiceErrorScenarios:
    """Tests for error handling in AsyncPricingService"""

    @pytest.mark.asyncio
    async def test_empty_results_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that empty API results return None"""
        # Mock pricing client to return empty results
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={'PriceList': []})
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_on_demand_price("t3.micro", "us-east-1")

            assert price is None
            # Verify None was cached
            mock_cache.set.assert_called_with("us-east-1", "t3.micro", "on_demand", None)

    @pytest.mark.asyncio
    async def test_throttling_retries_and_succeeds(self, mock_async_client, mock_cache, mock_settings):
        """Test that throttling errors trigger retries and eventually succeed"""
        # First call raises throttling, second succeeds
        throttle_error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'GetProducts'
        )

        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(side_effect=[
            throttle_error,
            {'PriceList': [
                '{"product":{"attributes":{"location":"US East (N. Virginia)"}},"terms":{"OnDemand":{"term1":{"priceDimensions":{"dim1":{"unit":"Hrs","pricePerUnit":{"USD":"0.0104"}}}}}}}'
            ]}
        ])
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

                price = await service.get_on_demand_price("t3.micro", "us-east-1", max_retries=3)

                # Should have retried and succeeded
                assert price == 0.0104

    @pytest.mark.asyncio
    async def test_throttling_all_retries_fail(self, mock_async_client, mock_cache, mock_settings):
        """Test that after all retries fail, returns None"""
        throttle_error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'GetProducts'
        )

        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(side_effect=throttle_error)
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

                price = await service.get_on_demand_price("t3.micro", "us-east-1", max_retries=2)

                assert price is None

    @pytest.mark.asyncio
    async def test_generic_client_error_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that generic client errors return None"""
        error = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'GetProducts'
        )

        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(side_effect=error)
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_on_demand_price("t3.micro", "us-east-1")

            assert price is None

    @pytest.mark.asyncio
    async def test_general_exception_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that general exceptions return None after retries"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(side_effect=Exception("Network error"))
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

                price = await service.get_on_demand_price("t3.micro", "us-east-1", max_retries=1)

                assert price is None

    @pytest.mark.asyncio
    async def test_invalid_region_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that invalid region returns None and caches result"""
        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_on_demand_price("t3.micro", "invalid-region-999")

            assert price is None
            # Verify None was cached for invalid region
            mock_cache.set.assert_called_with("invalid-region-999", "t3.micro", "on_demand", None)


class TestAsyncSpotPriceErrorScenarios:
    """Tests for spot price error handling"""

    @pytest.mark.asyncio
    async def test_spot_empty_history_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that empty spot price history returns None"""
        mock_ec2 = AsyncMock()
        mock_ec2.describe_spot_price_history = AsyncMock(return_value={'SpotPriceHistory': []})
        mock_ec2.__aenter__ = AsyncMock(return_value=mock_ec2)
        mock_ec2.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_ec2_client = Mock(return_value=mock_ec2)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_spot_price("t3.micro", "us-east-1")

            assert price is None
            mock_cache.set.assert_called_with("us-east-1", "t3.micro", "spot", None)

    @pytest.mark.asyncio
    async def test_spot_api_error_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that spot price API errors return None"""
        mock_ec2 = AsyncMock()
        mock_ec2.describe_spot_price_history = AsyncMock(side_effect=Exception("API Error"))
        mock_ec2.__aenter__ = AsyncMock(return_value=mock_ec2)
        mock_ec2.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_ec2_client = Mock(return_value=mock_ec2)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_spot_price("t3.micro", "us-east-1")

            assert price is None
            # Error should still cache None
            mock_cache.set.assert_called_with("us-east-1", "t3.micro", "spot", None)


class TestAsyncBatchPricingErrorScenarios:
    """Tests for batch pricing error handling"""

    @pytest.mark.asyncio
    async def test_batch_partial_failures(self, mock_async_client, mock_cache, mock_settings):
        """Test that batch pricing handles partial failures gracefully"""
        # Create responses for different instance types
        call_count = [0]

        async def mock_get_products(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call fails
                raise Exception("Network error")
            return {
                'PriceList': [
                    '{"product":{"attributes":{"location":"US East (N. Virginia)"}},"terms":{"OnDemand":{"term1":{"priceDimensions":{"dim1":{"unit":"Hrs","pricePerUnit":{"USD":"0.0104"}}}}}}}'
                ]
            }

        mock_pricing = AsyncMock()
        mock_pricing.get_products = mock_get_products
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

                # Request 3 prices, one will fail
                instance_types = ["t3.micro", "t3.small", "t3.medium"]
                results = await service.get_on_demand_prices_batch(
                    instance_types,
                    "us-east-1",
                    concurrency=1  # Serial execution for predictable test
                )

                # Should have results for all instance types (even if None)
                assert len(results) == 3
                assert "t3.micro" in results
                assert "t3.small" in results
                assert "t3.medium" in results

    @pytest.mark.asyncio
    async def test_batch_all_failures_returns_nones(self, mock_async_client, mock_cache, mock_settings):
        """Test that batch pricing returns None for all when all fail"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(side_effect=Exception("Service down"))
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

                instance_types = ["t3.micro", "t3.small"]
                results = await service.get_on_demand_prices_batch(
                    instance_types,
                    "us-east-1",
                    concurrency=2
                )

                # All should be None
                assert results["t3.micro"] is None
                assert results["t3.small"] is None

    @pytest.mark.asyncio
    async def test_batch_progress_callback_called(self, mock_async_client, mock_cache, mock_settings):
        """Test that progress callback is called during batch pricing"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={'PriceList': []})
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        progress_calls = []
        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            instance_types = ["t3.micro", "t3.small"]
            await service.get_on_demand_prices_batch(
                instance_types,
                "us-east-1",
                concurrency=1,
                progress_callback=progress_callback
            )

            # Progress callback should be called for each instance
            assert len(progress_calls) == 2
            # Check that we got progress updates (order may vary due to async)
            assert any(call[0] == 2 and call[1] == 2 for call in progress_calls)

    @pytest.mark.asyncio
    async def test_batch_price_callback_called(self, mock_async_client, mock_cache, mock_settings):
        """Test that price callback is called for each price"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={
            'PriceList': [
                '{"product":{"attributes":{"location":"US East (N. Virginia)"}},"terms":{"OnDemand":{"term1":{"priceDimensions":{"dim1":{"unit":"Hrs","pricePerUnit":{"USD":"0.0104"}}}}}}}'
            ]
        })
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        price_updates = []
        def price_callback(instance_type, price):
            price_updates.append((instance_type, price))

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            instance_types = ["t3.micro", "t3.small"]
            await service.get_on_demand_prices_batch(
                instance_types,
                "us-east-1",
                concurrency=1,
                price_callback=price_callback
            )

            # Price callback should be called for each instance
            assert len(price_updates) == 2
            instance_types_received = [p[0] for p in price_updates]
            assert "t3.micro" in instance_types_received
            assert "t3.small" in instance_types_received


class TestAsyncSpotBatchErrorScenarios:
    """Tests for batch spot pricing error handling"""

    @pytest.mark.asyncio
    async def test_spot_batch_empty_results(self, mock_async_client, mock_cache, mock_settings):
        """Test that batch spot pricing handles empty results"""
        mock_ec2 = AsyncMock()
        mock_ec2.describe_spot_price_history = AsyncMock(return_value={'SpotPriceHistory': []})
        mock_ec2.__aenter__ = AsyncMock(return_value=mock_ec2)
        mock_ec2.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_ec2_client = Mock(return_value=mock_ec2)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            instance_types = ["t3.micro", "t3.small"]
            results = await service.get_spot_prices_batch(instance_types, "us-east-1")

            # All should be None since no spot history returned
            assert results["t3.micro"] is None
            assert results["t3.small"] is None

    @pytest.mark.asyncio
    async def test_spot_batch_api_error(self, mock_async_client, mock_cache, mock_settings):
        """Test that batch spot pricing handles API errors"""
        mock_ec2 = AsyncMock()
        mock_ec2.describe_spot_price_history = AsyncMock(side_effect=Exception("API Error"))
        mock_ec2.__aenter__ = AsyncMock(return_value=mock_ec2)
        mock_ec2.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_ec2_client = Mock(return_value=mock_ec2)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            instance_types = ["t3.micro", "t3.small"]
            results = await service.get_spot_prices_batch(instance_types, "us-east-1")

            # Should return None for all on error
            assert results["t3.micro"] is None
            assert results["t3.small"] is None

    @pytest.mark.asyncio
    async def test_spot_batch_partial_results(self, mock_async_client, mock_cache, mock_settings):
        """Test that batch spot pricing returns partial results when some instances have no spot pricing"""
        from datetime import datetime

        mock_ec2 = AsyncMock()
        mock_ec2.describe_spot_price_history = AsyncMock(return_value={
            'SpotPriceHistory': [
                {
                    'InstanceType': 't3.micro',
                    'SpotPrice': '0.0031',
                    'Timestamp': datetime.now()
                }
                # t3.small has no spot pricing
            ]
        })
        mock_ec2.__aenter__ = AsyncMock(return_value=mock_ec2)
        mock_ec2.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_ec2_client = Mock(return_value=mock_ec2)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            instance_types = ["t3.micro", "t3.small"]
            results = await service.get_spot_prices_batch(instance_types, "us-east-1")

            # t3.micro should have price, t3.small should be None
            assert results["t3.micro"] == 0.0031
            assert results["t3.small"] is None


class TestAsyncReservedInstanceErrorScenarios:
    """Tests for Reserved Instance pricing error handling"""

    @pytest.mark.asyncio
    async def test_ri_invalid_lease_length(self, mock_async_client, mock_cache, mock_settings):
        """Test that invalid lease length returns None"""
        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_reserved_instance_price(
                "t3.micro", "us-east-1",
                lease_length="5yr",  # Invalid
                payment_option="no_upfront"
            )

            assert price is None

    @pytest.mark.asyncio
    async def test_ri_invalid_payment_option(self, mock_async_client, mock_cache, mock_settings):
        """Test that invalid payment option returns None"""
        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_reserved_instance_price(
                "t3.micro", "us-east-1",
                lease_length="1yr",
                payment_option="monthly"  # Invalid
            )

            assert price is None

    @pytest.mark.asyncio
    async def test_ri_empty_results_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that empty RI results return None"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={'PriceList': []})
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_reserved_instance_price(
                "t3.micro", "us-east-1",
                lease_length="1yr",
                payment_option="no_upfront"
            )

            assert price is None
            mock_cache.set.assert_called_with("us-east-1", "t3.micro", "ri_1yr_no_upfront", None)

    @pytest.mark.asyncio
    async def test_ri_throttling_retries(self, mock_async_client, mock_cache, mock_settings):
        """Test that RI pricing handles throttling with retries"""
        throttle_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'GetProducts'
        )

        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(side_effect=throttle_error)
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

                price = await service.get_reserved_instance_price(
                    "t3.micro", "us-east-1",
                    lease_length="1yr",
                    payment_option="partial_upfront",
                    max_retries=2
                )

                assert price is None


class TestAsyncSavingsPlanErrorScenarios:
    """Tests for Savings Plan pricing error handling"""

    @pytest.mark.asyncio
    async def test_savings_invalid_lease_length(self, mock_async_client, mock_cache, mock_settings):
        """Test that invalid savings plan lease length returns None"""
        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_savings_plan_price(
                "t3.micro", "us-east-1",
                lease_length="5yr"  # Invalid
            )

            assert price is None

    @pytest.mark.asyncio
    async def test_savings_empty_results_returns_none(self, mock_async_client, mock_cache, mock_settings):
        """Test that empty savings plan results return None"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={'PriceList': []})
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_savings_plan_price("t3.micro", "us-east-1", lease_length="1yr")

            assert price is None
            mock_cache.set.assert_called_with("us-east-1", "t3.micro", "savings_1yr", None)

    @pytest.mark.asyncio
    async def test_savings_throttling_retries(self, mock_async_client, mock_cache, mock_settings):
        """Test that savings plan pricing handles throttling with retries"""
        throttle_error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'GetProducts'
        )

        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(side_effect=throttle_error)
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

                price = await service.get_savings_plan_price(
                    "t3.micro", "us-east-1",
                    lease_length="3yr",
                    max_retries=2
                )

                assert price is None


class TestCacheHitCallback:
    """Tests for cache hit callback functionality"""

    @pytest.mark.asyncio
    async def test_cache_hit_callback_called(self, mock_async_client, mock_settings):
        """Test that cache hit callback is called on cache hits"""
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=0.0104)  # Cache hit
        mock_cache.set = Mock()

        callback_count = [0]
        def cache_hit_callback():
            callback_count[0] += 1

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_on_demand_price(
                "t3.micro", "us-east-1",
                cache_hit_callback=cache_hit_callback
            )

            assert price == 0.0104
            assert callback_count[0] == 1

    @pytest.mark.asyncio
    async def test_cache_hit_callback_not_called_on_miss(self, mock_async_client, mock_settings):
        """Test that cache hit callback is NOT called on cache miss"""
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)  # Cache miss
        mock_cache.set = Mock()

        callback_count = [0]
        def cache_hit_callback():
            callback_count[0] += 1

        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={'PriceList': []})
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            price = await service.get_on_demand_price(
                "t3.micro", "us-east-1",
                cache_hit_callback=cache_hit_callback
            )

            # Callback should NOT have been called (cache miss)
            assert callback_count[0] == 0


class TestPricingMetrics:
    """Tests for PricingMetrics dataclass"""

    def test_initial_state(self):
        """Test PricingMetrics initial state"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()

        assert metrics.total_requests == 0
        assert metrics.cache_hits == 0
        assert metrics.api_calls == 0
        assert metrics.successful_fetches == 0
        assert metrics.failed_fetches == 0
        assert metrics.end_time is None

    def test_record_cache_hit(self):
        """Test recording cache hits"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.record_cache_hit()
        metrics.record_cache_hit()

        assert metrics.cache_hits == 2
        assert metrics.total_requests == 2
        assert metrics.successful_fetches == 2
        assert metrics.api_calls == 0  # Cache hits don't count as API calls

    def test_record_api_call_success(self):
        """Test recording successful API calls"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.record_api_call(success=True)
        metrics.record_api_call(success=True)

        assert metrics.api_calls == 2
        assert metrics.total_requests == 2
        assert metrics.successful_fetches == 2
        assert metrics.failed_fetches == 0

    def test_record_api_call_failure(self):
        """Test recording failed API calls"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.record_api_call(success=False)
        metrics.record_api_call(success=True)
        metrics.record_api_call(success=False)

        assert metrics.api_calls == 3
        assert metrics.total_requests == 3
        assert metrics.successful_fetches == 1
        assert metrics.failed_fetches == 2

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.record_cache_hit()
        metrics.record_cache_hit()
        metrics.record_api_call(success=True)
        metrics.record_api_call(success=False)

        # 2 cache hits out of 4 total requests = 50%
        assert metrics.cache_hit_rate == 50.0

    def test_cache_hit_rate_zero_requests(self):
        """Test cache hit rate with no requests"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        assert metrics.cache_hit_rate == 0.0

    def test_success_rate(self):
        """Test success rate calculation"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.record_cache_hit()  # Success
        metrics.record_api_call(success=True)  # Success
        metrics.record_api_call(success=False)  # Failure

        # 2 successes out of 3 total = 66.67%
        assert round(metrics.success_rate, 1) == 66.7

    def test_success_rate_zero_requests(self):
        """Test success rate with no requests"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        assert metrics.success_rate == 0.0

    def test_elapsed_time_running(self):
        """Test elapsed time while metrics collection is running"""
        from src.services.async_pricing_service import PricingMetrics
        import time

        metrics = PricingMetrics()
        time.sleep(0.1)

        elapsed = metrics.elapsed_time
        assert elapsed >= 0.1

    def test_elapsed_time_finished(self):
        """Test elapsed time after metrics collection is finished"""
        from src.services.async_pricing_service import PricingMetrics
        import time

        metrics = PricingMetrics()
        time.sleep(0.1)
        metrics.finish()
        time.sleep(0.1)  # More time passes after finish

        # Elapsed time should be frozen at ~0.1s, not include the second sleep
        assert metrics.elapsed_time < 0.15

    def test_requests_per_second(self):
        """Test throughput calculation"""
        from src.services.async_pricing_service import PricingMetrics

        # Create metrics with known timing
        metrics = PricingMetrics()
        metrics.total_requests = 100
        metrics.start_time = 0
        metrics.end_time = 10  # 10 seconds elapsed

        assert metrics.requests_per_second == 10.0

    def test_requests_per_second_zero_elapsed(self):
        """Test throughput with zero elapsed time"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.start_time = 0
        metrics.end_time = 0

        assert metrics.requests_per_second == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.record_cache_hit()
        metrics.record_api_call(success=True)
        metrics.record_api_call(success=False)
        metrics.start_time = 0
        metrics.end_time = 1

        result = metrics.to_dict()

        assert result["total_requests"] == 3
        assert result["cache_hits"] == 1
        assert result["api_calls"] == 2
        assert result["successful_fetches"] == 2
        assert result["failed_fetches"] == 1
        assert result["cache_hit_rate"] == 33.3
        assert result["success_rate"] == 66.7
        assert result["elapsed_time"] == 1.0
        assert result["requests_per_second"] == 3.0

    def test_summary(self):
        """Test human-readable summary"""
        from src.services.async_pricing_service import PricingMetrics

        metrics = PricingMetrics()
        metrics.record_cache_hit()
        metrics.record_api_call(success=True)
        metrics.start_time = 0
        metrics.end_time = 1

        summary = metrics.summary()

        assert "2/2" in summary  # successful/total
        assert "100% success" in summary
        assert "50% cached" in summary
        assert "1.0s" in summary


class TestBatchPricingMetrics:
    """Tests for metrics integration in batch pricing"""

    @pytest.mark.asyncio
    async def test_batch_returns_metrics_when_requested(self, mock_async_client, mock_cache, mock_settings):
        """Test that batch pricing can return metrics"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={
            'PriceList': [
                '{"product":{"attributes":{"location":"US East (N. Virginia)"}},"terms":{"OnDemand":{"term1":{"priceDimensions":{"dim1":{"unit":"Hrs","pricePerUnit":{"USD":"0.0104"}}}}}}}'
            ]
        })
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            result = await service.get_on_demand_prices_batch(
                ["t3.micro", "t3.small"],
                "us-east-1",
                concurrency=1,
                return_metrics=True
            )

            # Should return tuple of (results, metrics)
            assert isinstance(result, tuple)
            assert len(result) == 2

            results, metrics = result
            assert isinstance(results, dict)
            assert "t3.micro" in results
            assert "t3.small" in results

            # Check metrics
            from src.services.async_pricing_service import PricingMetrics
            assert isinstance(metrics, PricingMetrics)
            assert metrics.total_requests == 2
            assert metrics.end_time is not None

    @pytest.mark.asyncio
    async def test_batch_does_not_return_metrics_by_default(self, mock_async_client, mock_cache, mock_settings):
        """Test that batch pricing returns only results by default"""
        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={'PriceList': []})
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            result = await service.get_on_demand_prices_batch(
                ["t3.micro"],
                "us-east-1",
                concurrency=1
            )

            # Should return dict, not tuple
            assert isinstance(result, dict)
            assert "t3.micro" in result

    @pytest.mark.asyncio
    async def test_batch_metrics_tracks_cache_hits(self, mock_async_client, mock_settings):
        """Test that batch metrics correctly tracks cache hits"""
        # Cache returns prices for all instances (simulating cache hits)
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=0.0104)  # Always return cached price
        mock_cache.set = Mock()

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            results, metrics = await service.get_on_demand_prices_batch(
                ["t3.micro", "t3.small", "t3.medium"],
                "us-east-1",
                concurrency=1,
                return_metrics=True
            )

            # All 3 should be cache hits
            assert metrics.cache_hits == 3
            assert metrics.api_calls == 0
            assert metrics.cache_hit_rate == 100.0

    @pytest.mark.asyncio
    async def test_batch_metrics_tracks_api_calls(self, mock_async_client, mock_settings):
        """Test that batch metrics correctly tracks API calls"""
        mock_cache = Mock()
        mock_cache.get = Mock(return_value=None)  # No cache hits
        mock_cache.set = Mock()

        mock_pricing = AsyncMock()
        mock_pricing.get_products = AsyncMock(return_value={
            'PriceList': [
                '{"product":{"attributes":{"location":"US East (N. Virginia)"}},"terms":{"OnDemand":{"term1":{"priceDimensions":{"dim1":{"unit":"Hrs","pricePerUnit":{"USD":"0.0104"}}}}}}}'
            ]
        })
        mock_pricing.__aenter__ = AsyncMock(return_value=mock_pricing)
        mock_pricing.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.get_pricing_client = Mock(return_value=mock_pricing)

        with patch('src.services.async_pricing_service.get_pricing_cache', return_value=mock_cache):
            service = AsyncPricingService(mock_async_client, use_cache=True, settings=mock_settings)

            results, metrics = await service.get_on_demand_prices_batch(
                ["t3.micro", "t3.small"],
                "us-east-1",
                concurrency=1,
                return_metrics=True
            )

            # All should be API calls (no cache hits)
            assert metrics.cache_hits == 0
            assert metrics.api_calls == 2
            assert metrics.successful_fetches == 2
