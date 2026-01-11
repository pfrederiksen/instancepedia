"""Tests for AWSClient"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

from src.services.aws_client import AWSClient
from src.exceptions import (
    AWSCredentialsError,
    AWSConnectionError,
    AWSRegionError
)


class TestAWSClientInit:
    """Test AWSClient initialization"""

    def test_init_basic(self):
        """Test basic initialization with region only"""
        client = AWSClient(region="us-east-1")

        assert client.region == "us-east-1"
        assert client.profile is None
        assert client.connect_timeout == 10
        assert client.read_timeout == 60
        assert client.pricing_timeout == 90
        assert client._ec2_client is None
        assert client._pricing_client is None

    def test_init_with_profile(self):
        """Test initialization with AWS profile"""
        client = AWSClient(region="us-west-2", profile="my-profile")

        assert client.region == "us-west-2"
        assert client.profile == "my-profile"

    def test_init_with_custom_timeouts(self):
        """Test initialization with custom timeout values"""
        client = AWSClient(
            region="eu-west-1",
            connect_timeout=20,
            read_timeout=120,
            pricing_timeout=180
        )

        assert client.connect_timeout == 20
        assert client.read_timeout == 120
        assert client.pricing_timeout == 180

    @patch('src.services.aws_client.AWSClient._validate_region')
    def test_init_with_validate_region_success(self, mock_validate):
        """Test initialization with validate_region=True (success)"""
        # Mock successful validation
        mock_validate.return_value = None

        client = AWSClient(region="us-east-1", validate_region=True)

        # Verify validation was called
        mock_validate.assert_called_once()
        assert client.region == "us-east-1"

    @patch('src.services.aws_client.AWSClient._validate_region')
    def test_init_with_validate_region_failure(self, mock_validate):
        """Test initialization with validate_region=True (failure)"""
        # Mock validation failure
        mock_validate.side_effect = AWSRegionError("Invalid region")

        with pytest.raises(AWSRegionError, match="Invalid region"):
            AWSClient(region="invalid-region", validate_region=True)


class TestSessionCreation:
    """Test boto3 session creation"""

    @patch('src.services.aws_client.boto3.Session')
    def test_get_session_without_profile(self, mock_session_class):
        """Test session creation without profile"""
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance

        client = AWSClient(region="us-east-1")
        session = client._get_session()

        # Verify Session() was called without profile_name
        mock_session_class.assert_called_once_with()
        assert session == mock_session_instance

    @patch('src.services.aws_client.boto3.Session')
    def test_get_session_with_profile(self, mock_session_class):
        """Test session creation with profile"""
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance

        client = AWSClient(region="us-east-1", profile="my-profile")
        session = client._get_session()

        # Verify Session() was called with profile_name
        mock_session_class.assert_called_once_with(profile_name="my-profile")
        assert session == mock_session_instance


class TestRegionValidation:
    """Test region validation functionality"""

    @patch('src.services.aws_client.AWSClient.get_accessible_regions')
    def test_validate_region_success(self, mock_get_regions):
        """Test successful region validation"""
        # Mock accessible regions
        mock_get_regions.return_value = ["us-east-1", "us-west-2", "eu-west-1"]

        client = AWSClient(region="us-east-1")
        # Should not raise any exception
        client._validate_region()

        mock_get_regions.assert_called_once()

    @patch('src.services.aws_client.AWSClient.get_accessible_regions')
    def test_validate_region_not_accessible(self, mock_get_regions):
        """Test region validation when region is not accessible"""
        # Mock accessible regions (doesn't include target region)
        mock_get_regions.return_value = ["us-east-1", "us-west-2"]

        client = AWSClient(region="ap-south-1")

        with pytest.raises(AWSRegionError, match="not accessible"):
            client._validate_region()

    @patch('src.services.aws_client.AWSClient.get_accessible_regions')
    def test_validate_region_credentials_error(self, mock_get_regions):
        """Test region validation when credentials are missing"""
        # Mock credentials error
        mock_get_regions.side_effect = AWSCredentialsError("No credentials")

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSCredentialsError, match="No credentials"):
            client._validate_region()

    @patch('src.services.aws_client.AWSClient.get_accessible_regions')
    def test_validate_region_connection_error(self, mock_get_regions):
        """Test region validation when connection fails"""
        # Mock connection error
        mock_get_regions.side_effect = AWSConnectionError("Connection failed")

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSConnectionError, match="Connection failed"):
            client._validate_region()

    @patch('src.services.aws_client.AWSClient.get_accessible_regions')
    def test_validate_region_unexpected_exception(self, mock_get_regions):
        """Test region validation with unexpected exception"""
        # Mock unexpected exception
        mock_get_regions.side_effect = ValueError("Unexpected error")

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSConnectionError, match="Failed to validate region"):
            client._validate_region()


class TestEC2ClientProperty:
    """Test EC2 client lazy loading and caching"""

    @patch('src.services.aws_client.boto3.Session')
    def test_ec2_client_lazy_creation(self, mock_session_class):
        """Test EC2 client is created on first access"""
        # Setup mock session and client
        mock_session = Mock()
        mock_ec2_client = Mock()
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        # Initially None
        assert client._ec2_client is None

        # Access creates client
        ec2 = client.ec2_client

        assert ec2 == mock_ec2_client
        assert client._ec2_client == mock_ec2_client
        mock_session.client.assert_called_once()

    @patch('src.services.aws_client.boto3.Session')
    def test_ec2_client_caching(self, mock_session_class):
        """Test EC2 client is cached after first creation"""
        # Setup mock session and client
        mock_session = Mock()
        mock_ec2_client = Mock()
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        # First access
        ec2_1 = client.ec2_client
        # Second access
        ec2_2 = client.ec2_client

        # Should be same instance
        assert ec2_1 == ec2_2
        # client() should only be called once (cached)
        mock_session.client.assert_called_once()

    @patch('src.services.aws_client.boto3.Session')
    def test_ec2_client_no_credentials_error(self, mock_session_class):
        """Test EC2 client handles missing credentials"""
        # Setup mock session that raises NoCredentialsError
        mock_session = Mock()
        mock_session.client.side_effect = NoCredentialsError()
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSCredentialsError, match="AWS credentials not found"):
            _ = client.ec2_client

    @patch('src.services.aws_client.boto3.Session')
    def test_ec2_client_invalid_region_error(self, mock_session_class):
        """Test EC2 client handles invalid region"""
        # Setup mock session that raises ClientError with InvalidRegionName
        mock_session = Mock()
        error_response = {"Error": {"Code": "InvalidRegionName"}}
        mock_session.client.side_effect = ClientError(error_response, "CreateClient")
        mock_session_class.return_value = mock_session

        client = AWSClient(region="invalid-region")

        with pytest.raises(AWSRegionError, match="Cannot access region"):
            _ = client.ec2_client

    @patch('src.services.aws_client.boto3.Session')
    def test_ec2_client_boto_core_error(self, mock_session_class):
        """Test EC2 client handles BotoCoreError"""
        # Setup mock session that raises BotoCoreError
        mock_session = Mock()
        mock_session.client.side_effect = BotoCoreError()
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSConnectionError, match="Failed to create EC2 client"):
            _ = client.ec2_client


class TestPricingClientProperty:
    """Test Pricing client lazy loading and caching"""

    @patch('src.services.aws_client.boto3.Session')
    def test_pricing_client_lazy_creation(self, mock_session_class):
        """Test Pricing client is created on first access"""
        # Setup mock session and client
        mock_session = Mock()
        mock_pricing_client = Mock()
        mock_session.client.return_value = mock_pricing_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-west-2")

        # Initially None
        assert client._pricing_client is None

        # Access creates client
        pricing = client.pricing_client

        assert pricing == mock_pricing_client
        assert client._pricing_client == mock_pricing_client
        # Verify pricing client is ALWAYS created in us-east-1
        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args[1]
        assert call_kwargs["region_name"] == "us-east-1"

    @patch('src.services.aws_client.boto3.Session')
    def test_pricing_client_caching(self, mock_session_class):
        """Test Pricing client is cached after first creation"""
        # Setup mock session and client
        mock_session = Mock()
        mock_pricing_client = Mock()
        mock_session.client.return_value = mock_pricing_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        # First access
        pricing_1 = client.pricing_client
        # Second access
        pricing_2 = client.pricing_client

        # Should be same instance
        assert pricing_1 == pricing_2
        # client() should only be called once (cached)
        mock_session.client.assert_called_once()

    @patch('src.services.aws_client.boto3.Session')
    def test_pricing_client_no_credentials_error(self, mock_session_class):
        """Test Pricing client handles missing credentials"""
        # Setup mock session that raises NoCredentialsError
        mock_session = Mock()
        mock_session.client.side_effect = NoCredentialsError()
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSCredentialsError, match="AWS credentials not found"):
            _ = client.pricing_client

    @patch('src.services.aws_client.boto3.Session')
    def test_pricing_client_boto_core_error(self, mock_session_class):
        """Test Pricing client handles BotoCoreError"""
        # Setup mock session that raises BotoCoreError
        mock_session = Mock()
        mock_session.client.side_effect = BotoCoreError()
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSConnectionError, match="Failed to create Pricing API client"):
            _ = client.pricing_client


class TestConnectionTest:
    """Test AWS connection testing functionality"""

    @patch('src.services.aws_client.boto3.Session')
    def test_connection_success(self, mock_session_class):
        """Test successful connection test"""
        # Setup mock session and EC2 client
        mock_session = Mock()
        mock_ec2_client = Mock()
        mock_ec2_client.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")
        result = client.test_connection()

        assert result is True
        mock_ec2_client.describe_regions.assert_called_once_with(MaxResults=1)

    @patch('src.services.aws_client.boto3.Session')
    def test_connection_failure_client_error(self, mock_session_class):
        """Test connection test with ClientError"""
        # Setup mock session and EC2 client that raises error
        mock_session = Mock()
        mock_ec2_client = Mock()
        error_response = {"Error": {"Code": "UnauthorizedOperation"}}
        mock_ec2_client.describe_regions.side_effect = ClientError(error_response, "DescribeRegions")
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")
        result = client.test_connection()

        assert result is False

    @patch('src.services.aws_client.boto3.Session')
    def test_connection_failure_botocore_error(self, mock_session_class):
        """Test connection test with BotoCoreError"""
        # Setup mock session and EC2 client that raises error
        mock_session = Mock()
        mock_ec2_client = Mock()
        mock_ec2_client.describe_regions.side_effect = BotoCoreError()
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")
        result = client.test_connection()

        assert result is False


class TestGetAccessibleRegions:
    """Test fetching list of accessible AWS regions"""

    @patch('src.services.aws_client.boto3.Session')
    def test_get_accessible_regions_success(self, mock_session_class):
        """Test successful fetching of accessible regions"""
        # Setup mock session and EC2 client
        mock_session = Mock()
        mock_ec2_client = Mock()
        mock_ec2_client.describe_regions.return_value = {
            "Regions": [
                {"RegionName": "us-east-1"},
                {"RegionName": "us-west-2"},
                {"RegionName": "eu-west-1"}
            ]
        }
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")
        regions = client.get_accessible_regions()

        assert regions == ["us-east-1", "us-west-2", "eu-west-1"]
        # Verify the EC2 client is created in us-east-1 (standard region)
        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args[1]
        assert call_kwargs["region_name"] == "us-east-1"

    @patch('src.services.aws_client.boto3.Session')
    def test_get_accessible_regions_no_credentials(self, mock_session_class):
        """Test get_accessible_regions with missing credentials"""
        # Setup mock session that raises NoCredentialsError
        mock_session = Mock()
        mock_session.client.side_effect = NoCredentialsError()
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSCredentialsError, match="AWS credentials not found"):
            client.get_accessible_regions()

    @patch('src.services.aws_client.boto3.Session')
    def test_get_accessible_regions_client_error(self, mock_session_class):
        """Test get_accessible_regions with ClientError"""
        # Setup mock session and EC2 client that raises ClientError
        mock_session = Mock()
        mock_ec2_client = Mock()
        error_response = {"Error": {"Code": "UnauthorizedOperation"}}
        mock_ec2_client.describe_regions.side_effect = ClientError(error_response, "DescribeRegions")
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSConnectionError, match="Failed to get accessible regions"):
            client.get_accessible_regions()

    @patch('src.services.aws_client.boto3.Session')
    def test_get_accessible_regions_botocore_error(self, mock_session_class):
        """Test get_accessible_regions with BotoCoreError"""
        # Setup mock session and EC2 client that raises BotoCoreError
        mock_session = Mock()
        mock_ec2_client = Mock()
        mock_ec2_client.describe_regions.side_effect = BotoCoreError()
        mock_session.client.return_value = mock_ec2_client
        mock_session_class.return_value = mock_session

        client = AWSClient(region="us-east-1")

        with pytest.raises(AWSConnectionError, match="Failed to get accessible regions"):
            client.get_accessible_regions()
