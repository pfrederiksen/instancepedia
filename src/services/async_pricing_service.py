"""Async EC2 pricing service using aioboto3"""

import asyncio
import json
import logging
import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable
from decimal import Decimal
from botocore.exceptions import ClientError, BotoCoreError

from src.services.async_aws_client import AsyncAWSClient
from src.services.pricing_service import SpotPriceHistory
from src.debug import DebugLog
from src.cache import get_pricing_cache
from src.config.settings import Settings
from src.models.region_mapping import get_pricing_region

logger = logging.getLogger("instancepedia")

# Callback type definitions for better IDE support and type safety
CacheHitCallback = Callable[[], None]
PriceCallback = Callable[[str, float | None], None]
ProgressCallback = Callable[[int, int], None]


@dataclass
class PricingMetrics:
    """Tracks pricing fetch performance metrics.

    Used to collect and report statistics about pricing operations
    for both user display and debugging.
    """
    total_requests: int = 0
    cache_hits: int = 0
    api_calls: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100

    @property
    def success_rate(self) -> float:
        """Calculate overall success percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_fetches / self.total_requests) * 100

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def requests_per_second(self) -> float:
        """Calculate throughput in requests per second."""
        elapsed = self.elapsed_time
        if elapsed <= 0:
            return 0.0
        return self.total_requests / elapsed

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits += 1
        self.total_requests += 1
        self.successful_fetches += 1

    def record_api_call(self, success: bool) -> None:
        """Record an API call result."""
        self.api_calls += 1
        self.total_requests += 1
        if success:
            self.successful_fetches += 1
        else:
            self.failed_fetches += 1

    def finish(self) -> None:
        """Mark the metrics collection as complete."""
        self.end_time = time.time()

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "api_calls": self.api_calls,
            "successful_fetches": self.successful_fetches,
            "failed_fetches": self.failed_fetches,
            "cache_hit_rate": round(self.cache_hit_rate, 1),
            "success_rate": round(self.success_rate, 1),
            "elapsed_time": round(self.elapsed_time, 2),
            "requests_per_second": round(self.requests_per_second, 1),
        }

    def summary(self) -> str:
        """Get a human-readable summary of metrics."""
        return (
            f"Pricing: {self.successful_fetches}/{self.total_requests} "
            f"({self.success_rate:.0f}% success, {self.cache_hit_rate:.0f}% cached) "
            f"in {self.elapsed_time:.1f}s"
        )


class AsyncPricingService:
    """Async service for fetching EC2 instance pricing"""

    def __init__(self, aws_client: AsyncAWSClient, use_cache: bool = True, settings: Settings | None = None):
        """
        Initialize async pricing service

        Args:
            aws_client: Async AWS client wrapper
            use_cache: Whether to use pricing cache (default: True)
            settings: Application settings (default: create new Settings instance)
        """
        self.aws_client = aws_client
        self.use_cache = use_cache
        self.cache = get_pricing_cache() if use_cache else None
        self.settings = settings or Settings()

    def _get_pricing_region(self, region: str) -> str:
        """Map AWS region code to Pricing API location name"""
        return get_pricing_region(region)

    def _build_ec2_filters(self, instance_type: str, pricing_region: str) -> list[Dict]:
        """Build common EC2 pricing filters for Pricing API queries"""
        return [
            {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonEC2'},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': pricing_region},
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
            {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
            {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
            {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
        ]

    async def get_on_demand_price(
        self,
        instance_type: str,
        region: str,
        max_retries: int = 3,
        cache_hit_callback: CacheHitCallback | None = None
    ) -> float | None:
        """
        Get on-demand price for an instance type in a region

        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            max_retries: Maximum number of retries for rate limiting
            cache_hit_callback: Optional callback() called when cache hit occurs

        Returns:
            Price per hour in USD, or None if not available
        """
        # Check cache first
        if self.cache:
            cached_price = self.cache.get(region, instance_type, 'on_demand')
            if cached_price is not None:
                logger.debug(f"Using cached on-demand price for {instance_type}: ${cached_price}/hr")
                # Notify callback that we had a cache hit
                if cache_hit_callback:
                    cache_hit_callback()
                return cached_price

        pricing_region = self._get_pricing_region(region)
        if not pricing_region:
            # Cache the None result
            if self.cache:
                self.cache.set(region, instance_type, 'on_demand', None)
            return None

        # Cache miss - fetch from AWS
        filters = self._build_ec2_filters(instance_type, pricing_region)

        for attempt in range(max_retries + 1):
            try:
                async with self.aws_client.get_pricing_client() as pricing:
                    response = await pricing.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=filters,
                        MaxResults=10
                    )

                    if not response.get('PriceList'):
                        # Cache the None result
                        if self.cache:
                            self.cache.set(region, instance_type, 'on_demand', None)
                        return None

                    # Parse results and find best price
                    best_price = None
                    for price_list_item in response['PriceList']:
                        price_data = json.loads(price_list_item)
                        price = self._extract_price(price_data, pricing_region)
                        if price is not None and (best_price is None or price < best_price):
                            best_price = price

                    if best_price is not None and best_price > 0:
                        DebugLog.log(f"Found price for {instance_type}: ${best_price}/hr")
                        # Cache the result
                        if self.cache:
                            self.cache.set(region, instance_type, 'on_demand', best_price)
                        return best_price

                    # Cache the None result
                    if self.cache:
                        self.cache.set(region, instance_type, 'on_demand', None)
                    return None

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code in ("Throttling", "ThrottlingException") or "429" in str(e):
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        DebugLog.log(f"Rate limited for {instance_type}, retrying in {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                        continue
                DebugLog.log(f"Pricing API error for {instance_type}: {error_code}")
                return None
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                DebugLog.log(f"Error fetching price for {instance_type}: {e}")
                return None

        return None

    def _extract_price(self, price_data: dict, pricing_region: str) -> float | None:
        """Extract USD price from pricing API response"""
        try:
            # Verify location matches
            attributes = price_data.get('product', {}).get('attributes', {})
            location = attributes.get('location', '')
            if pricing_region.lower() not in location.lower():
                return None

            terms = price_data.get('terms', {})
            on_demand = terms.get('OnDemand', {})
            if not on_demand:
                return None

            term_key = list(on_demand.keys())[0]
            price_dimensions = on_demand[term_key].get('priceDimensions', {})

            for dimension_data in price_dimensions.values():
                unit = dimension_data.get('unit', '')
                price_per_unit = dimension_data.get('pricePerUnit', {})
                usd_price = price_per_unit.get('USD')

                if usd_price and ('Hrs' in unit or 'Hr' in unit or unit == ''):
                    price = float(Decimal(usd_price))
                    if price > 0:
                        return price

            return None
        except Exception:
            return None

    async def get_spot_price(self, instance_type: str, region: str) -> float | None:
        """
        Get current spot price for an instance type in a region

        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')

        Returns:
            Current spot price per hour in USD, or None if not available
        """
        # Check cache first
        if self.cache:
            cached_price = self.cache.get(region, instance_type, 'spot')
            if cached_price is not None:
                logger.debug(f"Using cached spot price for {instance_type}: ${cached_price}/hr")
                return cached_price

        # Cache miss - fetch from AWS
        try:
            async with self.aws_client.get_ec2_client() as ec2:
                response = await ec2.describe_spot_price_history(
                    InstanceTypes=[instance_type],
                    ProductDescriptions=['Linux/UNIX'],
                    MaxResults=1
                )

                if not response.get('SpotPriceHistory'):
                    # Cache the None result
                    if self.cache:
                        self.cache.set(region, instance_type, 'spot', None)
                    return None

                latest = response['SpotPriceHistory'][0]
                spot_price = float(latest['SpotPrice'])

                # Cache the result
                if self.cache:
                    self.cache.set(region, instance_type, 'spot', spot_price)

                return spot_price

        except Exception:
            # Cache the None result
            if self.cache:
                self.cache.set(region, instance_type, 'spot', None)
            return None

    async def get_spot_price_history(
        self,
        instance_type: str,
        region: str,
        days: int = 30
    ) -> SpotPriceHistory | None:
        """
        Get historical spot prices for an instance type with statistics

        Args:
            instance_type: EC2 instance type (e.g., "t3.micro")
            region: AWS region code
            days: Number of days of history to fetch (default: 30)

        Returns:
            SpotPriceHistory object with statistics, or None if unavailable
        """
        try:
            # Calculate start time
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            # Fetch historical spot prices
            async with self.aws_client.get_ec2_client() as ec2:
                response = await ec2.describe_spot_price_history(
                    InstanceTypes=[instance_type],
                    ProductDescriptions=['Linux/UNIX'],
                    StartTime=start_time
                )

            if not response.get('SpotPriceHistory'):
                return None

            # Parse price history
            price_points = []
            for entry in response['SpotPriceHistory']:
                timestamp = entry['Timestamp']
                price = float(entry['SpotPrice'])
                price_points.append((timestamp, price))

            # Sort by timestamp (oldest first)
            price_points.sort(key=lambda x: x[0])

            if not price_points:
                return None

            # Extract prices for statistics
            prices = [price for _, price in price_points]

            # Calculate statistics
            current_price = prices[-1] if prices else None
            min_price = min(prices) if prices else None
            max_price = max(prices) if prices else None
            avg_price = statistics.mean(prices) if prices else None
            median_price = statistics.median(prices) if prices else None
            std_dev = statistics.stdev(prices) if len(prices) > 1 else None

            return SpotPriceHistory(
                instance_type=instance_type,
                region=region,
                days=days,
                current_price=current_price,
                min_price=min_price,
                max_price=max_price,
                avg_price=avg_price,
                median_price=median_price,
                std_dev=std_dev,
                price_points=price_points
            )

        except (ClientError, BotoCoreError, Exception) as e:
            logger.debug(f"Error fetching spot price history for {instance_type}: {e}")
            return None

    async def get_savings_plan_price(
        self,
        instance_type: str,
        region: str,
        lease_length: str = "1yr",
        max_retries: int = 3,
        cache_hit_callback: CacheHitCallback | None = None
    ) -> float | None:
        """
        Get Savings Plan price for an instance type (Reserved pricing with No Upfront)

        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            lease_length: "1yr" or "3yr"
            max_retries: Maximum number of retries for rate limiting
            cache_hit_callback: Optional callback() called when cache hit occurs

        Returns:
            Savings Plan price per hour in USD, or None if not available
        """
        # Check cache first
        cache_key = f"savings_{lease_length}"
        if self.cache:
            cached_price = self.cache.get(region, instance_type, cache_key)
            if cached_price is not None:
                logger.debug(f"Using cached {lease_length} savings plan price for {instance_type}: ${cached_price}/hr")
                if cache_hit_callback:
                    cache_hit_callback()
                return cached_price

        # Map lease length to AWS API format
        lease_map = {
            "1yr": "1yr",
            "3yr": "3yr"
        }

        api_lease = lease_map.get(lease_length)
        if not api_lease:
            logger.error(f"Invalid lease length: {lease_length}")
            return None

        pricing_region = self._get_pricing_region(region)
        if not pricing_region:
            if self.cache:
                self.cache.set(region, instance_type, cache_key, None)
            return None

        # Cache miss - fetch from AWS
        filters = self._build_ec2_filters(instance_type, pricing_region)

        for attempt in range(max_retries + 1):
            try:
                DebugLog.log(f"Querying Pricing API for {lease_length} savings plan: {instance_type} in {pricing_region}")
                async with self.aws_client.get_pricing_client() as pricing:
                    response = await pricing.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=filters,
                        MaxResults=10
                    )

                if not response.get('PriceList'):
                    DebugLog.log(f"No PriceList returned for savings plan {instance_type} in {pricing_region}")
                    if self.cache:
                        self.cache.set(region, instance_type, cache_key, None)
                    return None

                # Parse results and find Reserved terms
                best_price = None

                for price_list_item in response['PriceList']:
                    price_data = json.loads(price_list_item)

                    # Look for Reserved terms
                    terms = price_data.get('terms', {})
                    reserved = terms.get('Reserved', {})

                    if not reserved:
                        continue

                    # Iterate through all reserved offerings
                    for term_key, term_data in reserved.items():
                        term_attributes = term_data.get('termAttributes', {})
                        lease_contract_length = term_attributes.get('LeaseContractLength', '')
                        purchase_option = term_attributes.get('PurchaseOption', '')

                        # Match our desired lease length and "No Upfront" option
                        if lease_contract_length == api_lease and purchase_option == 'No Upfront':
                            price_dimensions = term_data.get('priceDimensions', {})

                            for dimension_key, dimension_data in price_dimensions.items():
                                unit = dimension_data.get('unit', '')
                                price_per_unit = dimension_data.get('pricePerUnit', {})
                                usd_price = price_per_unit.get('USD')

                                # Look for hourly pricing
                                if ('Hrs' in unit or 'Hr' in unit) and usd_price:
                                    try:
                                        temp_price = float(Decimal(usd_price))
                                        if temp_price > 0 and (best_price is None or temp_price < best_price):
                                            best_price = temp_price
                                    except (ValueError, TypeError) as e:
                                        DebugLog.log(f"Error parsing savings plan price '{usd_price}': {e}")
                                        continue

                if best_price is not None:
                    DebugLog.log(f"Found {lease_length} savings plan price for {instance_type}: ${best_price}/hr")
                    if self.cache:
                        self.cache.set(region, instance_type, cache_key, best_price)
                    return best_price

                DebugLog.log(f"No {lease_length} savings plan pricing found for {instance_type}")
                if self.cache:
                    self.cache.set(region, instance_type, cache_key, None)
                return None

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")

                # Handle rate limiting with retry
                if error_code == "Throttling" or error_code == "ThrottlingException":
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        DebugLog.log(f"Rate limited for savings plan {instance_type}, retrying in {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        DebugLog.log(f"Rate limited for savings plan {instance_type} after {max_retries} retries")
                        return None

                DebugLog.log(f"Pricing API error for savings plan {instance_type}: {error_code}")
                return None
            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    DebugLog.log(f"Exception for savings plan {instance_type}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                DebugLog.log(f"Pricing API exception for savings plan {instance_type}: {str(e)}")
                return None

        # All retries failed
        if self.cache:
            self.cache.set(region, instance_type, cache_key, None)
        return None

    async def get_reserved_instance_price(
        self,
        instance_type: str,
        region: str,
        lease_length: str = "1yr",
        payment_option: str = "no_upfront",
        max_retries: int = 3,
        cache_hit_callback: CacheHitCallback | None = None
    ) -> float | None:
        """
        Get Reserved Instance price for an instance type (Standard RIs only)

        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            lease_length: "1yr" or "3yr"
            payment_option: "no_upfront", "partial_upfront", or "all_upfront"
            max_retries: Maximum number of retries for rate limiting
            cache_hit_callback: Optional callback() called when cache hit occurs

        Returns:
            RI effective hourly rate in USD, or None if not available
        """
        # Check cache first
        cache_key = f"ri_{lease_length}_{payment_option}"
        if self.cache:
            cached_price = self.cache.get(region, instance_type, cache_key)
            if cached_price is not None:
                logger.debug(f"Using cached {lease_length} RI {payment_option} price for {instance_type}: ${cached_price}/hr")
                if cache_hit_callback:
                    cache_hit_callback()
                return cached_price

        # Map lease length and payment option to AWS API format
        lease_map = {
            "1yr": "1yr",
            "3yr": "3yr"
        }
        payment_map = {
            "no_upfront": "No Upfront",
            "partial_upfront": "Partial Upfront",
            "all_upfront": "All Upfront"
        }

        api_lease = lease_map.get(lease_length)
        api_payment = payment_map.get(payment_option)

        if not api_lease:
            logger.error(f"Invalid lease length: {lease_length}")
            return None
        if not api_payment:
            logger.error(f"Invalid payment option: {payment_option}")
            return None

        pricing_region = self._get_pricing_region(region)
        if not pricing_region:
            if self.cache:
                self.cache.set(region, instance_type, cache_key, None)
            return None

        # Cache miss - fetch from AWS
        filters = self._build_ec2_filters(instance_type, pricing_region)

        for attempt in range(max_retries + 1):
            try:
                DebugLog.log(f"Querying Pricing API for {lease_length} RI {payment_option}: {instance_type} in {pricing_region}")
                async with self.aws_client.get_pricing_client() as pricing:
                    response = await pricing.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=filters,
                        MaxResults=10
                    )

                if not response.get('PriceList'):
                    DebugLog.log(f"No PriceList returned for RI {instance_type} in {pricing_region}")
                    if self.cache:
                        self.cache.set(region, instance_type, cache_key, None)
                    return None

                # Parse results and find Reserved terms with Standard offering class
                best_price = None

                for price_list_item in response['PriceList']:
                    price_data = json.loads(price_list_item)

                    # Look for Reserved terms
                    terms = price_data.get('terms', {})
                    reserved = terms.get('Reserved', {})

                    if not reserved:
                        continue

                    # Iterate through all reserved offerings
                    for term_key, term_data in reserved.items():
                        term_attributes = term_data.get('termAttributes', {})
                        lease_contract_length = term_attributes.get('LeaseContractLength', '')
                        purchase_option = term_attributes.get('PurchaseOption', '')
                        offering_class = term_attributes.get('OfferingClass', '')

                        # Match our desired lease length, payment option, and Standard offering class
                        if (lease_contract_length == api_lease and
                            purchase_option == api_payment and
                            offering_class == 'standard'):

                            price_dimensions = term_data.get('priceDimensions', {})

                            for dimension_key, dimension_data in price_dimensions.items():
                                unit = dimension_data.get('unit', '')
                                price_per_unit = dimension_data.get('pricePerUnit', {})
                                usd_price = price_per_unit.get('USD')

                                # Look for hourly pricing
                                if ('Hrs' in unit or 'Hr' in unit) and usd_price:
                                    try:
                                        temp_price = float(Decimal(usd_price))
                                        if temp_price > 0 and (best_price is None or temp_price < best_price):
                                            best_price = temp_price
                                    except (ValueError, TypeError) as e:
                                        DebugLog.log(f"Error parsing RI price '{usd_price}': {e}")
                                        continue

                if best_price is not None:
                    DebugLog.log(f"Found {lease_length} RI {payment_option} price for {instance_type}: ${best_price}/hr")
                    if self.cache:
                        self.cache.set(region, instance_type, cache_key, best_price)
                    return best_price

                DebugLog.log(f"No {lease_length} RI {payment_option} pricing found for {instance_type}")
                if self.cache:
                    self.cache.set(region, instance_type, cache_key, None)
                return None

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")

                # Handle rate limiting with retry
                if error_code == "Throttling" or error_code == "ThrottlingException":
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        DebugLog.log(f"Rate limited for RI {instance_type}, retrying in {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        DebugLog.log(f"Rate limited for RI {instance_type} after {max_retries} retries")
                        return None

                DebugLog.log(f"Pricing API error for RI {instance_type}: {error_code}")
                return None
            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    DebugLog.log(f"Exception for RI {instance_type}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                DebugLog.log(f"Pricing API exception for RI {instance_type}: {str(e)}")
                return None

        # All retries failed
        if self.cache:
            self.cache.set(region, instance_type, cache_key, None)
        return None

    async def get_on_demand_prices_batch(
        self,
        instance_types: list[str],
        region: str,
        concurrency: int = 10,
        progress_callback: ProgressCallback | None = None,
        price_callback: PriceCallback | None = None,
        cache_hit_callback: CacheHitCallback | None = None,
        return_metrics: bool = False
    ) -> dict[str, float | None]:
        """
        Get on-demand prices for multiple instance types concurrently

        Args:
            instance_types: List of EC2 instance types
            region: AWS region code
            concurrency: Maximum concurrent requests (default 10)
            progress_callback: Optional callback(completed, total) for progress updates
            price_callback: Optional callback(instance_type, price) called when each price is fetched
            cache_hit_callback: Optional callback() called when a cache hit occurs
            return_metrics: If True, returns (results, metrics) tuple instead of just results

        Returns:
            Dictionary mapping instance_type to price (or None)
            If return_metrics=True, returns tuple (results, PricingMetrics)
        """
        metrics = PricingMetrics()
        logger.debug(f"Starting batch pricing fetch: {len(instance_types)} instances, concurrency={concurrency}, delay={self.settings.pricing_request_delay_ms}ms")

        semaphore = asyncio.Semaphore(concurrency)
        results = {}
        completed = 0
        total = len(instance_types)

        def metrics_cache_hit_callback():
            """Internal callback to track cache hits in metrics"""
            metrics.record_cache_hit()
            # Also call user's callback if provided
            if cache_hit_callback:
                cache_hit_callback()

        async def fetch_with_semaphore(inst_type: str):
            nonlocal completed
            async with semaphore:
                # Small delay to avoid rate limiting (configurable via settings)
                delay_seconds = self.settings.pricing_request_delay_ms / 1000.0
                await asyncio.sleep(delay_seconds)

                # Check if this will be a cache hit (for tracking API calls)
                is_cache_hit = False
                if self.cache:
                    cached_price = self.cache.get(region, inst_type, 'on_demand')
                    is_cache_hit = cached_price is not None

                price = await self.get_on_demand_price(
                    inst_type, region,
                    cache_hit_callback=metrics_cache_hit_callback if is_cache_hit else None
                )

                # Track API call if not a cache hit
                if not is_cache_hit:
                    metrics.record_api_call(success=price is not None)

                results[inst_type] = price
                completed += 1
                # Call price callback first so instance is updated before progress callback
                if price_callback:
                    price_callback(inst_type, price)
                if progress_callback:
                    progress_callback(completed, total)
                return price

        # Create tasks for all instance types
        tasks = [fetch_with_semaphore(inst_type) for inst_type in instance_types]

        # Run all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Finalize metrics
        metrics.finish()
        logger.debug(metrics.summary())
        if metrics.elapsed_time > 0:
            logger.debug(f"Throughput: {metrics.requests_per_second:.1f} requests/second")

        if return_metrics:
            return results, metrics
        return results

    async def get_spot_prices_batch(
        self,
        instance_types: list[str],
        region: str
    ) -> dict[str, float | None]:
        """
        Get spot prices for multiple instance types (uses EC2 batch API)

        Args:
            instance_types: List of EC2 instance types
            region: AWS region code

        Returns:
            Dictionary mapping instance_type to spot price (or None)
        """
        result = {}
        timestamps = {}

        try:
            async with self.aws_client.get_ec2_client() as ec2:
                # Process in chunks (EC2 API limit is ~50 instance types, configurable)
                chunk_size = self.settings.spot_batch_size
                for i in range(0, len(instance_types), chunk_size):
                    chunk = instance_types[i:i + chunk_size]

                    next_token = None
                    while True:
                        request_params = {
                            'InstanceTypes': chunk,
                            'ProductDescriptions': ['Linux/UNIX'],
                            'MaxResults': 1000
                        }
                        if next_token:
                            request_params['NextToken'] = next_token

                        response = await ec2.describe_spot_price_history(**request_params)

                        for price_data in response.get('SpotPriceHistory', []):
                            inst_type = price_data['InstanceType']
                            timestamp = price_data['Timestamp']

                            if inst_type not in result or timestamp > timestamps.get(inst_type, timestamp):
                                result[inst_type] = float(price_data['SpotPrice'])
                                timestamps[inst_type] = timestamp

                        next_token = response.get('NextToken')
                        if not next_token:
                            break

        except Exception as e:
            DebugLog.log(f"Error in get_spot_prices_batch: {e}")

        # Ensure all instance types are in result
        for inst_type in instance_types:
            if inst_type not in result:
                result[inst_type] = None

        return result
