"""Async AWS client wrapper using aioboto3"""

import aioboto3
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from botocore.config import Config


class AsyncAWSClient:
    """Async wrapper for AWS clients using aioboto3"""

    def __init__(
        self,
        region: str,
        profile: Optional[str] = None,
        connect_timeout: int = 10,
        read_timeout: int = 60,
        pricing_timeout: int = 90
    ):
        """
        Initialize async AWS client

        Args:
            region: AWS region code
            profile: Optional AWS profile name
            connect_timeout: Connection timeout in seconds (default: 10)
            read_timeout: Read timeout for AWS API calls in seconds (default: 60)
            pricing_timeout: Read timeout for pricing API calls in seconds (default: 90)
        """
        self.region = region
        self.profile = profile
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.pricing_timeout = pricing_timeout
        self._session = None

    def _get_session(self) -> aioboto3.Session:
        """Get aioboto3 session (lazy initialization)"""
        if self._session is None:
            if self.profile:
                self._session = aioboto3.Session(profile_name=self.profile)
            else:
                self._session = aioboto3.Session()
        return self._session

    def get_ec2_client(self):
        """
        Get EC2 client context manager

        Usage:
            async with client.get_ec2_client() as ec2:
                response = await ec2.describe_instance_types()
        """
        session = self._get_session()
        config = Config(
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
        return session.client("ec2", region_name=self.region, config=config)

    def get_pricing_client(self):
        """
        Get Pricing API client context manager

        Note: Pricing API is only available in us-east-1 and ap-south-1

        Usage:
            async with client.get_pricing_client() as pricing:
                response = await pricing.get_products(...)
        """
        session = self._get_session()
        config = Config(
            connect_timeout=self.connect_timeout,
            read_timeout=self.pricing_timeout,
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
        # Pricing API is only available in us-east-1
        return session.client("pricing", region_name="us-east-1", config=config)

    async def test_connection(self) -> bool:
        """Test AWS connection asynchronously"""
        try:
            async with self.get_ec2_client() as ec2:
                await ec2.describe_regions(MaxResults=1)
            return True
        except (ClientError, BotoCoreError):
            return False

    async def get_accessible_regions(self) -> list[str]:
        """
        Get list of regions that are enabled and accessible to the current AWS account.

        Returns:
            List of region codes that are accessible
        """
        try:
            session = self._get_session()
            config = Config(
                connect_timeout=self.connect_timeout,
                read_timeout=self.read_timeout,
                retries={'max_attempts': 3, 'mode': 'standard'}
            )
            async with session.client("ec2", region_name="us-east-1", config=config) as ec2:
                response = await ec2.describe_regions()
                return [region["RegionName"] for region in response["Regions"]]
        except Exception:
            return []
