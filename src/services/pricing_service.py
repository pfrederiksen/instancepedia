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
                'af-south-1': 'Africa (Cape Town)',
                'ap-east-1': 'Asia Pacific (Hong Kong)',
                'ap-south-1': 'Asia Pacific (Mumbai)',
                'ap-northeast-1': 'Asia Pacific (Tokyo)',
                'ap-northeast-2': 'Asia Pacific (Seoul)',
                'ap-northeast-3': 'Asia Pacific (Osaka)',
                'ap-southeast-1': 'Asia Pacific (Singapore)',
                'ap-southeast-2': 'Asia Pacific (Sydney)',
                'ca-central-1': 'Canada (Central)',
                'eu-central-1': 'EU (Frankfurt)',
                'eu-west-1': 'EU (Ireland)',
                'eu-west-2': 'EU (London)',
                'eu-west-3': 'EU (Paris)',
                'eu-north-1': 'EU (Stockholm)',
                'eu-south-1': 'EU (Milan)',
                'me-south-1': 'Middle East (Bahrain)',
                'sa-east-1': 'South America (Sao Paulo)',  # Note: AWS uses "Sao" without special character
            }
            
                pricing_region = region_map.get(region)
                if not pricing_region:
                    # If region not in map, try using region code directly (may not work)
                    pricing_region = region
                
                # Try to get pricing - use simpler filters first
                filters = [
                    {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonEC2'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': pricing_region},
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                ]
                
                DebugLog.log(f"Querying Pricing API for {instance_type} in {pricing_region}")
                response = self.aws_client.pricing_client.get_products(
                    ServiceCode='AmazonEC2',
                    Filters=filters,
                    MaxResults=1
                )
                
                if not response.get('PriceList'):
                    DebugLog.log(f"No PriceList returned for {instance_type} in {pricing_region}")
                    return None
                
                DebugLog.log(f"Got PriceList with {len(response['PriceList'])} items for {instance_type}")
                
                # Parse the price from the response
                import json
                price_data = json.loads(response['PriceList'][0])
                
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
                term_key = list(on_demand.keys())[0]
                price_dimensions = on_demand[term_key].get('priceDimensions', {})
                
                if not price_dimensions:
                    DebugLog.log(f"No 'priceDimensions' for {instance_type}")
                    return None
                
                # Get the first price dimension
                dimension_key = list(price_dimensions.keys())[0]
                price_per_unit = price_dimensions[dimension_key].get('pricePerUnit', {})
                
                # Get USD price
                usd_price = price_per_unit.get('USD')
                if usd_price:
                    price = float(Decimal(usd_price))
                    DebugLog.log(f"Found price for {instance_type}: ${price}/hr")
                    return price
                
                DebugLog.log(f"No USD price found in pricePerUnit for {instance_type}")
                return None
                
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))
                
                # Handle rate limiting with retry
                if error_code == "Throttling" or error_code == "ThrottlingException" or "429" in str(e):
                    if attempt < max_retries:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        DebugLog.log(f"Rate limited for {instance_type}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
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
                        response = self.aws_client.ec2_client.describe_spot_price_history(
                            InstanceTypes=chunk,
                            ProductDescriptions=['Linux/UNIX'],
                            MaxResults=len(chunk)
                        )
                        
                        # Group by instance type, keeping most recent
                        for price_data in response.get('SpotPriceHistory', []):
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
