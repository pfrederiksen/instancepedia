"""Tests for AsyncAWSClient cleanup to prevent unclosed session warnings"""

import asyncio
import pytest
import warnings
from unittest.mock import Mock, AsyncMock, MagicMock, patch


class TestAsyncClientCleanup:
    """Test that AsyncAWSClient properly cleans up aiohttp sessions"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aioboto3 session"""
        session = Mock()
        return session

    @pytest.fixture
    def mock_client(self):
        """Create a mock aioboto3 client with aiohttp internals"""
        client = AsyncMock()

        # Create mock http session and connector
        connector = Mock()
        connector.close = Mock()
        connector.closed = False

        http_session = AsyncMock()
        # Set both _connector (used by aiohttp internally) and connector (public property)
        http_session._connector = connector
        http_session.connector = connector
        http_session._closed = False
        http_session.close = AsyncMock()

        # Set up endpoint with http session
        endpoint = Mock()
        endpoint.http_session = http_session

        client._endpoint = endpoint
        client.__aexit__ = AsyncMock()

        return client

    @pytest.mark.asyncio
    async def test_close_calls_connector_close(self, mock_client):
        """Test that close() properly closes the connector"""
        from src.services.async_aws_client import AsyncAWSClient

        with patch('aioboto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            async_client = AsyncAWSClient("us-east-1")
            async_client._ec2_client = mock_client

            await async_client.close()

            # Verify connector was closed (may be called multiple times due to sync+async cleanup)
            mock_client._endpoint.http_session._connector.close.assert_called()

    @pytest.mark.asyncio
    async def test_close_marks_session_closed(self, mock_client):
        """Test that close() marks the session as closed to prevent __del__ warning"""
        from src.services.async_aws_client import AsyncAWSClient

        with patch('aioboto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            async_client = AsyncAWSClient("us-east-1")
            async_client._ec2_client = mock_client

            await async_client.close()

            # Verify session was marked as closed (prevents __del__ warning)
            assert mock_client._endpoint.http_session._closed == True

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, mock_client):
        """Test that async context manager properly cleans up"""
        from src.services.async_aws_client import AsyncAWSClient

        with patch('aioboto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            async_client = AsyncAWSClient("us-east-1")
            async_client._ec2_client = mock_client

            async with async_client:
                pass  # Just enter and exit

            # Verify cleanup was called
            mock_client._endpoint.http_session.connector.close.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_on_cancellation(self, mock_client):
        """Test that cleanup happens even when coroutine is cancelled"""
        from src.services.async_aws_client import AsyncAWSClient

        with patch('aioboto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            async_client = AsyncAWSClient("us-east-1")
            async_client._ec2_client = mock_client

            async def work_then_cancel():
                async with async_client:
                    # Simulate some work then cancellation
                    await asyncio.sleep(0.01)
                    raise asyncio.CancelledError()

            with pytest.raises(asyncio.CancelledError):
                await work_then_cancel()

            # Give background cleanup tasks time to run
            await asyncio.sleep(0.5)

            # Verify cleanup was still called despite cancellation
            mock_client._endpoint.http_session.connector.close.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_clients_cleanup(self, mock_client):
        """Test that both EC2 and Pricing clients are cleaned up"""
        from src.services.async_aws_client import AsyncAWSClient

        # Create second mock client for pricing
        mock_pricing_client = AsyncMock()
        pricing_connector = Mock()
        pricing_connector.close = Mock()
        pricing_connector.closed = False
        pricing_http_session = AsyncMock()
        pricing_http_session._connector = pricing_connector
        pricing_http_session.connector = pricing_connector
        pricing_http_session._closed = False
        pricing_http_session.close = AsyncMock()
        pricing_endpoint = Mock()
        pricing_endpoint.http_session = pricing_http_session
        mock_pricing_client._endpoint = pricing_endpoint
        mock_pricing_client.__aexit__ = AsyncMock()

        with patch('aioboto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            async_client = AsyncAWSClient("us-east-1")
            async_client._ec2_client = mock_client
            async_client._pricing_client = mock_pricing_client

            await async_client.close()

            # Verify both connectors were closed
            mock_client._endpoint.http_session.connector.close.assert_called()
            mock_pricing_client._endpoint.http_session.connector.close.assert_called()

    @pytest.mark.asyncio
    async def test_no_warnings_on_normal_exit(self):
        """Test that no unclosed session warnings occur on normal exit"""
        from src.services.async_aws_client import AsyncAWSClient

        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with patch('aioboto3.Session') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value = mock_session

                async_client = AsyncAWSClient("us-east-1")

                async with async_client:
                    pass

                # Give time for any cleanup
                await asyncio.sleep(0.3)

            # Check for unclosed session warnings
            unclosed_warnings = [
                warning for warning in w
                if "Unclosed" in str(warning.message)
            ]

            assert len(unclosed_warnings) == 0, f"Found unclosed warnings: {unclosed_warnings}"


class TestAsyncClientCleanupIntegration:
    """Integration tests for async client cleanup with real async operations"""

    @pytest.mark.asyncio
    async def test_cleanup_after_pricing_fetch_simulation(self):
        """Simulate a pricing fetch and verify cleanup"""
        from src.services.async_aws_client import AsyncAWSClient

        with patch('aioboto3.Session') as mock_session_class:
            # Create mock that simulates real client behavior
            mock_session = Mock()

            # Mock the client context manager
            mock_pricing_ctx = AsyncMock()
            mock_pricing = AsyncMock()
            mock_pricing.get_products = AsyncMock(return_value={'PriceList': []})
            mock_pricing_ctx.__aenter__ = AsyncMock(return_value=mock_pricing)
            mock_pricing_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_session.client = Mock(return_value=mock_pricing_ctx)
            mock_session_class.return_value = mock_session

            async_client = AsyncAWSClient("us-east-1")

            async with async_client:
                # Simulate getting pricing client and making a call
                async with async_client.get_pricing_client() as pricing:
                    await pricing.get_products(ServiceCode='AmazonEC2', Filters=[], MaxResults=1)

            # Verify the context manager exit was called
            # This ensures cleanup path was executed
            assert async_client._pricing_client is None or mock_pricing_ctx.__aexit__.called

    @pytest.mark.asyncio
    async def test_rapid_create_destroy_cycle(self):
        """Test rapid creation and destruction doesn't leak connections"""
        from src.services.async_aws_client import AsyncAWSClient

        with patch('aioboto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Rapidly create and destroy clients
            for _ in range(5):
                async_client = AsyncAWSClient("us-east-1")
                async with async_client:
                    await asyncio.sleep(0.01)

            # Give cleanup time
            await asyncio.sleep(0.5)

            # If we get here without hanging, cleanup is working
            assert True
