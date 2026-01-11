"""Tests for AsyncAWSClient"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

from src.services.async_aws_client import AsyncAWSClient


class TestAsyncAWSClientInit:
    """Test AsyncAWSClient initialization"""

    def test_init_basic(self):
        """Test basic initialization with region only"""
        client = AsyncAWSClient(region="us-east-1")

        assert client.region == "us-east-1"
        assert client.profile is None
        assert client.connect_timeout == 10
        assert client.read_timeout == 60
        assert client.pricing_timeout == 90
        assert client.max_pool_connections == 50
        assert client._session is None
        assert client._ec2_client is None
        assert client._pricing_client is None

    def test_init_with_profile(self):
        """Test initialization with AWS profile"""
        client = AsyncAWSClient(region="us-west-2", profile="my-profile")

        assert client.region == "us-west-2"
        assert client.profile == "my-profile"

    def test_init_with_custom_timeouts(self):
        """Test initialization with custom timeout values"""
        client = AsyncAWSClient(
            region="eu-west-1",
            connect_timeout=20,
            read_timeout=120,
            pricing_timeout=180,
            max_pool_connections=100
        )

        assert client.connect_timeout == 20
        assert client.read_timeout == 120
        assert client.pricing_timeout == 180
        assert client.max_pool_connections == 100


class TestSessionCreation:
    """Test aioboto3 session creation"""

    @patch('src.services.async_aws_client.aioboto3.Session')
    def test_get_session_without_profile(self, mock_session_class):
        """Test session creation without profile"""
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance

        client = AsyncAWSClient(region="us-east-1")
        session = client._get_session()

        # Verify Session() was called without profile_name
        mock_session_class.assert_called_once_with()
        assert session == mock_session_instance

    @patch('src.services.async_aws_client.aioboto3.Session')
    def test_get_session_with_profile(self, mock_session_class):
        """Test session creation with profile"""
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance

        client = AsyncAWSClient(region="us-east-1", profile="my-profile")
        session = client._get_session()

        # Verify Session() was called with profile_name
        mock_session_class.assert_called_once_with(profile_name="my-profile")
        assert session == mock_session_instance

    @patch('src.services.async_aws_client.aioboto3.Session')
    def test_session_caching(self, mock_session_class):
        """Test that session is cached after first creation"""
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance

        client = AsyncAWSClient(region="us-east-1")

        # First call creates session
        session1 = client._get_session()
        # Second call returns cached session
        session2 = client._get_session()

        # Should be same instance
        assert session1 == session2
        # Session class should only be instantiated once
        mock_session_class.assert_called_once()


class TestEC2ClientContextManager:
    """Test EC2 client context manager"""

    @pytest.mark.asyncio
    async def test_get_ec2_client_lazy_creation(self):
        """Test EC2 client is created on first access"""
        # Create mock client context manager
        mock_ec2_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client

        # Create mock session
        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1")

        # Patch _get_session to return our mock
        with patch.object(client, '_get_session', return_value=mock_session):
            # Initially None
            assert client._ec2_client is None

            # Access creates client
            async with client.get_ec2_client() as ec2:
                assert ec2 == mock_ec2_client
                assert client._ec2_client == mock_ec2_client

            # Verify session.client was called
            mock_session.client.assert_called_once()
            call_args = mock_session.client.call_args
            assert call_args[0][0] == "ec2"
            assert call_args[1]["region_name"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_get_ec2_client_reuses_cached(self):
        """Test EC2 client is reused after first creation"""
        mock_ec2_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            # First access
            async with client.get_ec2_client() as ec2_1:
                first_client = ec2_1

            # Second access - should reuse
            async with client.get_ec2_client() as ec2_2:
                second_client = ec2_2

            # Should be same instance
            assert first_client == second_client
            # session.client should only be called once
            mock_session.client.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ec2_client_recreates_after_error(self):
        """Test EC2 client is recreated after an error"""
        # First client - will error
        mock_ec2_client_1 = AsyncMock()
        mock_ec2_client_1.describe_instance_types.side_effect = ClientError(
            {"Error": {"Code": "Throttling"}}, "DescribeInstanceTypes"
        )

        # Second client - will succeed
        mock_ec2_client_2 = AsyncMock()

        mock_client_cm_1 = AsyncMock()
        mock_client_cm_1.__aenter__.return_value = mock_ec2_client_1

        mock_client_cm_2 = AsyncMock()
        mock_client_cm_2.__aenter__.return_value = mock_ec2_client_2

        mock_session = Mock()
        mock_session.client.side_effect = [mock_client_cm_1, mock_client_cm_2]

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            # First access - triggers error
            with pytest.raises(ClientError):
                async with client.get_ec2_client() as ec2:
                    await ec2.describe_instance_types()

            # Client should be None after error
            assert client._ec2_client is None

            # Second access - creates new client
            async with client.get_ec2_client() as ec2:
                assert ec2 == mock_ec2_client_2

            # Verify client was created twice
            assert mock_session.client.call_count == 2


class TestPricingClientContextManager:
    """Test Pricing client context manager"""

    @pytest.mark.asyncio
    async def test_get_pricing_client_lazy_creation(self):
        """Test Pricing client is created on first access"""
        mock_pricing_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_pricing_client

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-west-2")  # Different region

        with patch.object(client, '_get_session', return_value=mock_session):
            assert client._pricing_client is None

            async with client.get_pricing_client() as pricing:
                assert pricing == mock_pricing_client
                assert client._pricing_client == mock_pricing_client

            # Verify pricing client always uses us-east-1
            call_args = mock_session.client.call_args
            assert call_args[0][0] == "pricing"
            assert call_args[1]["region_name"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_get_pricing_client_always_uses_us_east_1(self):
        """Test Pricing client always uses us-east-1 regardless of client region"""
        mock_pricing_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_pricing_client

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        # Create client with ap-south-1 region
        client = AsyncAWSClient(region="ap-south-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            async with client.get_pricing_client() as pricing:
                pass

            # Verify us-east-1 was used
            call_args = mock_session.client.call_args
            assert call_args[1]["region_name"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_get_pricing_client_uses_pricing_timeout(self):
        """Test Pricing client uses pricing_timeout instead of read_timeout"""
        mock_pricing_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_pricing_client

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(
            region="us-east-1",
            read_timeout=60,
            pricing_timeout=180
        )

        with patch.object(client, '_get_session', return_value=mock_session):
            async with client.get_pricing_client() as pricing:
                pass

            # Verify pricing timeout was used
            call_args = mock_session.client.call_args
            config = call_args[1]["config"]
            assert config.read_timeout == 180


class TestConnectionTesting:
    """Test async connection testing functionality"""

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test successful connection test"""
        mock_ec2_client = AsyncMock()
        mock_ec2_client.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}

        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client
        mock_client_cm.__aexit__.return_value = None

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client.test_connection()

        assert result is True
        mock_ec2_client.describe_regions.assert_called_once_with(MaxResults=1)

    @pytest.mark.asyncio
    async def test_connection_failure_client_error(self):
        """Test connection test with ClientError"""
        mock_ec2_client = AsyncMock()
        mock_ec2_client.describe_regions.side_effect = ClientError(
            {"Error": {"Code": "UnauthorizedOperation"}}, "DescribeRegions"
        )

        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client
        mock_client_cm.__aexit__.return_value = None

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client.test_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_connection_failure_botocore_error(self):
        """Test connection test with BotoCoreError"""
        mock_ec2_client = AsyncMock()
        mock_ec2_client.describe_regions.side_effect = BotoCoreError()

        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client
        mock_client_cm.__aexit__.return_value = None

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client.test_connection()

        assert result is False


class TestGetAccessibleRegions:
    """Test fetching list of accessible AWS regions"""

    @pytest.mark.asyncio
    async def test_get_accessible_regions_success(self):
        """Test successful fetching of accessible regions"""
        mock_ec2_client = AsyncMock()
        mock_ec2_client.describe_regions.return_value = {
            "Regions": [
                {"RegionName": "us-east-1"},
                {"RegionName": "us-west-2"},
                {"RegionName": "eu-west-1"}
            ]
        }
        mock_ec2_client.__aenter__.return_value = mock_ec2_client
        mock_ec2_client.__aexit__.return_value = None

        mock_session = Mock()
        mock_session.client.return_value = mock_ec2_client

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            regions = await client.get_accessible_regions()

        assert regions == ["us-east-1", "us-west-2", "eu-west-1"]
        mock_ec2_client.describe_regions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_accessible_regions_failure(self):
        """Test get_accessible_regions with exception"""
        mock_ec2_client = AsyncMock()
        mock_ec2_client.describe_regions.side_effect = ClientError(
            {"Error": {"Code": "UnauthorizedOperation"}}, "DescribeRegions"
        )
        mock_ec2_client.__aenter__.return_value = mock_ec2_client
        mock_ec2_client.__aexit__.return_value = None

        mock_session = Mock()
        mock_session.client.return_value = mock_ec2_client

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            regions = await client.get_accessible_regions()

        # Should return empty list on error
        assert regions == []

    @pytest.mark.asyncio
    async def test_get_accessible_regions_empty_response(self):
        """Test get_accessible_regions with empty response"""
        mock_ec2_client = AsyncMock()
        mock_ec2_client.describe_regions.return_value = {"Regions": []}
        mock_ec2_client.__aenter__.return_value = mock_ec2_client
        mock_ec2_client.__aexit__.return_value = None

        mock_session = Mock()
        mock_session.client.return_value = mock_ec2_client

        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_get_session', return_value=mock_session):
            regions = await client.get_accessible_regions()

        assert regions == []


class TestAsyncContextManager:
    """Test async context manager behavior"""

    @pytest.mark.asyncio
    async def test_context_manager_entry(self):
        """Test async context manager __aenter__"""
        client = AsyncAWSClient(region="us-east-1")

        result = await client.__aenter__()

        assert result == client

    @pytest.mark.asyncio
    async def test_context_manager_exit_normal(self):
        """Test async context manager __aexit__ with normal exit"""
        client = AsyncAWSClient(region="us-east-1")

        # Mock the close and cleanup methods
        with patch.object(client, 'close', new_callable=AsyncMock) as mock_close:
            with patch.object(client, '_close_connectors_sync') as mock_sync_close:
                result = await client.__aexit__(None, None, None)

        # Should call both cleanup methods
        mock_sync_close.assert_called_once()
        mock_close.assert_called_once()
        # Should return False (don't suppress exceptions)
        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager_exit_with_exception(self):
        """Test async context manager __aexit__ with exception"""
        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, 'close', new_callable=AsyncMock) as mock_close:
            with patch.object(client, '_close_connectors_sync') as mock_sync_close:
                result = await client.__aexit__(ValueError, ValueError("test"), None)

        # Should still call cleanup
        mock_sync_close.assert_called_once()
        mock_close.assert_called_once()
        # Should return False (don't suppress the ValueError)
        assert result is False


class TestCloseMethod:
    """Test close() method"""

    @pytest.mark.asyncio
    async def test_close_clears_clients(self):
        """Test close() clears client references"""
        client = AsyncAWSClient(region="us-east-1")

        # Set some fake clients
        client._ec2_client = Mock()
        client._pricing_client = Mock()
        client._session = Mock()

        with patch.object(client, '_close_connectors_sync'):
            await client.close()

        # Verify clients are cleared
        assert client._ec2_client is None
        assert client._pricing_client is None
        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_calls_sync_cleanup(self):
        """Test close() calls sync cleanup first"""
        client = AsyncAWSClient(region="us-east-1")

        with patch.object(client, '_close_connectors_sync') as mock_sync_close:
            await client.close()

        mock_sync_close.assert_called_once()


class TestConfigurationParameters:
    """Test that configuration parameters are properly used"""

    @pytest.mark.asyncio
    async def test_ec2_client_uses_connect_timeout(self):
        """Test EC2 client uses connect_timeout parameter"""
        mock_ec2_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1", connect_timeout=25)

        with patch.object(client, '_get_session', return_value=mock_session):
            async with client.get_ec2_client():
                pass

            # Verify connect_timeout in config
            call_args = mock_session.client.call_args
            config = call_args[1]["config"]
            assert config.connect_timeout == 25

    @pytest.mark.asyncio
    async def test_ec2_client_uses_read_timeout(self):
        """Test EC2 client uses read_timeout parameter"""
        mock_ec2_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1", read_timeout=150)

        with patch.object(client, '_get_session', return_value=mock_session):
            async with client.get_ec2_client():
                pass

            call_args = mock_session.client.call_args
            config = call_args[1]["config"]
            assert config.read_timeout == 150

    @pytest.mark.asyncio
    async def test_ec2_client_uses_max_pool_connections(self):
        """Test EC2 client uses max_pool_connections parameter"""
        mock_ec2_client = AsyncMock()
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__.return_value = mock_ec2_client

        mock_session = Mock()
        mock_session.client.return_value = mock_client_cm

        client = AsyncAWSClient(region="us-east-1", max_pool_connections=200)

        with patch.object(client, '_get_session', return_value=mock_session):
            async with client.get_ec2_client():
                pass

            call_args = mock_session.client.call_args
            config = call_args[1]["config"]
            assert config.max_pool_connections == 200
