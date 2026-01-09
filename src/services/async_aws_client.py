"""Async AWS client wrapper using aioboto3"""

import aioboto3
import aiohttp
import asyncio
import atexit
import gc
import weakref
from typing import Optional
from contextlib import asynccontextmanager, AsyncExitStack
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from botocore.config import Config


# Global registry of all AsyncAWSClient instances for cleanup at exit
_active_clients: weakref.WeakSet = weakref.WeakSet()


def _cleanup_all_aiohttp_resources():
    """Force cleanup of any unclosed aiohttp resources at interpreter exit.

    This is a last-resort cleanup that runs when Python exits.
    It finds any unclosed aiohttp sessions/connectors and closes them.
    """
    # First, try to close any registered clients
    for client in list(_active_clients):
        try:
            client._close_connectors_sync()
        except Exception:
            pass

    # Then do a GC sweep to find any remaining aiohttp resources
    gc.collect()
    for obj in gc.get_objects():
        try:
            if isinstance(obj, aiohttp.ClientSession):
                if not obj.closed:
                    if obj._connector and not obj._connector.closed:
                        obj._connector.close()
                    obj._closed = True
            elif isinstance(obj, aiohttp.TCPConnector):
                if not obj.closed:
                    obj.close()
        except Exception:
            pass


# Register cleanup at interpreter exit
atexit.register(_cleanup_all_aiohttp_resources)


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
        self._exit_stack = AsyncExitStack()
        # Register in global registry for cleanup at exit
        _active_clients.add(self)

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
        # ALWAYS do sync cleanup first to ensure connectors are closed
        # This prevents warnings even if async cleanup is cancelled
        self._close_connectors_sync()

        # Then try async cleanup for graceful shutdown
        try:
            await self.close()
        except asyncio.CancelledError:
            # Sync cleanup already done, just re-raise
            raise
        return False

    def _close_connectors_sync(self) -> None:
        """Synchronously close aiohttp connectors and mark sessions as closed.

        This is used when async cleanup is cancelled (e.g., during app exit)
        to ensure TCP connections are properly closed and no warnings are emitted.
        """
        for client in [self._ec2_client, self._pricing_client]:
            if client is not None:
                self._close_single_client_sync(client)

        self._ec2_client = None
        self._pricing_client = None
        self._session = None

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
        Uses AsyncExitStack for proper cleanup, with sync fallback.
        """
        # FIRST: Do sync cleanup to prevent warnings even if async fails
        self._close_connectors_sync()

        # Then try proper async cleanup via exit stack
        try:
            await self._exit_stack.aclose()
        except Exception:
            pass

        # Clear references
        self._ec2_client = None
        self._pricing_client = None
        self._session = None

        # Create new exit stack for potential reuse
        self._exit_stack = AsyncExitStack()

    def _close_single_client_sync(self, client) -> None:
        """Synchronously close a single aioboto3 client's connector and mark session closed."""
        try:
            if hasattr(client, '_endpoint'):
                endpoint = client._endpoint
                http_session = getattr(endpoint, 'http_session', None) or getattr(endpoint, '_http_session', None)
                if http_session is not None:
                    # Close the connector (handles TCP connections)
                    connector = getattr(http_session, '_connector', None) or getattr(http_session, 'connector', None)
                    if connector is not None and not getattr(connector, 'closed', True):
                        connector.close()
                    # Mark the session as closed to prevent __del__ warning
                    if hasattr(http_session, '_closed'):
                        http_session._closed = True
        except Exception:
            pass  # Best effort - don't fail on sync cleanup

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
                # Use AsyncExitStack for proper cleanup management
                client_cm = session.client("ec2", region_name=self.region, config=config)
                self._ec2_client = await self._exit_stack.enter_async_context(client_cm)

        try:
            yield self._ec2_client
        except Exception:
            # On error, close the client so it gets recreated next time
            async with self._lock:
                if self._ec2_client is not None:
                    self._close_single_client_sync(self._ec2_client)
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
                # Use AsyncExitStack for proper cleanup management
                client_cm = session.client("pricing", region_name="us-east-1", config=config)
                self._pricing_client = await self._exit_stack.enter_async_context(client_cm)

        try:
            yield self._pricing_client
        except Exception:
            # On error, close the client so it gets recreated next time
            async with self._lock:
                if self._pricing_client is not None:
                    self._close_single_client_sync(self._pricing_client)
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
