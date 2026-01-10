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
    
    @patch('src.cli.commands.base.AWSClient')
    def test_get_aws_client_success(self, mock_aws_client_class):
        """Test successful AWS client creation"""
        mock_client = Mock()
        mock_aws_client_class.return_value = mock_client
        
        client = commands.get_aws_client("us-east-1", None)
        assert client == mock_client
        mock_aws_client_class.assert_called_once_with("us-east-1", None)
    
    @patch('src.cli.commands.base.AWSClient')
    def test_get_aws_client_error(self, mock_aws_client_class):
        """Test AWS client creation with error"""
        mock_aws_client_class.side_effect = ValueError("AWS credentials not found")
        
        with pytest.raises(SystemExit):
            commands.get_aws_client("us-east-1", None)


class TestStatusHelper:
    """Tests for status() helper function"""

    def test_status_prints_to_stderr_when_not_quiet(self, capsys):
        """Test status prints message to stderr when quiet=False"""
        from src.cli.commands.base import status
        status("Test message", quiet=False)
        captured = capsys.readouterr()
        assert captured.err == "Test message\n"
        assert captured.out == ""

    def test_status_silent_when_quiet(self, capsys):
        """Test status prints nothing when quiet=True"""
        from src.cli.commands.base import status
        status("Test message", quiet=True)
        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out == ""

    def test_status_default_not_quiet(self, capsys):
        """Test status defaults to quiet=False"""
        from src.cli.commands.base import status
        status("Default test")
        captured = capsys.readouterr()
        assert captured.err == "Default test\n"


class TestProgressHelper:
    """Tests for progress() helper function"""

    def test_progress_prints_to_stderr_when_not_quiet(self, capsys):
        """Test progress prints formatted message to stderr when quiet=False"""
        from src.cli.commands.base import progress
        progress(5, 10, "items", quiet=False)
        captured = capsys.readouterr()
        assert "5/10 items" in captured.err
        assert captured.out == ""

    def test_progress_silent_when_quiet(self, capsys):
        """Test progress prints nothing when quiet=True"""
        from src.cli.commands.base import progress
        progress(5, 10, "items", quiet=True)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_progress_custom_item_type(self, capsys):
        """Test progress with custom item type"""
        from src.cli.commands.base import progress
        progress(3, 7, "instances", quiet=False)
        captured = capsys.readouterr()
        assert "3/7 instances" in captured.err


class TestWriteOutputHelper:
    """Tests for write_output() helper function"""

    def test_write_output_to_stdout(self, capsys):
        """Test write_output writes to stdout when no path given"""
        from src.cli.commands.base import write_output
        write_output("Test output", None, quiet=False)
        captured = capsys.readouterr()
        assert captured.out == "Test output\n"

    def test_write_output_to_file(self, tmp_path, capsys):
        """Test write_output writes to file when path given"""
        from src.cli.commands.base import write_output
        output_file = tmp_path / "output.txt"
        write_output("File content", str(output_file), quiet=False)

        # Check file was written
        assert output_file.read_text() == "File content"

        # Check status message
        captured = capsys.readouterr()
        assert "Output written to" in captured.err

    def test_write_output_to_file_quiet(self, tmp_path, capsys):
        """Test write_output suppresses status message when quiet"""
        from src.cli.commands.base import write_output
        output_file = tmp_path / "output.txt"
        write_output("File content", str(output_file), quiet=True)

        # Check file was written
        assert output_file.read_text() == "File content"

        # Check no status message
        captured = capsys.readouterr()
        assert captured.err == ""


class TestSafeWriteFile:
    """Tests for safe_write_file function"""

    def test_safe_write_file_basic(self, tmp_path):
        """Test basic file writing"""
        from src.cli.commands.base import safe_write_file
        output_file = tmp_path / "test.txt"
        safe_write_file(str(output_file), "Test content")

        assert output_file.read_text() == "Test content"

    def test_safe_write_file_creates_parent_dirs(self, tmp_path):
        """Test that parent directories are created"""
        from src.cli.commands.base import safe_write_file
        output_file = tmp_path / "nested" / "dir" / "test.txt"
        safe_write_file(str(output_file), "Test content")

        assert output_file.exists()
        assert output_file.read_text() == "Test content"

    def test_safe_write_file_no_create_dirs(self, tmp_path):
        """Test that missing parent dirs raise error when create_dirs=False"""
        from src.cli.commands.base import safe_write_file
        import pytest

        output_file = tmp_path / "nonexistent" / "test.txt"
        with pytest.raises(IOError):
            safe_write_file(str(output_file), "Test content", create_dirs=False)

    def test_safe_write_file_overwrites_existing(self, tmp_path):
        """Test that existing files are overwritten"""
        from src.cli.commands.base import safe_write_file
        output_file = tmp_path / "test.txt"
        output_file.write_text("Original content")

        safe_write_file(str(output_file), "New content")

        assert output_file.read_text() == "New content"


class TestCmdList:
    """Tests for cmd_list function"""
    
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
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
    
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
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
    
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
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

    @patch('src.cli.commands.instance_commands.get_instance_by_name')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_cmd_show_success(self, mock_get_formatter, mock_get_client, mock_get_instance, sample_instance_type):
        """Test successful show command"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = sample_instance_type

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

    @patch('src.cli.commands.instance_commands.get_instance_by_name')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_cmd_show_not_found(self, mock_get_formatter, mock_get_client, mock_get_instance, sample_instance_type):
        """Test show command with instance not found"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = None  # Instance not found

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

    @patch('src.cli.commands.pricing_commands.fetch_instance_pricing')
    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    @patch('src.cli.commands.pricing_commands.get_formatter')
    def test_cmd_pricing_success(self, mock_get_formatter, mock_get_client,
                                  mock_get_instance, mock_pricing_service_class,
                                  mock_fetch_pricing, sample_instance_type):
        """Test successful pricing command"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = sample_instance_type

        mock_pricing_service = Mock()
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
    
    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
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

    @patch('src.cli.commands.instance_commands.get_instances_by_names')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_cmd_compare_success(self, mock_get_formatter, mock_get_client, mock_get_instances, sample_instance_type, sample_instance_type_no_pricing):
        """Test successful compare command"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instances.return_value = [sample_instance_type, sample_instance_type_no_pricing]

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

    @patch('src.cli.commands.instance_commands.get_instances_by_names')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    def test_cmd_compare_not_found(self, mock_get_client, mock_get_instances, sample_instance_type):
        """Test compare command with instance not found"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instances.return_value = [sample_instance_type, None]  # Second instance not found

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

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.cache_commands.get_pricing_cache')
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

    @patch('src.cli.commands.pricing_commands.fetch_instance_pricing')
    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    def test_cmd_cost_estimate_on_demand(self, mock_get_client, mock_get_instance,
                                          mock_pricing_class, mock_fetch_pricing, sample_instance_type):
        """Test cost estimate with on-demand pricing"""
        from src.models.instance_type import PricingInfo

        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = sample_instance_type

        mock_pricing = Mock()
        mock_pricing_class.return_value = mock_pricing

        # Mock fetch_instance_pricing to set pricing on the instance
        def set_pricing(pricing_service, instance_type, region):
            return PricingInfo(on_demand_price=0.0104, spot_price=0.0031)
        mock_fetch_pricing.side_effect = set_pricing

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

    @patch('src.cli.commands.pricing_commands.fetch_instance_pricing')
    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    def test_cmd_cost_estimate_spot(self, mock_get_client, mock_get_instance,
                                     mock_pricing_class, mock_fetch_pricing, sample_instance_type):
        """Test cost estimate with spot pricing"""
        from src.models.instance_type import PricingInfo

        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = sample_instance_type

        mock_pricing = Mock()
        mock_pricing_class.return_value = mock_pricing

        def set_pricing(pricing_service, instance_type, region):
            return PricingInfo(on_demand_price=0.0104, spot_price=0.0031)
        mock_fetch_pricing.side_effect = set_pricing

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

    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    def test_cmd_cost_estimate_instance_not_found(self, mock_get_client, mock_get_instance):
        """Test cost estimate with instance not found"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = None  # Instance not found

        args = Mock()
        args.instance_type = "invalid.type"
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.quiet = False
        args.debug = False

        result = commands.cmd_cost_estimate(args)

        assert result == 1

    @patch('src.cli.commands.pricing_commands.fetch_instance_pricing')
    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_instance_by_name')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    def test_cmd_cost_estimate_pricing_unavailable(self, mock_get_client, mock_get_instance,
                                                    mock_pricing_class, mock_fetch_pricing, sample_instance_type):
        """Test cost estimate when pricing is unavailable"""
        from src.models.instance_type import PricingInfo

        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_instance.return_value = sample_instance_type

        mock_pricing = Mock()
        mock_pricing_class.return_value = mock_pricing

        def set_pricing(pricing_service, instance_type, region):
            return PricingInfo(on_demand_price=None, spot_price=None)
        mock_fetch_pricing.side_effect = set_pricing

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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.InstanceService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.InstanceService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.InstanceService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
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

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
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

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
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

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
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

    @patch('src.cli.commands.preset_commands.FilterPresetService')
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

    @patch('src.cli.commands.preset_commands.FilterPresetService')
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

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_list_error(self, mock_service_class):
        """Test listing presets with error"""
        mock_service_class.side_effect = Exception("Service error")

        args = Mock()
        args.format = "table"

        result = commands.cmd_presets_list(args)

        assert result == 1


class TestCmdPresetsApply:
    """Tests for cmd_presets_apply function"""

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.preset_commands.FilterPresetService')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
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

    @patch('src.cli.commands.preset_commands.FilterPresetService')
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

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.preset_commands.FilterPresetService')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
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

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    def test_cmd_spot_history_metal_instance_error_message(self, mock_get_client, mock_pricing_class, capsys):
        """Test that metal instances get appropriate error message"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_pricing = Mock()
        mock_pricing.get_spot_price_history.return_value = None
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "m5.metal"  # Metal instance
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.days = 30

        result = commands.cmd_spot_history(args)

        assert result == 1
        captured = capsys.readouterr()
        # Should mention spot not supported
        assert "not supported" in captured.err.lower() or "not supported" in captured.out.lower()

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    def test_cmd_spot_history_mac_instance_error_message(self, mock_get_client, mock_pricing_class, capsys):
        """Test that Mac instances get appropriate error message"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_pricing = Mock()
        mock_pricing.get_spot_price_history.return_value = None
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "mac1.metal"  # Mac instance
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.days = 30

        result = commands.cmd_spot_history(args)

        assert result == 1
        captured = capsys.readouterr()
        # Should mention spot not supported for Metal/Mac
        assert "not supported" in captured.err.lower() or "not supported" in captured.out.lower()

    @patch('src.cli.commands.pricing_commands.PricingService')
    @patch('src.cli.commands.pricing_commands.get_aws_client')
    def test_cmd_spot_history_regular_instance_suggests_alternatives(self, mock_get_client, mock_pricing_class, capsys):
        """Test that regular instances get suggestion to try other regions"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_pricing = Mock()
        mock_pricing.get_spot_price_history.return_value = None
        mock_pricing_class.return_value = mock_pricing

        args = Mock()
        args.instance_type = "t3.micro"  # Regular instance
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = False
        args.debug = False
        args.days = 30

        result = commands.cmd_spot_history(args)

        assert result == 1
        captured = capsys.readouterr()
        # Should suggest trying other regions
        output = captured.err + captured.out
        assert "compare-regions" in output.lower() or "region" in output.lower()


class TestSpotPricingErrorDetection:
    """Tests for spot pricing error detection logic"""

    def test_metal_instance_detection(self):
        """Test detection of metal instances"""
        metal_instances = ["m5.metal", "c5.metal", "r5.metal", "i3.metal"]
        for inst in metal_instances:
            assert ".metal" in inst

    def test_mac_instance_detection(self):
        """Test detection of Mac instances"""
        mac_instances = ["mac1.metal", "mac2.metal", "mac2-m2pro.metal"]
        for inst in mac_instances:
            assert inst.startswith("mac")

    def test_regular_instance_not_detected_as_metal_or_mac(self):
        """Test that regular instances are not detected as metal/mac"""
        regular_instances = ["t3.micro", "m5.large", "c5.xlarge", "r5.2xlarge"]
        for inst in regular_instances:
            assert ".metal" not in inst
            assert not inst.startswith("mac")


class TestCLIFilters:
    """Tests for CLI filter integration"""

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_storage_type_ebs_only_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_ebs_only, instance_with_instance_store
    ):
        """Test --storage-type ebs-only filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_ebs_only,
            instance_with_instance_store
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = "ebs-only"
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "t3.small"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_storage_type_instance_store_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_ebs_only, instance_with_instance_store
    ):
        """Test --storage-type instance-store filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_ebs_only,
            instance_with_instance_store
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = "instance-store"
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "i3.large"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_nvme_required_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_with_instance_store, instance_nvme_supported, instance_ebs_only
    ):
        """Test --nvme required filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_with_instance_store,  # nvme_support="required"
            instance_nvme_supported,       # nvme_support="supported"
            instance_ebs_only              # no instance storage
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = "required"
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "i3.large"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_nvme_supported_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_with_instance_store, instance_nvme_supported, instance_ebs_only
    ):
        """Test --nvme supported filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_with_instance_store,  # nvme_support="required"
            instance_nvme_supported,       # nvme_support="supported"
            instance_ebs_only              # no instance storage
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = "supported"
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "m5d.large"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_nvme_unsupported_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_with_instance_store, instance_nvme_supported, instance_ebs_only
    ):
        """Test --nvme unsupported filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_with_instance_store,  # nvme_support="required"
            instance_nvme_supported,       # nvme_support="supported"
            instance_ebs_only              # no instance storage
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = "unsupported"
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "t3.small"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_processor_family_intel_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        sample_instance_type, instance_amd, instance_graviton
    ):
        """Test --processor-family intel filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            sample_instance_type,  # t3.micro - Intel (x86_64, no 'a' suffix)
            instance_amd,          # m5a.large - AMD
            instance_graviton      # m6g.large - Graviton (arm64)
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = "intel"
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "t3.micro"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_processor_family_amd_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        sample_instance_type, instance_amd, instance_graviton
    ):
        """Test --processor-family amd filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            sample_instance_type,  # t3.micro - Intel
            instance_amd,          # m5a.large - AMD
            instance_graviton      # m6g.large - Graviton
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = "amd"
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "m5a.large"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_processor_family_graviton_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        sample_instance_type, instance_amd, instance_graviton
    ):
        """Test --processor-family graviton filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            sample_instance_type,  # t3.micro - Intel
            instance_amd,          # m5a.large - AMD
            instance_graviton      # m6g.large - Graviton
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = "graviton"
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 1
        assert instances[0].instance_type == "m6g.large"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_network_performance_low_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_low_network, sample_instance_type, instance_very_high_network
    ):
        """Test --network-performance low filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_low_network,       # "Low"
            sample_instance_type,       # "Up to 5 Gigabit"
            instance_very_high_network  # "100 Gigabit"
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = "low"
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        # "Low" matches "low" and "Up to 5 Gigabit" matches "up to 5 gigabit"
        assert len(instances) == 2
        instance_types = [i.instance_type for i in instances]
        assert "t2.nano" in instance_types
        assert "t3.micro" in instance_types

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_network_performance_high_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_low_network, instance_high_network, instance_very_high_network
    ):
        """Test --network-performance high filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_low_network,       # "Low"
            instance_high_network,      # "Up to 25 Gigabit"
            instance_very_high_network  # "100 Gigabit"
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = "high"
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        # "Up to 25 Gigabit" matches "up to 25 gigabit"
        assert len(instances) == 1
        assert instances[0].instance_type == "c5n.xlarge"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_network_performance_very_high_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_low_network, instance_high_network, instance_very_high_network
    ):
        """Test --network-performance very-high filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_low_network,       # "Low"
            instance_high_network,      # "Up to 25 Gigabit"
            instance_very_high_network  # "100 Gigabit"
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
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = "very-high"
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        # "100 Gigabit" matches "100 gigabit"
        assert len(instances) == 1
        assert instances[0].instance_type == "c5n.18xlarge"

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.instance_commands.PricingService')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_min_price_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        mock_pricing_class, mock_settings_class,
        instance_cheap, sample_instance_type, instance_expensive
    ):
        """Test --min-price filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_cheap,        # $0.0042/hr
            sample_instance_type,  # $0.0104/hr
            instance_expensive     # $32.77/hr
        ]
        mock_service_class.return_value = mock_service

        mock_settings = Mock()
        mock_settings.cli_pricing_concurrency = 5
        mock_settings_class.return_value = mock_settings

        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        args = Mock()
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = True  # Suppress pricing fetch progress messages
        args.debug = False
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = 0.01  # Filter out instances below $0.01/hr
        args.max_price = None
        args.include_pricing = False  # Don't fetch pricing, use fixture data

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        # instance_cheap ($0.0042) and sample_instance_type ($0.0104) are below $0.01
        # But we also keep instances without pricing, so test checks for proper filtering
        # Since these already have pricing attached, the filter should apply
        assert len(instances) == 2
        instance_types = [i.instance_type for i in instances]
        assert "t4g.nano" not in instance_types  # $0.0042 < $0.01
        assert "t3.micro" in instance_types       # $0.0104 > $0.01
        assert "p4d.24xlarge" in instance_types   # $32.77 > $0.01

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.instance_commands.PricingService')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_max_price_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        mock_pricing_class, mock_settings_class,
        instance_cheap, sample_instance_type, instance_expensive
    ):
        """Test --max-price filter"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_cheap,        # $0.0042/hr
            sample_instance_type,  # $0.0104/hr
            instance_expensive     # $32.77/hr
        ]
        mock_service_class.return_value = mock_service

        mock_settings = Mock()
        mock_settings.cli_pricing_concurrency = 5
        mock_settings_class.return_value = mock_settings

        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        args = Mock()
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = True
        args.debug = False
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = None
        args.max_price = 0.05  # Filter out instances above $0.05/hr
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        assert len(instances) == 2
        instance_types = [i.instance_type for i in instances]
        assert "t4g.nano" in instance_types       # $0.0042 < $0.05
        assert "t3.micro" in instance_types       # $0.0104 < $0.05
        assert "p4d.24xlarge" not in instance_types  # $32.77 > $0.05

    @patch('src.cli.commands.instance_commands.Settings')
    @patch('src.cli.commands.instance_commands.PricingService')
    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_price_range_filter(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        mock_pricing_class, mock_settings_class,
        instance_cheap, sample_instance_type, instance_expensive
    ):
        """Test --min-price and --max-price combined"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_cheap,        # $0.0042/hr
            sample_instance_type,  # $0.0104/hr
            instance_expensive     # $32.77/hr
        ]
        mock_service_class.return_value = mock_service

        mock_settings = Mock()
        mock_settings.cli_pricing_concurrency = 5
        mock_settings_class.return_value = mock_settings

        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        args = Mock()
        args.region = "us-east-1"
        args.profile = None
        args.format = "table"
        args.output = None
        args.quiet = True
        args.debug = False
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = 0.005   # Filter out below $0.005/hr
        args.max_price = 1.00    # Filter out above $1.00/hr
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        # Only t3.micro ($0.0104) is in range $0.005 - $1.00
        assert len(instances) == 1
        assert instances[0].instance_type == "t3.micro"

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_price_filter_keeps_instances_without_pricing(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        sample_instance_type, sample_instance_type_no_pricing
    ):
        """Test that price filter keeps instances without pricing data"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            sample_instance_type,          # Has pricing
            sample_instance_type_no_pricing  # No pricing
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
        args.quiet = True
        args.debug = False
        args.search = None
        args.free_tier_only = False
        args.family = None
        args.storage_type = None
        args.nvme = None
        args.processor_family = None
        args.network_performance = None
        args.min_price = 0.001
        args.max_price = 0.02
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        # t3.micro ($0.0104) is in range, m5.large (no pricing) should be kept
        assert len(instances) == 2
        instance_types = [i.instance_type for i in instances]
        assert "t3.micro" in instance_types
        assert "m5.large" in instance_types  # Kept despite no pricing

    @patch('src.cli.commands.instance_commands.InstanceService')
    @patch('src.cli.commands.instance_commands.get_aws_client')
    @patch('src.cli.commands.instance_commands.get_formatter')
    def test_combined_filters(
        self, mock_get_formatter, mock_get_client, mock_service_class,
        instance_with_instance_store, instance_ebs_only, instance_graviton,
        instance_amd, sample_instance_type
    ):
        """Test combining multiple filters"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_service = Mock()
        mock_service.get_instance_types.return_value = [
            instance_with_instance_store,  # i3.large - instance store, NVMe required, Intel
            instance_ebs_only,             # t3.small - EBS only, Intel
            instance_graviton,             # m6g.large - EBS only (no storage info), Graviton
            instance_amd,                  # m5a.large - EBS only (no storage info), AMD
            sample_instance_type           # t3.micro - EBS only, Intel
        ]
        mock_service_class.return_value = mock_service

        mock_formatter = Mock()
        mock_formatter.format_instance_list.return_value = "formatted output"
        mock_get_formatter.return_value = mock_formatter

        # Filter: EBS-only + Intel processor
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
        args.storage_type = "ebs-only"
        args.nvme = None
        args.processor_family = "intel"
        args.network_performance = None
        args.min_price = None
        args.max_price = None
        args.include_pricing = False

        result = commands.cmd_list(args)

        assert result == 0
        call_args = mock_formatter.format_instance_list.call_args
        instances = call_args[0][0]
        # Should only get EBS-only Intel instances: t3.small, t3.micro
        instance_types = [i.instance_type for i in instances]
        assert "t3.small" in instance_types
        assert "t3.micro" in instance_types
        assert "i3.large" not in instance_types   # Has instance store
        assert "m6g.large" not in instance_types  # Graviton
        assert "m5a.large" not in instance_types  # AMD
