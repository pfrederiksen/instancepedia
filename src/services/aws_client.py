"""AWS client wrapper"""

import boto3
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError


class AWSClient:
    """Wrapper for AWS clients"""

    def __init__(self, region: str, profile: Optional[str] = None):
        """
        Initialize AWS client
        
        Args:
            region: AWS region code
            profile: Optional AWS profile name
        """
        self.region = region
        self.profile = profile
        self._ec2_client = None
        self._pricing_client = None

    def _get_session(self):
        """Get boto3 session"""
        if self.profile:
            return boto3.Session(profile_name=self.profile)
        return boto3.Session()

    @property
    def ec2_client(self):
        """Get EC2 client, creating if necessary"""
        if self._ec2_client is None:
            try:
                session = self._get_session()
                self._ec2_client = session.client("ec2", region_name=self.region)
            except NoCredentialsError:
                raise ValueError(
                    "AWS credentials not found. Please configure credentials using:\n"
                    "  - AWS CLI: aws configure\n"
                    "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
                    "  - Or specify a profile with --profile"
                )
            except Exception as e:
                raise ValueError(f"Failed to create AWS client: {str(e)}")
        return self._ec2_client

    @property
    def pricing_client(self):
        """Get Pricing API client, creating if necessary"""
        if self._pricing_client is None:
            try:
                session = self._get_session()
                # Pricing API is only available in us-east-1 and ap-south-1
                self._pricing_client = session.client("pricing", region_name="us-east-1")
            except NoCredentialsError:
                raise ValueError(
                    "AWS credentials not found. Please configure credentials using:\n"
                    "  - AWS CLI: aws configure\n"
                    "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
                    "  - Or specify a profile with --profile"
                )
            except Exception as e:
                raise ValueError(f"Failed to create Pricing API client: {str(e)}")
        return self._pricing_client

    def test_connection(self) -> bool:
        """Test AWS connection"""
        try:
            self.ec2_client.describe_regions(MaxResults=1)
            return True
        except (ClientError, BotoCoreError) as e:
            return False
    
    def get_accessible_regions(self) -> list[str]:
        """
        Get list of regions that are enabled and accessible to the current AWS account.
        Only returns regions the account can actually use (not opt-in required or disabled).
        
        Returns:
            List of region codes that are accessible
        """
        try:
            # Use a default region to query for accessible regions
            session = self._get_session()
            ec2 = session.client("ec2", region_name="us-east-1")  # Use a standard region for the query
            # By default, describe_regions() returns only regions enabled for the account
            # This avoids trying to access regions that require opt-in or are disabled
            response = ec2.describe_regions()
            accessible_regions = [region["RegionName"] for region in response["Regions"]]
            return accessible_regions
        except Exception as e:
            # If we can't get the list, return empty and let the app handle it
            return []

