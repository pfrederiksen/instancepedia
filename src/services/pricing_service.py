"""EC2 pricing service"""

from typing import Optional, Dict, List
from botocore.exceptions import ClientError, BotoCoreError
from decimal import Decimal
import time

from src.services.aws_client import AWSClient
from src.debug import DebugLog


class PricingService:
    """Service for fetching EC2 instance pricing"""

    def __init__(self, aws_client: AWSClient):
        """
        Initialize pricing service
        
        Args:
            aws_client: AWS client wrapper
        """
        self.aws_client = aws_client

    def get_on_demand_price(self, instance_type: str, region: str, max_retries: int = 3) -> Optional[float]:
        """
        Get on-demand price for an instance type in a region
        
        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            max_retries: Maximum number of retries for rate limiting
            
        Returns:
            Price per hour in USD, or None if not available
        """
        for attempt in range(max_retries + 1):
            try:
                # Map region to pricing API region name
                # AWS Pricing API uses human-readable location names, not region codes
                region_map = {
                'us-east-1': 'US East (N. Virginia)',
                'us-east-2': 'US East (Ohio)',
                'us-west-1': 'US West (N. California)',
                'us-west-2': 'US West (Oregon)',
                'us-west-3': 'US West (Phoenix)',
                'us-west-4': 'US West (Las Vegas)',
                'us-east-3': 'US East (Columbus)',
                'af-south-1': 'Africa (Cape Town)',
                'ap-east-1': 'Asia Pacific (Hong Kong)',
                'ap-south-1': 'Asia Pacific (Mumbai)',
                'ap-south-2': 'Asia Pacific (Hyderabad)',
                'ap-northeast-1': 'Asia Pacific (Tokyo)',
                'ap-northeast-2': 'Asia Pacific (Seoul)',
                'ap-northeast-3': 'Asia Pacific (Osaka)',
                'ap-southeast-1': 'Asia Pacific (Singapore)',
                'ap-southeast-2': 'Asia Pacific (Sydney)',
                'ap-southeast-3': 'Asia Pacific (Jakarta)',
                'ap-southeast-4': 'Asia Pacific (Melbourne)',
                'ap-southeast-5': 'Asia Pacific (Osaka)',
                'ca-central-1': 'Canada (Central)',
                'eu-central-1': 'EU (Frankfurt)',
                'eu-central-2': 'EU (Zurich)',
                'eu-west-1': 'EU (Ireland)',
                'eu-west-2': 'EU (London)',
                'eu-west-3': 'EU (Paris)',
                'eu-north-1': 'EU (Stockholm)',
                'eu-north-2': 'EU (Warsaw)',
                'eu-south-1': 'EU (Milan)',
                'eu-south-2': 'EU (Spain)',
                'me-south-1': 'Middle East (Bahrain)',
                'me-central-1': 'Middle East (UAE)',
                'il-central-1': 'Israel (Tel Aviv)',
                'sa-east-1': 'South America (Sao Paulo)',  # Note: AWS uses "Sao" without special character
            }
            
                pricing_region = region_map.get(region)
                if not pricing_region:
                    # If region not in map, try using region code directly (may not work)
                    DebugLog.log(f"Warning: Region {region} not in pricing region map, using region code directly")
                    pricing_region = region
                
                # Try to get pricing - use simpler filters first
                filters = [
                    {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonEC2'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': pricing_region},
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                ]
                
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
                import json
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
        return None

    def get_spot_price(self, instance_type: str, region: str) -> Optional[float]:
        """
        Get current spot price for an instance type in a region
        
        Args:
            instance_type: EC2 instance type (e.g., 't3.micro')
            region: AWS region code (e.g., 'us-east-1')
            
        Returns:
            Current spot price per hour in USD, or None if not available
        """
        try:
            response = self.aws_client.ec2_client.describe_spot_price_history(
                InstanceTypes=[instance_type],
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=1
            )
            
            if not response.get('SpotPriceHistory'):
                return None
            
            # Get the most recent spot price
            latest = response['SpotPriceHistory'][0]
            return float(latest['SpotPrice'])
            
        except ClientError:
            return None
        except BotoCoreError:
            return None
        except Exception:
            return None
    
    def get_spot_prices_batch(self, instance_types: List[str], region: str, max_retries: int = 3) -> Dict[str, Optional[float]]:
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

    def get_pricing(self, instance_type: str, region: str) -> Dict[str, Optional[float]]:
        """
        Get both on-demand and spot pricing for an instance type
        
        Args:
            instance_type: EC2 instance type
            region: AWS region code
            
        Returns:
            Dictionary with 'on_demand' and 'spot' keys
        """
        return {
            'on_demand': self.get_on_demand_price(instance_type, region),
            'spot': self.get_spot_price(instance_type, region),
        }
