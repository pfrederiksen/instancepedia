"""Tests for CLI commands"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from src.cli import commands


class TestGetAWSClient:
    """Tests for get_aws_client function"""
    
    @patch('src.cli.commands.AWSClient')
    def test_get_aws_client_success(self, mock_aws_client_class):
        """Test successful AWS client creation"""
        mock_client = Mock()
        mock_aws_client_class.return_value = mock_client
        
        client = commands.get_aws_client("us-east-1", None)
        assert client == mock_client
        mock_aws_client_class.assert_called_once_with("us-east-1", None)
    
    @patch('src.cli.commands.AWSClient')
    def test_get_aws_client_error(self, mock_aws_client_class):
        """Test AWS client creation with error"""
        mock_aws_client_class.side_effect = ValueError("AWS credentials not found")
        
        with pytest.raises(SystemExit):
            commands.get_aws_client("us-east-1", None)


class TestCmdList:
    """Tests for cmd_list function"""
    
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_list_success(self, mock_get_formatter, mock_get_client, mock_service_class, sample_instance_type):
        """Test successful list command"""
        # Setup mocks
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service
        
        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter
        
        # Create args
        args = Mock()
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.include_pricing = False
        
        # Run command
        result = commands.cmd_list(args)
        
        assert result == 0
        mock_service.get_instance_types.assert_called_once_with(fetch_pricing=False)
        mock_formatter.format_instance_list.assert_called_once()
    
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_list_with_search(self, mock_get_formatter, mock_get_client, mock_service_class, sample_instance_type, sample_instance_type_no_pricing):
        """Test list command with search filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            sample_instance_type,
            sample_instance_type_no_pricing
        ]
        mock_service_class.return_value = mock_service
        
        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter
        
        args = Mock()
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.search = "t3"
        args.free_tier_only = False
        args.family = None
        args.include_pricing = False
        
        result = commands.cmd_list(args)
        
        assert result == 0
        # Should filter to only t3.micro
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "t3.micro"
    
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_list_error(self, mock_get_client, mock_service_class):
        """Test list command with error"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.side_effect = Exception("API Error")
        mock_service_class.return_value = mock_service
        
        args = Mock()
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.include_pricing = False
        
        result = commands.cmd_list(args)
        assert result == 1


class TestCmdShow:
    """Tests for cmd_show function"""
    
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_show_success(self, mock_get_formatter, mock_get_client, mock_service_class, sample_instance_type):
        """Test successful show command"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service
        
        mock_formatter = Mock()
        mock_formatter.format_instance_detail.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter
        
        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False
        
        result = commands.cmd_show(args)
        
        assert result == 0
        mock_formatter.format_instance_detail.assert_called_once()
    
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_show_not_found(self, mock_get_formatter, mock_get_client, mock_service_class, sample_instance_type):
        """Test show command with instance not found"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service
        
        args = Mock()
        args.instance_type = "invalid.type"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False
        
        result = commands.cmd_show(args)
        assert result == 1


class TestCmdPricing:
    """Tests for cmd_pricing function"""
    
    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_pricing_success(self, mock_get_formatter, mock_get_client, 
                                  mock_service_class, mock_pricing_service_class, sample_instance_type):
        """Test successful pricing command"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service
        
        mock_pricing_service = Mock()
        mock_pricing_service.get_on_demand_price.return_value = 0.0104
        mock_pricing_service.get_spot_price.return_value = 0.0031
        mock_pricing_service_class.return_value = mock_pricing_service
        
        mock_formatter = Mock()
        mock_formatter.format_pricing.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter
        
        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        
        result = commands.cmd_pricing(args)
        
        assert result == 0
        mock_formatter.format_pricing.assert_called_once()


class TestCmdRegions:
    """Tests for cmd_regions function"""
    
    @patch('src.cli.commands.Settings')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_regions_success(self, mock_get_formatter, mock_get_client, mock_settings_class):
        """Test successful regions command"""
        mock_client = Mock()
        mock_client.get_accessible_regions.return_value = ["us-east-1", "us-west-2"]
        mock_get_client.return_value = mock_client
        
        mock_settings = Mock()
        mock_settings_class.return_value = mock_settings
        
        mock_formatter = Mock()
        mock_formatter.format_regions.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter
        
        args = Mock()
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        
        result = commands.cmd_regions(args)
        
        assert result == 0
        mock_formatter.format_regions.assert_called_once()


class TestCmdCompare:
    """Tests for cmd_compare function"""
    
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_compare_success(self, mock_get_formatter, mock_get_client, mock_service_class, sample_instance_type, sample_instance_type_no_pricing):
        """Test successful compare command"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            sample_instance_type,
            sample_instance_type_no_pricing
        ]
        mock_service_class.return_value = mock_service
        
        mock_formatter = Mock()
        mock_formatter.format_comparison.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter
        
        args = Mock()
        args.instance_type1 = "t3.micro"
        args.instance_type2 = "m5.large"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False
        
        result = commands.cmd_compare(args)
        
        assert result == 0
        mock_formatter.format_comparison.assert_called_once()
    
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_compare_not_found(self, mock_get_client, mock_service_class, sample_instance_type):
        """Test compare command with instance not found"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service
        
        args = Mock()
        args.instance_type1 = "t3.micro"
        args.instance_type2 = "invalid.type"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False
        
        result = commands.cmd_compare(args)
        assert result == 1


class TestRunCLI:
    """Tests for run_cli function"""
    
    def test_run_cli_with_func(self):
        """Test run_cli with function in args"""
        args = Mock()
        args.func = Mock(return_value=0)
        
        result = commands.run_cli(args)
        
        assert result == 0
        args.func.assert_called_once_with(args)
    
    def test_run_cli_without_func(self):
        """Test run_cli without function in args"""
        args = Mock()
        del args.func
        
        result = commands.run_cli(args)
        assert result == 1
