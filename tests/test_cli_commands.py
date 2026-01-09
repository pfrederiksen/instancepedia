"""Tests for CLI commands"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from src.cli import commands
from src.models.instance_type import (
    InstanceType,
    VCpuInfo,
    MemoryInfo,
    NetworkInfo,
    ProcessorInfo,
    EbsInfo,
    PricingInfo
)


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
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = None
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


class TestCmdSearch:
    """Tests for cmd_search function (alias for cmd_list with search)"""

    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_search_success(self, mock_get_formatter, mock_get_client, mock_service_class, sample_instance_type):
        """Test successful search command"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
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
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_search(args)

        assert result == 0
        mock_formatter.format_instance_list.assert_called_once()


class TestCmdCacheStats:
    """Tests for cmd_cache_stats function"""

    @patch('src.cli.commands.get_pricing_cache')
    def test_cmd_cache_stats_table_format(self, mock_get_cache):
        """Test cache stats with table format"""
        mock_cache = Mock()
        mock_cache.cache_dir = "/tmp/cache"
        mock_cache.get_stats.return_value = {
            'total_entries': 100,
            'valid_entries': 80,
            'expired_entries': 20,
            'cache_size_bytes': 50000,
            'oldest_entry': '2024-01-01 00:00:00',
            'newest_entry': '2024-01-02 00:00:00'
        }
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.format = "table"
        args.debug = False

        result = commands.cmd_cache_stats(args)

        assert result == 0
        mock_cache.get_stats.assert_called_once()

    @patch('src.cli.commands.get_pricing_cache')
    def test_cmd_cache_stats_json_format(self, mock_get_cache):
        """Test cache stats with JSON format"""
        mock_cache = Mock()
        mock_cache.get_stats.return_value = {
            'total_entries': 100,
            'valid_entries': 80,
            'expired_entries': 20,
            'cache_size_bytes': 50000,
            'oldest_entry': None,
            'newest_entry': None
        }
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.format = "json"
        args.debug = False

        result = commands.cmd_cache_stats(args)

        assert result == 0

    @patch('src.cli.commands.get_pricing_cache')
    def test_cmd_cache_stats_error(self, mock_get_cache):
        """Test cache stats with error"""
        mock_get_cache.side_effect = Exception("Cache error")

        args = Mock()
        args.format = "table"
        args.debug = False

        result = commands.cmd_cache_stats(args)

        assert result == 1


class TestCmdCacheClear:
    """Tests for cmd_cache_clear function"""

    @patch('src.cli.commands.get_pricing_cache')
    def test_cmd_cache_clear_all_force(self, mock_get_cache):
        """Test clearing all cache with --force"""
        mock_cache = Mock()
        mock_cache.clear.return_value = 50
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.force = True
        args.quiet = False
        args.debug = False
        args.region = None
        args.instance_type = None

        result = commands.cmd_cache_clear(args)

        assert result == 0
        mock_cache.clear.assert_called_once_with(region=None, instance_type=None)

    @patch('src.cli.commands.get_pricing_cache')
    def test_cmd_cache_clear_by_region(self, mock_get_cache):
        """Test clearing cache by region"""
        mock_cache = Mock()
        mock_cache.clear.return_value = 25
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.force = True
        args.quiet = False
        args.debug = False
        args.region = "us-east-1"
        args.instance_type = None

        result = commands.cmd_cache_clear(args)

        assert result == 0
        mock_cache.clear.assert_called_once_with(region="us-east-1", instance_type=None)

    @patch('src.cli.commands.get_pricing_cache')
    def test_cmd_cache_clear_by_instance_type(self, mock_get_cache):
        """Test clearing cache by instance type"""
        mock_cache = Mock()
        mock_cache.clear.return_value = 5
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.force = True
        args.quiet = False
        args.debug = False
        args.region = None
        args.instance_type = "t3.micro"

        result = commands.cmd_cache_clear(args)

        assert result == 0
        mock_cache.clear.assert_called_once_with(region=None, instance_type="t3.micro")

    @patch('src.cli.commands.get_pricing_cache')
    @patch('builtins.input', return_value='n')
    def test_cmd_cache_clear_cancelled(self, mock_input, mock_get_cache):
        """Test cache clear cancelled by user"""
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.force = False
        args.quiet = False
        args.debug = False
        args.region = None
        args.instance_type = None

        result = commands.cmd_cache_clear(args)

        assert result == 0
        mock_cache.clear.assert_not_called()

    @patch('src.cli.commands.get_pricing_cache')
    @patch('builtins.input', return_value='y')
    def test_cmd_cache_clear_confirmed(self, mock_input, mock_get_cache):
        """Test cache clear confirmed by user"""
        mock_cache = Mock()
        mock_cache.clear.return_value = 10
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.force = False
        args.quiet = False
        args.debug = False
        args.region = None
        args.instance_type = None

        result = commands.cmd_cache_clear(args)

        assert result == 0
        mock_cache.clear.assert_called_once()

    @patch('src.cli.commands.get_pricing_cache')
    def test_cmd_cache_clear_error(self, mock_get_cache):
        """Test cache clear with error"""
        mock_cache = Mock()
        mock_cache.clear.side_effect = Exception("Clear error")
        mock_get_cache.return_value = mock_cache

        args = Mock()
        args.force = True
        args.quiet = False
        args.debug = False
        args.region = None
        args.instance_type = None

        result = commands.cmd_cache_clear(args)

        assert result == 1


class TestCmdCostEstimate:
    """Tests for cmd_cost_estimate function"""

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_cost_estimate_on_demand(self, mock_get_formatter, mock_get_client,
                                          mock_service_class, mock_pricing_class, sample_instance_type):
        """Test cost estimate with on-demand pricing"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        mock_pricing = Mock()
        mock_pricing.get_on_demand_price.return_value = 0.0104
        mock_pricing.get_spot_price.return_value = 0.0031
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.pricing_model = "on-demand"
        args.hours_per_month = 730
        args.months = 1

        result = commands.cmd_cost_estimate(args)

        assert result == 0

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_cost_estimate_spot(self, mock_get_formatter, mock_get_client,
                                     mock_service_class, mock_pricing_class, sample_instance_type):
        """Test cost estimate with spot pricing"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        mock_pricing = Mock()
        mock_pricing.get_on_demand_price.return_value = 0.0104
        mock_pricing.get_spot_price.return_value = 0.0031
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.pricing_model = "spot"
        args.hours_per_month = 730
        args.months = 12

        result = commands.cmd_cost_estimate(args)

        assert result == 0

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_cost_estimate_instance_not_found(self, mock_get_formatter, mock_get_client,
                                                   mock_service_class, mock_pricing_class):
        """Test cost estimate with instance not found"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = []
        mock_service_class.return_value = mock_service

        args = Mock()
        args.instance_type = "invalid.type"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.quiet = False
        args.debug = False

        result = commands.cmd_cost_estimate(args)

        assert result == 1

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_cost_estimate_pricing_unavailable(self, mock_get_client, mock_service_class,
                                                    mock_pricing_class, sample_instance_type):
        """Test cost estimate when pricing is unavailable"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        mock_pricing = Mock()
        mock_pricing.get_on_demand_price.return_value = None
        mock_pricing.get_spot_price.return_value = None
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.pricing_model = "on-demand"
        args.hours_per_month = 730
        args.months = 1

        result = commands.cmd_cost_estimate(args)

        assert result == 1


class TestCmdCompareRegions:
    """Tests for cmd_compare_regions function"""

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_compare_regions_success(self, mock_get_client, mock_service_class,
                                          mock_pricing_class, sample_instance_type):
        """Test successful region comparison"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        mock_pricing = Mock()
        mock_pricing.get_on_demand_price.return_value = 0.0104
        mock_pricing.get_spot_price.return_value = 0.0031
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.regions = "us-east-1,us-west-2"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False

        result = commands.cmd_compare_regions(args)

        assert result == 0

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_compare_regions_json_format(self, mock_get_client, mock_service_class,
                                              mock_pricing_class, sample_instance_type):
        """Test region comparison with JSON format"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        mock_pricing = Mock()
        mock_pricing.get_on_demand_price.return_value = 0.0104
        mock_pricing.get_spot_price.return_value = 0.0031
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.regions = "us-east-1"
        args.profile = None
        args.format = "json"
        args.output = None
        args.quiet = False
        args.debug = False

        result = commands.cmd_compare_regions(args)

        assert result == 0

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_compare_regions_instance_not_found(self, mock_get_client, mock_service_class, mock_pricing_class):
        """Test region comparison when instance not found in a region"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = []
        mock_service_class.return_value = mock_service

        args = Mock()
        args.instance_type = "invalid.type"
        args.regions = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False

        result = commands.cmd_compare_regions(args)

        # Should still succeed but show error in output
        assert result == 0


class TestCmdCompareFamily:
    """Tests for cmd_compare_family function"""

    @patch('src.cli.commands.Settings')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_compare_family_success(self, mock_get_formatter, mock_get_client,
                                         mock_service_class, mock_settings_class, sample_instance_type):
        """Test successful family comparison"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Create instances in the same family
        t3_micro = sample_instance_type
        t3_small = InstanceType(
            instance_type="t3.small",
            vcpu_info=VCpuInfo(default_vcpus=2),
            memory_info=MemoryInfo(size_in_mib=2048),
            network_info=NetworkInfo(
                network_performance="Up to 5 Gigabit",
                maximum_network_interfaces=3,
                maximum_ipv4_addresses_per_interface=4,
                maximum_ipv6_addresses_per_interface=4
            ),
            processor_info=ProcessorInfo(supported_architectures=["x86_64"]),
            ebs_info=EbsInfo(ebs_optimized_support="supported"),
            current_generation=True,
            burstable_performance_supported=True,
            hibernation_supported=False
        )

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [t3_micro, t3_small]
        mock_service_class.return_value = mock_service

        mock_settings = Mock()
        mock_settings.cli_pricing_concurrency = 5
        mock_settings_class.return_value = mock_settings

        args = Mock()
        args.family = "t3"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False
        args.sort_by = "name"

        result = commands.cmd_compare_family(args)

        assert result == 0

    @patch('src.cli.commands.Settings')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_compare_family_not_found(self, mock_get_client, mock_service_class, mock_settings_class):
        """Test family comparison with no instances found"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = []
        mock_service_class.return_value = mock_service

        args = Mock()
        args.family = "invalid"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.quiet = False
        args.debug = False
        args.include_pricing = False

        result = commands.cmd_compare_family(args)

        assert result == 1

    @patch('src.cli.commands.Settings')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_compare_family_json_format(self, mock_get_client, mock_service_class,
                                             mock_settings_class, sample_instance_type):
        """Test family comparison with JSON format"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        args = Mock()
        args.family = "t3"
        args.region = "us-east-1"
        args.profile = None
        args.format = "json"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False
        args.sort_by = "vcpu"

        result = commands.cmd_compare_family(args)

        assert result == 0


class TestCmdPresetsList:
    """Tests for cmd_presets_list function"""

    @patch('src.cli.commands.FilterPresetService')
    def test_cmd_presets_list_table_format(self, mock_service_class):
        """Test listing presets with table format"""
        mock_service = Mock()
        mock_preset = Mock()
        mock_preset.description = "Test preset"
        mock_service.get_all_presets.return_value = {"test-preset": mock_preset}
        mock_service_class.return_value = mock_service

        args = Mock()
        args.format = "table"

        result = commands.cmd_presets_list(args)

        assert result == 0
        mock_service.get_all_presets.assert_called_once()

    @patch('src.cli.commands.FilterPresetService')
    def test_cmd_presets_list_json_format(self, mock_service_class):
        """Test listing presets with JSON format"""
        mock_service = Mock()
        mock_preset = Mock()
        mock_preset.description = "Test preset"
        mock_preset.min_vcpu = 2
        mock_preset.max_vcpu = 8
        mock_preset.min_memory = 4
        mock_preset.max_memory = 32
        mock_preset.has_gpu = False
        mock_preset.current_generation_only = True
        mock_preset.burstable_only = False
        mock_preset.free_tier_only = False
        mock_preset.architecture = None
        mock_preset.instance_families = []
        mock_service.get_all_presets.return_value = {"web-server": mock_preset}
        mock_service_class.return_value = mock_service

        args = Mock()
        args.format = "json"

        result = commands.cmd_presets_list(args)

        assert result == 0

    @patch('src.cli.commands.FilterPresetService')
    def test_cmd_presets_list_error(self, mock_service_class):
        """Test listing presets with error"""
        mock_service_class.side_effect = Exception("Service error")

        args = Mock()
        args.format = "table"

        result = commands.cmd_presets_list(args)

        assert result == 1


class TestCmdPresetsApply:
    """Tests for cmd_presets_apply function"""

    @patch('src.cli.commands.Settings')
    @patch('src.cli.commands.FilterPresetService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_presets_apply_success(self, mock_get_formatter, mock_get_client,
                                        mock_service_class, mock_preset_service_class,
                                        mock_settings_class, sample_instance_type):
        """Test applying a preset successfully"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        mock_preset = Mock()
        mock_preset.name = "test-preset"
        mock_preset.description = "Test preset"
        mock_preset.min_vcpu = None
        mock_preset.max_vcpu = None
        mock_preset.min_memory = None
        mock_preset.max_memory = None
        mock_preset.has_gpu = None
        mock_preset.current_generation_only = False
        mock_preset.burstable_only = False
        mock_preset.free_tier_only = False
        mock_preset.architecture = None
        mock_preset.instance_families = []

        mock_preset_service = Mock()
        mock_preset_service.get_preset.return_value = mock_preset
        mock_preset_service_class.return_value = mock_preset_service

        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        args = Mock()
        args.preset_name = "test-preset"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False

        result = commands.cmd_presets_apply(args)

        assert result == 0

    @patch('src.cli.commands.FilterPresetService')
    def test_cmd_presets_apply_not_found(self, mock_preset_service_class):
        """Test applying a preset that doesn't exist"""
        mock_preset_service = Mock()
        mock_preset_service.get_preset.return_value = None
        mock_preset_service_class.return_value = mock_preset_service

        args = Mock()
        args.preset_name = "invalid-preset"
        args.quiet = False

        result = commands.cmd_presets_apply(args)

        assert result == 1

    @patch('src.cli.commands.Settings')
    @patch('src.cli.commands.FilterPresetService')
    @patch('src.cli.commands.InstanceService')
    @patch('src.cli.commands.get_aws_client')
    @patch('src.cli.commands.get_formatter')
    def test_cmd_presets_apply_with_filters(self, mock_get_formatter, mock_get_client,
                                             mock_service_class, mock_preset_service_class,
                                             mock_settings_class, sample_instance_type):
        """Test applying a preset with various filters"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [sample_instance_type]
        mock_service_class.return_value = mock_service

        mock_preset = Mock()
        mock_preset.name = "compute-preset"
        mock_preset.description = "Compute optimized"
        mock_preset.min_vcpu = 2
        mock_preset.max_vcpu = 16
        mock_preset.min_memory = 1
        mock_preset.max_memory = 64
        mock_preset.has_gpu = False
        mock_preset.current_generation_only = True
        mock_preset.burstable_only = True
        mock_preset.free_tier_only = False
        mock_preset.architecture = "x86_64"
        mock_preset.instance_families = ["t3"]

        mock_preset_service = Mock()
        mock_preset_service.get_preset.return_value = mock_preset
        mock_preset_service_class.return_value = mock_preset_service

        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        args = Mock()
        args.preset_name = "compute-preset"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.include_pricing = False

        result = commands.cmd_presets_apply(args)

        assert result == 0


class TestCmdSpotHistory:
    """Tests for cmd_spot_history function"""

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_spot_history_success(self, mock_get_client, mock_pricing_class):
        """Test successful spot history fetch"""
        from datetime import datetime
        from src.services.pricing_service import SpotPriceHistory

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # SpotPriceHistory has volatility_percentage, price_range, savings_vs_current as properties
        mock_history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=30,
            price_points=[
                (datetime(2024, 1, 1, 0, 0), 0.0030),
                (datetime(2024, 1, 2, 0, 0), 0.0031),
                (datetime(2024, 1, 3, 0, 0), 0.0029),
            ],
            current_price=0.0031,
            min_price=0.0029,
            max_price=0.0031,
            avg_price=0.0030,
            median_price=0.0030,
            std_dev=0.0001,
        )

        mock_pricing = Mock()
        mock_pricing.get_spot_price_history.return_value = mock_history
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.days = 30

        result = commands.cmd_spot_history(args)

        assert result == 0

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_spot_history_json_format(self, mock_get_client, mock_pricing_class):
        """Test spot history with JSON format"""
        from datetime import datetime
        from src.services.pricing_service import SpotPriceHistory

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # SpotPriceHistory has volatility_percentage, price_range, savings_vs_current as properties
        mock_history = SpotPriceHistory(
            instance_type="t3.micro",
            region="us-east-1",
            days=7,
            price_points=[
                (datetime(2024, 1, 1, 0, 0), 0.0030),
            ],
            current_price=0.0030,
            min_price=0.0030,
            max_price=0.0030,
            avg_price=0.0030,
            median_price=0.0030,
            std_dev=0.0,
        )

        mock_pricing = Mock()
        mock_pricing.get_spot_price_history.return_value = mock_history
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "json"
        args.output = None
        args.quiet = False
        args.debug = False
        args.days = 7

        result = commands.cmd_spot_history(args)

        assert result == 0

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_spot_history_no_data(self, mock_get_client, mock_pricing_class):
        """Test spot history when no data available"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_pricing = Mock()
        mock_pricing.get_spot_price_history.return_value = None
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.days = 30

        result = commands.cmd_spot_history(args)

        assert result == 1

    @patch('src.cli.commands.PricingService')
    @patch('src.cli.commands.get_aws_client')
    def test_cmd_spot_history_error(self, mock_get_client, mock_pricing_class):
        """Test spot history with error"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_pricing = Mock()
        mock_pricing.get_spot_price_history.side_effect = Exception("API error")
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.days = 30

        result = commands.cmd_spot_history(args)

        assert result == 1
