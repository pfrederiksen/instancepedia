"""Async AWS client wrapper using aioboto3"""

import aioboto3
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from botocore.config import Config


class AsyncAWSClient:
    """Async wrapper for AWS clients using aioboto3 with connection pooling"""

    def __init__(
        self,
        region: str,
        profile: Optional[str] = None,
        connect_timeout: int = 10,
        read_timeout: int = 60,
        pricing_timeout: int = 90,
        max_pool_connections: int = 50
    ):
        """
        Initialize async AWS client

        Args:
            region: AWS region code
            profile: Optional AWS profile name
            connect_timeout: Connection timeout in seconds (default: 10)
            read_timeout: Read timeout for AWS API calls in seconds (default: 60)
            pricing_timeout: Read timeout for pricing API calls in seconds (default: 90)
            max_pool_connections: Maximum connections in the pool (default: 50)
        """
        self.region = region
        self.profile = profile
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.pricing_timeout = pricing_timeout
        self.max_pool_connections = max_pool_connections
        self._session = None
        self._ec2_client = None
        self._pricing_client = None
        self._lock = asyncio.Lock()

    def _get_session(self) -> aioboto3.Session:
        """Get aioboto3 session (lazy initialization)"""
        if self._session is None:
            if self.profile:
                self._session = aioboto3.Session(profile_name=self.profile)
            else:
                self._session = aioboto3.Session()
        return self._session

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        await self.close()
        return False

    async def _close_client_internal(self, client) -> None:
        """Internal method to close a single client with proper aiohttp cleanup"""
        try:
            # aioboto3/aiobotocore stores the http session in the endpoint
            # Try multiple possible attribute paths
            http_session = None

            # Path 1: _endpoint.http_session (aiobotocore style)
            if hasattr(client, '_endpoint'):
                endpoint = client._endpoint
                if hasattr(endpoint, 'http_session'):
                    http_session = endpoint.http_session
                elif hasattr(endpoint, '_http_session'):
                    http_session = endpoint._http_session

            # Path 2: _client._endpoint (wrapped client style)
            if http_session is None and hasattr(client, '_client'):
                inner = client._client
                if hasattr(inner, '_endpoint'):
                    endpoint = inner._endpoint
                    if hasattr(endpoint, 'http_session'):
                        http_session = endpoint.http_session
                    elif hasattr(endpoint, '_http_session'):
                        http_session = endpoint._http_session

            # Close the http session if found
            if http_session is not None:
                connector = getattr(http_session, 'connector', None) or getattr(http_session, '_connector', None)
                if connector is not None:
                    connector.close()
                await http_session.close()

            # Call the client's __aexit__
            await client.__aexit__(None, None, None)

            # aiohttp graceful shutdown wait
            await asyncio.sleep(0.250)
        except Exception:
            pass  # Ignore all cleanup errors

    async def close(self):
        """Close all clients and cleanup resources

        Properly closes aioboto3 clients and their underlying aiohttp sessions.
        Uses fire-and-forget tasks to ensure cleanup completes even if the caller is cancelled.
        """
        async with self._lock:
            clients_to_close = []

            if self._ec2_client is not None:
                clients_to_close.append(self._ec2_client)
                self._ec2_client = None

            if self._pricing_client is not None:
                clients_to_close.append(self._pricing_client)
                self._pricing_client = None

            self._session = None

        # Schedule cleanup tasks that will continue even if this coroutine is cancelled
        # This is critical for proper aiohttp shutdown
        cleanup_tasks = []
        for client in clients_to_close:
            try:
                # Create a task that's independent of the current coroutine
                task = asyncio.create_task(self._close_client_internal(client))
                cleanup_tasks.append(task)
            except Exception:
                pass

        # Wait for cleanup with a timeout, but don't fail if cancelled
        if cleanup_tasks:
            try:
                # Use gather with return_exceptions to not raise on individual failures
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=1.0
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # If we time out or are cancelled, the tasks will still run
                # until the event loop stops
                pass

    @asynccontextmanager
    async def get_ec2_client(self):
        """
        Get EC2 client with connection pooling

        Usage:
            async with client.get_ec2_client() as ec2:
                response = await ec2.describe_instance_types()
        """
        async with self._lock:
            if self._ec2_client is None:
                session = self._get_session()
                config = Config(
                    connect_timeout=self.connect_timeout,
                    read_timeout=self.read_timeout,
                    retries={'max_attempts': 3, 'mode': 'standard'},
                    max_pool_connections=self.max_pool_connections
                )
                self._ec2_client = session.client("ec2", region_name=self.region, config=config)
                self._ec2_client = await self._ec2_client.__aenter__()

        try:
            yield self._ec2_client
        except Exception:
            # On error, close the client so it gets recreated next time
            async with self._lock:
                if self._ec2_client is not None:
                    try:
                        await self._ec2_client.__aexit__(None, None, None)
                    except Exception:
                        pass
                    self._ec2_client = None
            raise

    @asynccontextmanager
    async def get_pricing_client(self):
        """
        Get Pricing API client with connection pooling

        Note: Pricing API is only available in us-east-1 and ap-south-1

        Usage:
            async with client.get_pricing_client() as pricing:
                response = await pricing.get_products(...)
        """
        async with self._lock:
            if self._pricing_client is None:
                session = self._get_session()
                config = Config(
                    connect_timeout=self.connect_timeout,
                    read_timeout=self.pricing_timeout,
                    retries={'max_attempts': 3, 'mode': 'standard'},
                    max_pool_connections=self.max_pool_connections
                )
                # Pricing API is only available in us-east-1
                self._pricing_client = session.client("pricing", region_name="us-east-1", config=config)
                self._pricing_client = await self._pricing_client.__aenter__()

        try:
            yield self._pricing_client
        except Exception:
            # On error, close the client so it gets recreated next time
            async with self._lock:
                if self._pricing_client is not None:
                    try:
                        await self._pricing_client.__aexit__(None, None, None)
                    except Exception:
                        pass
                    self._pricing_client = None
            raise

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
