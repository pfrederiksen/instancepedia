"""EC2 instance type service"""

from typing import List, Optional
from botocore.exceptions import ClientError, BotoCoreError

from src.models.instance_type import InstanceType, PricingInfo
from src.services.aws_client import AWSClient
from src.services.pricing_service import PricingService


class InstanceService:
    """Service for fetching EC2 instance types"""

    def __init__(self, aws_client: AWSClient):
        """
        Initialize instance service
        
        Args:
            aws_client: AWS client wrapper
        """
        self.aws_client = aws_client

    def get_instance_types(self, fetch_pricing: bool = False) -> List[InstanceType]:
        """
        Fetch all available instance types for the region
        
        Args:
            fetch_pricing: If True, fetch pricing information for each instance type (slower)
        
        Returns:
            List of InstanceType objects
            
        Raises:
            Exception: If API call fails
        """
        instance_types = []
        next_token = None

        try:
            while True:
                params = {"MaxResults": 100}
                if next_token:
                    params["NextToken"] = next_token

                response = self.aws_client.ec2_client.describe_instance_types(**params)

                for instance_data in response.get("InstanceTypes", []):
                    instance_type = InstanceType.from_aws_response(instance_data)
                    instance_types.append(instance_type)

                next_token = response.get("NextToken")
                if not next_token:
                    break

            instance_types = sorted(instance_types, key=lambda x: x.instance_type)
            
            # Fetch pricing if requested
            if fetch_pricing:
                pricing_service = PricingService(self.aws_client)
                for instance_type in instance_types:
                    try:
                        pricing_data = pricing_service.get_pricing(
                            instance_type.instance_type,
                            self.aws_client.region
                        )
                        instance_type.pricing = PricingInfo(
                            on_demand_price=pricing_data.get('on_demand'),
                            spot_price=pricing_data.get('spot')
                        )
                    except Exception:
                        # If pricing fails, continue without pricing info
                        pass

            return instance_types

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise Exception(f"AWS API error ({error_code}): {error_msg}")
        except BotoCoreError as e:
            raise Exception(f"AWS connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to fetch instance types: {str(e)}")
    
    def update_instance_pricing(self, instance_type: InstanceType) -> None:
        """
        Update pricing information for a single instance type
        
        Args:
            instance_type: InstanceType to update pricing for
        """
        try:
            pricing_service = PricingService(self.aws_client)
            pricing_data = pricing_service.get_pricing(
                instance_type.instance_type,
                self.aws_client.region
            )
            instance_type.pricing = PricingInfo(
                on_demand_price=pricing_data.get('on_demand'),
                spot_price=pricing_data.get('spot')
            )
        except Exception:
            # If pricing fails, set to None
            instance_type.pricing = None

