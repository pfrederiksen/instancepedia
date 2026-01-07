"""AWS client wrapper"""

import boto3
import logging
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

from src.exceptions import (
    AWSCredentialsError,
    AWSConnectionError,
    AWSRegionError
)

logger = logging.getLogger("instancepedia")


class AWSClient:
    """Wrapper for AWS clients"""

    def __init__(self, region: str, profile: Optional[str] = None, validate_region: bool = False):
        """
        Initialize AWS client

        Args:
            region: AWS region code
            profile: Optional AWS profile name
            validate_region: If True, validate that region is accessible (slower but safer)
        """
        self.region = region
        self.profile = profile
        self._ec2_client = None
        self._pricing_client = None

        # Optionally validate region on initialization
        if validate_region:
            self._validate_region()

    def _get_session(self):
        """Get boto3 session"""
        if self.profile:
            return boto3.Session(profile_name=self.profile)
        return boto3.Session()

    def _validate_region(self) -> None:
        """
        Validate that the region is accessible

        Raises:
            AWSRegionError: If region is invalid or not accessible
            AWSCredentialsError: If credentials are missing
            AWSConnectionError: If unable to connect to AWS
        """
        try:
            accessible_regions = self.get_accessible_regions()
            if self.region not in accessible_regions:
                logger.error(f"Region '{self.region}' is not accessible")
                raise AWSRegionError(
                    f"Region '{self.region}' is not accessible. "
                    f"This region may require opt-in or may not be enabled for your account.\n"
                    f"Use 'instancepedia regions' to see available regions."
                )
        except AWSRegionError:
            # Re-raise AWSRegionError as-is
            raise
        except (AWSCredentialsError, AWSConnectionError):
            # Re-raise credential and connection errors as-is
            raise
        except Exception as e:
            logger.error(f"Failed to validate region: {e}")
            raise AWSConnectionError(f"Failed to validate region '{self.region}': {str(e)}") from e

    @property
    def ec2_client(self):
        """Get EC2 client, creating if necessary"""
        if self._ec2_client is None:
            try:
                session = self._get_session()
                self._ec2_client = session.client("ec2", region_name=self.region)
            except NoCredentialsError as e:
                logger.error("AWS credentials not found")
                raise AWSCredentialsError(
                    "AWS credentials not found. Please configure credentials using:\n"
                    "  - AWS CLI: aws configure\n"
                    "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
                    "  - Or specify a profile with --profile"
                ) from e
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                # Check for region-specific errors
                if error_code in ("InvalidRegionName", "UnauthorizedOperation"):
                    logger.error(f"Region '{self.region}' error: {error_code}")
                    raise AWSRegionError(
                        f"Cannot access region '{self.region}'. "
                        f"The region may be invalid or not enabled for your account.\n"
                        f"Use 'instancepedia regions' to see available regions."
                    ) from e
                logger.error(f"Failed to create EC2 client: {e}")
                raise AWSConnectionError(f"Failed to create EC2 client: {str(e)}") from e
            except BotoCoreError as e:
                logger.error(f"Failed to create EC2 client: {e}")
                raise AWSConnectionError(f"Failed to create EC2 client: {str(e)}") from e
        return self._ec2_client

    @property
    def pricing_client(self):
        """Get Pricing API client, creating if necessary"""
        if self._pricing_client is None:
            try:
                session = self._get_session()
                # Pricing API is only available in us-east-1 and ap-south-1
                self._pricing_client = session.client("pricing", region_name="us-east-1")
            except NoCredentialsError as e:
                logger.error("AWS credentials not found")
                raise AWSCredentialsError(
                    "AWS credentials not found. Please configure credentials using:\n"
                    "  - AWS CLI: aws configure\n"
                    "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
                    "  - Or specify a profile with --profile"
                ) from e
            except (ClientError, BotoCoreError) as e:
                logger.error(f"Failed to create Pricing API client: {e}")
                raise AWSConnectionError(f"Failed to create Pricing API client: {str(e)}") from e
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

        Raises:
            AWSCredentialsError: If credentials are missing or invalid
            AWSConnectionError: If unable to connect to AWS
        """
        try:
            # Use a default region to query for accessible regions
            session = self._get_session()
            ec2 = session.client("ec2", region_name="us-east-1")  # Use a standard region for the query
            # By default, describe_regions() returns only regions enabled for the account
            # This avoids trying to access regions that require opt-in or are disabled
            response = ec2.describe_regions()
            accessible_regions = [region["RegionName"] for region in response["Regions"]]
            logger.debug(f"Found {len(accessible_regions)} accessible regions")
            return accessible_regions
        except NoCredentialsError as e:
            logger.error("AWS credentials not found when listing regions")
            raise AWSCredentialsError("AWS credentials not found") from e
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to get accessible regions: {e}")
            raise AWSConnectionError(f"Failed to get accessible regions: {str(e)}") from e

