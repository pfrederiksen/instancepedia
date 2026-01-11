"""EC2 pricing service"""

from botocore.exceptions import ClientError, BotoCoreError
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import json
import time
import logging
import statistics

from src.services.aws_client import AWSClient
from src.debug import DebugLog
from src.cache import get_pricing_cache
from src.config.settings import Settings
from src.models.region_mapping import get_pricing_region

logger = logging.getLogger("instancepedia")


@dataclass
class SpotPriceHistory:
    """Spot price history data with statistics"""
    instance_type: str
    region: str
    days: int
    current_price: float | None
    min_price: float | None
    max_price: float | None
    avg_price: float | None
    median_price: float | None
    std_dev: float | None
    price_points: list[tuple[datetime, float]]  # List of (timestamp, price) tuples

    @property
    def volatility_percentage(self) -> float | None:
        """Calculate volatility as percentage of average price"""
        if self.avg_price and self.std_dev and self.avg_price > 0:
            return (self.std_dev / self.avg_price) * 100
        return None

    @property
    def price_range(self) -> float | None:
        """Calculate price range (max - min)"""
        if self.min_price is not None and self.max_price is not None:
            return self.max_price - self.min_price
        return None

    @property
    def savings_vs_current(self) -> float | None:
        """Calculate potential savings if buying at min vs current"""
        if self.current_price and self.min_price and self.current_price > 0:
            return ((self.current_price - self.min_price) / self.current_price) * 100
        return None


class PricingService:
    """Service for fetching EC2 instance pricing"""

    def __init__(self, aws_client: AWSClient, use_cache: bool = True, settings: Settings | None = None):
        """
        Initialize pricing service

        Args:
            aws_client: AWS client wrapper
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

    def _parse_hourly_price_from_dimensions(self, price_dimensions: Dict) -> float | None:
        """
        Extract hourly USD price from price dimensions.

        Args:
            price_dimensions: AWS Pricing API priceDimensions dict

        Returns:
            Hourly price in USD, or None if not found
        """
        for dimension_key, dimension_data in price_dimensions.items():
            unit = dimension_data.get('unit', '')
            price_per_unit = dimension_data.get('pricePerUnit', {})
            usd_price = price_per_unit.get('USD')
            jpy_price = price_per_unit.get('JPY')

            # Convert JPY to USD if needed (approximate rate)
            if jpy_price and not usd_price:
                try:
                    jpy_value = float(Decimal(jpy_price))
                    if jpy_value > 0:
                        usd_price = str(jpy_value / 150.0)  # Approximate exchange rate
                except (ValueError, TypeError):
                    continue

            # Look for hourly pricing
            if ('Hrs' in unit or 'Hr' in unit or unit == '') and usd_price:
                try:
                    price = float(Decimal(usd_price))
                    if price > 0:
                        return price
                except (ValueError, TypeError):
                    continue
        return None

    def _handle_throttling(self, attempt: int, max_retries: int, error: Exception) -> bool:
        """
        Handle API throttling with exponential backoff.

        Returns:
            True if should retry, False if should give up
        """
        error_code = getattr(error, 'response', {}).get('Error', {}).get('Code', '')
        if error_code == 'ThrottlingException' and attempt < max_retries:
            wait_time = min(2 ** attempt, 30)  # Exponential backoff, max 30 seconds
            DebugLog.log(f"Rate limited, waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait_time)
            return True
        return False

    def get_on_demand_price(self, instance_type: str, region: str, max_retries: int = 3) -> float | None:
        """
        Get on-demand price for an instance type in a region

        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            max_retries: Maximum number of retries for rate limiting

        Returns:
            Price per hour in USD, or None if not available
        """
        # Check cache first
        if self.cache:
            cached_price = self.cache.get(region, instance_type, 'on_demand')
            if cached_price is not None:
                logger.debug(f"Using cached on-demand price for {instance_type}: ${cached_price}/hr")
                return cached_price

        # Cache miss - fetch from AWS
        pricing_region = self._get_pricing_region(region)
        filters = self._build_ec2_filters(instance_type, pricing_region)

        for attempt in range(max_retries + 1):
            try:
                DebugLog.log(f"Querying Pricing API for {instance_type} in {pricing_region} (region code: {region})")
                response = self.aws_client.pricing_client.get_products(
                    ServiceCode='AmazonEC2',
                    Filters=filters,
                    MaxResults=10  # Get more results to find the right one
                )
                
                if not response.get('PriceList'):
                    DebugLog.log(f"No PriceList returned for {instance_type} in {pricing_region}")
                    return None
                
                DebugLog.log(f"Got PriceList with {len(response['PriceList'])} items for {instance_type}")
                
                # Parse all results and find the best match
                best_price = None
                best_price_data = None
                
                for price_list_item in response['PriceList']:
                    price_data = json.loads(price_list_item)
                    
                    # Verify the location matches (sometimes multiple regions can match)
                    attributes = price_data.get('product', {}).get('attributes', {})
                    location = attributes.get('location', '')
                    
                    # Check if this is the right location
                    if pricing_region.lower() not in location.lower() and location.lower() not in pricing_region.lower():
                        # Skip if location doesn't match (but allow if it's close)
                        if 'osaka' not in location.lower() or 'osaka' not in pricing_region.lower():
                            continue
                    
                    # Try to extract price from this result
                    terms = price_data.get('terms', {})
                    on_demand = terms.get('OnDemand', {})
                    
                    if on_demand:
                        # Get first term's price
                        term_key = list(on_demand.keys())[0]
                        price_dimensions = on_demand[term_key].get('priceDimensions', {})
                        
                        for dimension_key, dimension_data in price_dimensions.items():
                            unit = dimension_data.get('unit', '')
                            price_per_unit = dimension_data.get('pricePerUnit', {})
                            temp_usd_price = price_per_unit.get('USD')
                            temp_jpy_price = price_per_unit.get('JPY')
                            
                            # Convert JPY to USD if needed (approximate rate)
                            if temp_jpy_price and not temp_usd_price:
                                jpy_to_usd_rate = 150.0
                                try:
                                    jpy_value = float(Decimal(temp_jpy_price))
                                    if jpy_value > 0:  # Only convert if JPY price is valid
                                        temp_usd_price = str(jpy_value / jpy_to_usd_rate)
                                except (ValueError, TypeError):
                                    continue
                            
                            # Only process if we have a valid USD price (after potential conversion)
                            if temp_usd_price and temp_usd_price.strip() and temp_usd_price != '0' and ('Hrs' in unit or 'Hr' in unit or unit == ''):
                                try:
                                    temp_price = float(Decimal(temp_usd_price))
                                    # Only use valid prices (greater than 0)
                                    if temp_price > 0 and (best_price is None or temp_price < best_price):
                                        # Use the lowest price (should be the standard on-demand)
                                        best_price = temp_price
                                        best_price_data = price_data
                                except (ValueError, TypeError) as e:
                                    DebugLog.log(f"Error parsing price '{temp_usd_price}' for {instance_type}: {e}")
                                    continue
                
                # If we found a best price in the loop, use it directly
                if best_price is not None and best_price > 0:
                    DebugLog.log(f"Found price for {instance_type}: ${best_price}/hr")
                    # Cache the result
                    if self.cache:
                        self.cache.set(region, instance_type, 'on_demand', best_price)
                    return best_price
                
                # Otherwise, fall back to parsing the first result
                price_data = json.loads(response['PriceList'][0])
                DebugLog.log(f"Warning: Using first result for {instance_type}, may not be optimal")
                
                # Navigate the complex pricing structure
                terms = price_data.get('terms', {})
                if not terms:
                    DebugLog.log(f"No 'terms' in price data for {instance_type}")
                    return None
                    
                on_demand = terms.get('OnDemand', {})
                
                if not on_demand:
                    DebugLog.log(f"No 'OnDemand' terms for {instance_type}")
                    return None
                
                # Get the first (and usually only) term
                # There can be multiple terms, but we want the on-demand one
                term_key = list(on_demand.keys())[0]
                price_dimensions = on_demand[term_key].get('priceDimensions', {})
                
                if not price_dimensions:
                    DebugLog.log(f"No 'priceDimensions' for {instance_type}")
                    return None
                
                # Find the price dimension with unit "Hrs" (hourly pricing)
                # Sometimes there are multiple dimensions, we want the per-hour one
                # Check for USD first, then JPY (Japanese Yen) and convert if needed
                usd_price = None
                currency_used = None
                
                for dimension_key, dimension_data in price_dimensions.items():
                    unit = dimension_data.get('unit', '')
                    price_per_unit = dimension_data.get('pricePerUnit', {})
                    
                    # Prefer USD, but also check for JPY
                    temp_usd_price = price_per_unit.get('USD')
                    temp_jpy_price = price_per_unit.get('JPY')
                    
                    # Prefer "Hrs" unit for hourly pricing
                    if ('Hrs' in unit or 'Hr' in unit or unit == '') and (temp_usd_price or temp_jpy_price):
                        if temp_usd_price:
                            usd_price = temp_usd_price
                            currency_used = 'USD'
                            break
                        elif temp_jpy_price:
                            # Convert JPY to USD (approximate rate, ~150 JPY = 1 USD)
                            # Note: This is an approximation; for accurate conversion, use a currency API
                            jpy_to_usd_rate = 150.0  # Approximate exchange rate
                            try:
                                jpy_value = float(Decimal(temp_jpy_price))
                                usd_price = str(jpy_value / jpy_to_usd_rate)
                                currency_used = 'JPY'
                                DebugLog.log(f"Found JPY price {temp_jpy_price} for {instance_type}, converting to USD at rate {jpy_to_usd_rate}")
                                break
                            except (ValueError, TypeError):
                                continue
                
                # If no "Hrs" unit found, use the first available price (USD or JPY)
                if not usd_price:
                    dimension_key = list(price_dimensions.keys())[0]
                    price_per_unit = price_dimensions[dimension_key].get('pricePerUnit', {})
                    usd_price = price_per_unit.get('USD')
                    if usd_price:
                        currency_used = 'USD'
                    else:
                        jpy_price = price_per_unit.get('JPY')
                        if jpy_price:
                            jpy_to_usd_rate = 150.0
                            try:
                                jpy_value = float(Decimal(jpy_price))
                                usd_price = str(jpy_value / jpy_to_usd_rate)
                                currency_used = 'JPY'
                                DebugLog.log(f"Found JPY price {jpy_price} for {instance_type}, converting to USD")
                            except (ValueError, TypeError):
                                pass
                
                if usd_price:
                    try:
                        price = float(Decimal(usd_price))
                        # Basic sanity check: prices should be positive and reasonable
                        # EC2 prices typically range from $0.005/hr to $100+/hr
                        if price <= 0:
                            DebugLog.log(f"Warning: Invalid price (<= 0) for {instance_type}: {usd_price} - skipping")
                            return None
                        if price > 1000:
                            DebugLog.log(f"Warning: Unusual price for {instance_type}: ${price}/hr (from {currency_used}) - may be incorrect")
                        if currency_used == 'JPY':
                            DebugLog.log(f"Found price for {instance_type}: ${price:.4f}/hr (converted from JPY)")
                        else:
                            DebugLog.log(f"Found price for {instance_type}: ${price}/hr")
                        # Cache the result
                        if self.cache:
                            self.cache.set(region, instance_type, 'on_demand', price)
                        return price
                    except (ValueError, TypeError) as e:
                        DebugLog.log(f"Error parsing price '{usd_price}' for {instance_type}: {e}")
                        return None
                
                # Log what currencies were available for debugging
                available_currencies = []
                for dimension_key, dimension_data in price_dimensions.items():
                    price_per_unit = dimension_data.get('pricePerUnit', {})
                    available_currencies.extend(price_per_unit.keys())
                DebugLog.log(f"No USD or JPY price found for {instance_type}. Available currencies: {set(available_currencies)}")
                return None
                
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))
                
                # Handle rate limiting with retry
                if error_code == "Throttling" or error_code == "ThrottlingException" or "429" in str(e):
                    if attempt < max_retries:
                        # Exponential backoff with jitter: 2s, 4s, 8s, etc.
                        wait_time = (2 ** attempt) + (attempt * 0.5)  # Add some jitter
                        DebugLog.log(f"Rate limited for {instance_type}, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries + 1})")
                        time.sleep(wait_time)
                        continue  # Retry
                    else:
                        DebugLog.log(f"Rate limited for {instance_type} after {max_retries} retries, giving up")
                        return None
                
                DebugLog.log(f"Pricing API ClientError for {instance_type} in {region}: {error_code} - {error_message}")
                # Don't raise for pricing errors, just return None
                if error_code == "AccessDeniedException":
                    DebugLog.log(f"Access denied to Pricing API. Check IAM permissions.")
                    raise Exception(f"AWS Pricing API error ({error_code}): {error_message}")
                return None
            except BotoCoreError as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    DebugLog.log(f"BotoCoreError for {instance_type}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                DebugLog.log(f"Pricing API BotoCoreError for {instance_type} in {region}: {str(e)}")
                return None
            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    DebugLog.log(f"Exception for {instance_type}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                DebugLog.log(f"Pricing API Exception for {instance_type} in {region}: {str(e)}")
                import traceback
                DebugLog.log(f"Traceback: {traceback.format_exc()}")
                return None
        
        # If we get here, all retries failed
        # Cache the None result to avoid repeated failed lookups
        if self.cache:
            self.cache.set(region, instance_type, 'on_demand', None)
        return None

    def get_spot_price(self, instance_type: str, region: str) -> float | None:
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
            response = self.aws_client.ec2_client.describe_spot_price_history(
                InstanceTypes=[instance_type],
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=1
            )

            if not response.get('SpotPriceHistory'):
                # Cache the None result
                if self.cache:
                    self.cache.set(region, instance_type, 'spot', None)
                return None

            # Get the most recent spot price
            latest = response['SpotPriceHistory'][0]
            spot_price = float(latest['SpotPrice'])

            # Cache the result
            if self.cache:
                self.cache.set(region, instance_type, 'spot', spot_price)

            return spot_price

        except ClientError:
            # Cache the None result
            if self.cache:
                self.cache.set(region, instance_type, 'spot', None)
            return None
        except BotoCoreError:
            # Cache the None result
            if self.cache:
                self.cache.set(region, instance_type, 'spot', None)
            return None
        except Exception:
            # Cache the None result
            if self.cache:
                self.cache.set(region, instance_type, 'spot', None)
            return None

    def get_spot_price_history(
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
            response = self.aws_client.ec2_client.describe_spot_price_history(
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

    def get_spot_prices_batch(self, instance_types: list[str], region: str, max_retries: int = 3) -> dict[str, float | None]:
        """
        Get current spot prices for multiple instance types in a region (batch)
        
        Args:
            instance_types: List of EC2 instance types
            region: AWS region code
            max_retries: Maximum number of retries for rate limiting
            
        Returns:
            Dictionary mapping instance_type to spot price (or None)
        """
        result = {}
        timestamps = {}  # Track timestamps separately
        
        try:
            # EC2 API supports querying multiple instance types at once
            # Process in chunks to avoid hitting limits
            chunk_size = 50  # EC2 API limit
            for i in range(0, len(instance_types), chunk_size):
                chunk = instance_types[i:i + chunk_size]
                
                # Retry logic for each chunk
                chunk_success = False
                for attempt in range(max_retries + 1):
                    try:
                        # Paginate through all results using NextToken
                        # describe_spot_price_history returns one result per instance type per AZ,
                        # so we need to fetch all pages to get complete data
                        next_token = None
                        all_price_data = []
                        max_pages = 100  # Safety limit to prevent infinite loops
                        page_count = 0
                        
                        while page_count < max_pages:
                            try:
                                request_params = {
                                    'InstanceTypes': chunk,
                                    'ProductDescriptions': ['Linux/UNIX'],
                                    'MaxResults': 1000  # AWS API max, allows multiple AZs per instance type
                                }
                                if next_token:
                                    request_params['NextToken'] = next_token
                                
                                response = self.aws_client.ec2_client.describe_spot_price_history(**request_params)
                                
                                # Collect all price data from this page
                                page_results = response.get('SpotPriceHistory', [])
                                all_price_data.extend(page_results)
                                page_count += 1
                                
                                DebugLog.log(f"Fetched page {page_count} with {len(page_results)} spot price results for chunk of {len(chunk)} instance types")
                                
                                # Check if there are more pages
                                next_token = response.get('NextToken')
                                if not next_token:
                                    break
                            except Exception as page_error:
                                # If we get an error during pagination, log it but try to use what we have
                                DebugLog.log(f"Error during pagination (page {page_count + 1}): {page_error}")
                                # Break out of pagination loop - we'll process what we have so far
                                break
                        
                        if page_count >= max_pages:
                            DebugLog.log(f"Warning: Hit pagination safety limit ({max_pages} pages) for chunk, may have incomplete data")
                        
                        DebugLog.log(f"Collected {len(all_price_data)} total spot price results for chunk")
                        
                        # Group by instance type, keeping most recent
                        for price_data in all_price_data:
                            inst_type = price_data['InstanceType']
                            timestamp = price_data['Timestamp']
                            
                            # Keep the most recent price for each instance type
                            if inst_type not in result or timestamp > timestamps.get(inst_type, timestamp):
                                result[inst_type] = float(price_data['SpotPrice'])
                                timestamps[inst_type] = timestamp
                        
                        chunk_success = True
                        break  # Success, move to next chunk
                        
                    except ClientError as e:
                        error_code = e.response.get("Error", {}).get("Code", "Unknown")
                        # Handle rate limiting
                        if (error_code == "Throttling" or error_code == "ThrottlingException" or 
                            "429" in str(e) or "RequestLimitExceeded" in error_code):
                            if attempt < max_retries:
                                wait_time = 2 ** attempt
                                DebugLog.log(f"Rate limited for spot price chunk, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                                time.sleep(wait_time)
                                continue  # Retry
                            else:
                                DebugLog.log(f"Rate limited for spot price chunk after {max_retries} retries")
                                # Mark chunk as failed but continue
                                break
                        else:
                            # Other error, don't retry
                            DebugLog.log(f"Error fetching spot prices for chunk: {error_code} - {str(e)}")
                            break
                            
                    except Exception as e:
                        if attempt < max_retries:
                            wait_time = 2 ** attempt
                            DebugLog.log(f"Exception fetching spot prices for chunk, retrying in {wait_time}s")
                            time.sleep(wait_time)
                            continue
                        DebugLog.log(f"Error fetching spot prices for chunk: {e}")
                        break
                
                # If chunk failed, mark all in chunk as None
                if not chunk_success:
                    for inst_type in chunk:
                        if inst_type not in result:
                            result[inst_type] = None
            
            # Ensure all instance types are in result
            for inst_type in instance_types:
                if inst_type not in result:
                    result[inst_type] = None
                    
        except Exception as e:
            DebugLog.log(f"Error in get_spot_prices_batch: {e}")
            # Return None for all
            result = {inst_type: None for inst_type in instance_types}
        
        return result

    def get_savings_plan_price(
        self,
        instance_type: str,
        region: str,
        lease_length: str = "1yr",
        max_retries: int = 3
    ) -> float | None:
        """
        Get Savings Plan price for an instance type (Reserved pricing with No Upfront)

        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            lease_length: "1yr" or "3yr"
            max_retries: Maximum number of retries for rate limiting

        Returns:
            Savings Plan price per hour in USD, or None if not available
        """
        # Check cache first
        cache_key = f"savings_{lease_length}"
        if self.cache:
            cached_price = self.cache.get(region, instance_type, cache_key)
            if cached_price is not None:
                logger.debug(f"Using cached {lease_length} savings plan price for {instance_type}: ${cached_price}/hr")
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

        # Cache miss - fetch from AWS
        pricing_region = self._get_pricing_region(region)
        filters = self._build_ec2_filters(instance_type, pricing_region)

        for attempt in range(max_retries + 1):
            try:
                DebugLog.log(f"Querying Pricing API for {lease_length} savings plan: {instance_type} in {pricing_region}")
                response = self.aws_client.pricing_client.get_products(
                    ServiceCode='AmazonEC2',
                    Filters=filters,
                    MaxResults=10
                )

                if not response.get('PriceList'):
                    DebugLog.log(f"No PriceList returned for savings plan {instance_type} in {pricing_region}")
                    # Cache the None result
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
                    # Cache the result
                    if self.cache:
                        self.cache.set(region, instance_type, cache_key, best_price)
                    return best_price

                DebugLog.log(f"No {lease_length} savings plan pricing found for {instance_type}")
                # Cache the None result
                if self.cache:
                    self.cache.set(region, instance_type, cache_key, None)
                return None

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))

                # Handle rate limiting with retry
                if error_code == "Throttling" or error_code == "ThrottlingException":
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        DebugLog.log(f"Rate limited for savings plan {instance_type}, retrying in {wait_time:.1f}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        DebugLog.log(f"Rate limited for savings plan {instance_type} after {max_retries} retries")
                        return None

                DebugLog.log(f"Pricing API error for savings plan {instance_type}: {error_code} - {error_message}")
                if error_code == "AccessDeniedException":
                    raise Exception(f"AWS Pricing API error ({error_code}): {error_message}")
                return None
            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    DebugLog.log(f"Exception for savings plan {instance_type}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                DebugLog.log(f"Pricing API exception for savings plan {instance_type}: {str(e)}")
                return None

        # All retries failed
        if self.cache:
            self.cache.set(region, instance_type, cache_key, None)
        return None

    def get_reserved_instance_price(
        self,
        instance_type: str,
        region: str,
        lease_length: str = "1yr",
        payment_option: str = "no_upfront",
        max_retries: int = 3
    ) -> float | None:
        """
        Get Reserved Instance price for an instance type (Standard RIs only)

        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            lease_length: "1yr" or "3yr"
            payment_option: "no_upfront", "partial_upfront", or "all_upfront"
            max_retries: Maximum number of retries for rate limiting

        Returns:
            RI effective hourly rate in USD, or None if not available
        """
        # Check cache first
        cache_key = f"ri_{lease_length}_{payment_option}"
        if self.cache:
            cached_price = self.cache.get(region, instance_type, cache_key)
            if cached_price is not None:
                logger.debug(f"Using cached {lease_length} RI {payment_option} price for {instance_type}: ${cached_price}/hr")
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

        # Cache miss - fetch from AWS
        pricing_region = self._get_pricing_region(region)
        filters = self._build_ec2_filters(instance_type, pricing_region)

        for attempt in range(max_retries + 1):
            try:
                DebugLog.log(f"Querying Pricing API for {lease_length} RI {payment_option}: {instance_type} in {pricing_region}")
                response = self.aws_client.pricing_client.get_products(
                    ServiceCode='AmazonEC2',
                    Filters=filters,
                    MaxResults=10
                )

                if not response.get('PriceList'):
                    DebugLog.log(f"No PriceList returned for RI {instance_type} in {pricing_region}")
                    # Cache the None result
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
                    # Cache the result
                    if self.cache:
                        self.cache.set(region, instance_type, cache_key, best_price)
                    return best_price

                DebugLog.log(f"No {lease_length} RI {payment_option} pricing found for {instance_type}")
                # Cache the None result
                if self.cache:
                    self.cache.set(region, instance_type, cache_key, None)
                return None

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))

                # Handle rate limiting with retry
                if error_code == "Throttling" or error_code == "ThrottlingException":
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        DebugLog.log(f"Rate limited for RI {instance_type}, retrying in {wait_time:.1f}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        DebugLog.log(f"Rate limited for RI {instance_type} after {max_retries} retries")
                        return None

                DebugLog.log(f"Pricing API error for RI {instance_type}: {error_code} - {error_message}")
                if error_code == "AccessDeniedException":
                    raise Exception(f"AWS Pricing API error ({error_code}): {error_message}")
                return None
            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    DebugLog.log(f"Exception for RI {instance_type}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                DebugLog.log(f"Pricing API exception for RI {instance_type}: {str(e)}")
                return None

        # All retries failed
        if self.cache:
            self.cache.set(region, instance_type, cache_key, None)
        return None

    def get_pricing(self, instance_type: str, region: str) -> dict[str, float | None]:
        """
        Get comprehensive pricing for an instance type

        Args:
            instance_type: EC2 instance type
            region: AWS region code

        Returns:
            Dictionary with 'on_demand', 'spot', 'savings_1yr', and 'savings_3yr' keys
        """
        return {
            'on_demand': self.get_on_demand_price(instance_type, region),
            'spot': self.get_spot_price(instance_type, region),
            'savings_1yr': self.get_savings_plan_price(instance_type, region, "1yr"),
            'savings_3yr': self.get_savings_plan_price(instance_type, region, "3yr"),
        }
