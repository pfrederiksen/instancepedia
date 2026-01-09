"""Tests for CLI argument parser"""

import argparse
import pytest
from src.cli.parser import create_parser, parse_args, region_type
from src.cli.commands.base import validate_region, validate_regions


class TestParser:
    """Tests for argument parser"""
    
    def test_create_parser(self):
        """Test parser creation"""
        parser = create_parser()
        assert parser is not None
    
    def test_parse_no_args(self):
        """Test parsing with no arguments (should default to TUI)"""
        args = parse_args([])
        assert args.command is None or args.tui
    
    def test_parse_tui_flag(self):
        """Test parsing with --tui flag"""
        args = parse_args(["--tui"])
        assert args.tui is True
    
    def test_parse_list_command(self):
        """Test parsing list command"""
        args = parse_args(["list", "--region", "us-east-1"])
        assert args.command == "list"
        assert args.region == "us-east-1"
        assert hasattr(args, "func")
    
    def test_parse_list_with_filters(self):
        """Test parsing list command with filters"""
        args = parse_args([
            "list",
            "--region", "us-east-1",
            "--search", "t3",
            "--free-tier-only",
            "--family", "t3"
        ])
        assert args.command == "list"
        assert args.search == "t3"
        assert args.free_tier_only is True
        assert args.family == "t3"
    
    def test_parse_show_command(self):
        """Test parsing show command"""
        args = parse_args(["show", "t3.micro", "--region", "us-east-1"])
        assert args.command == "show"
        assert args.instance_type == "t3.micro"
        assert args.region == "us-east-1"
    
    def test_parse_search_command(self):
        """Test parsing search command"""
        args = parse_args(["search", "m5", "--region", "us-east-1"])
        assert args.command == "search"
        assert args.term == "m5"
        assert args.region == "us-east-1"
    
    def test_parse_pricing_command(self):
        """Test parsing pricing command"""
        args = parse_args(["pricing", "t3.micro", "--region", "us-east-1"])
        assert args.command == "pricing"
        assert args.instance_type == "t3.micro"
        assert args.region == "us-east-1"
    
    def test_parse_regions_command(self):
        """Test parsing regions command"""
        args = parse_args(["regions"])
        assert args.command == "regions"
    
    def test_parse_compare_command(self):
        """Test parsing compare command"""
        args = parse_args([
            "compare",
            "t3.micro",
            "t3.small",
            "--region", "us-east-1"
        ])
        assert args.command == "compare"
        assert args.instance_type1 == "t3.micro"
        assert args.instance_type2 == "t3.small"
        assert args.region == "us-east-1"
    
    def test_parse_format_options(self):
        """Test parsing format options"""
        args = parse_args(["list", "--format", "json"])
        assert args.format == "json"
        
        args = parse_args(["list", "--format", "csv"])
        assert args.format == "csv"
        
        args = parse_args(["list", "--format", "table"])
        assert args.format == "table"
    
    def test_parse_output_option(self):
        """Test parsing output file option"""
        args = parse_args(["list", "--output", "output.json"])
        assert args.output == "output.json"
    
    def test_parse_quiet_option(self):
        """Test parsing quiet option"""
        args = parse_args(["list", "--quiet"])
        assert args.quiet is True
    
    def test_parse_debug_option(self):
        """Test parsing debug option"""
        args = parse_args(["list", "--debug"])
        assert args.debug is True
    
    def test_parse_profile_option(self):
        """Test parsing profile option"""
        args = parse_args(["list", "--profile", "my-profile"])
        assert args.profile == "my-profile"
    
    def test_parse_include_pricing(self):
        """Test parsing include-pricing option"""
        args = parse_args(["list", "--include-pricing"])
        assert args.include_pricing is True


class TestRegionValidation:
    """Tests for region validation utilities"""

    def test_region_type_valid(self):
        """Test region_type accepts valid regions"""
        assert region_type("us-east-1") == "us-east-1"
        assert region_type("eu-west-1") == "eu-west-1"
        assert region_type("ap-southeast-2") == "ap-southeast-2"

    def test_region_type_invalid(self):
        """Test region_type rejects invalid regions with helpful error"""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            region_type("invalid-region")
        error_msg = str(exc_info.value)
        assert "Invalid region 'invalid-region'" in error_msg
        assert "instancepedia regions" in error_msg

    def test_region_type_similar_suggestions(self):
        """Test region_type suggests similar region names"""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            region_type("us-east")  # Close to us-east-1, us-east-2
        error_msg = str(exc_info.value)
        assert "Did you mean:" in error_msg

    def test_validate_region_valid(self):
        """Test validate_region returns True for valid regions"""
        assert validate_region("us-east-1", exit_on_error=False) is True
        assert validate_region("eu-west-1", exit_on_error=False) is True

    def test_validate_region_invalid(self):
        """Test validate_region returns False for invalid regions"""
        assert validate_region("invalid", exit_on_error=False) is False
        assert validate_region("foo-bar-1", exit_on_error=False) is False

    def test_validate_regions_all_valid(self):
        """Test validate_regions returns empty list for all valid regions"""
        invalid = validate_regions(["us-east-1", "us-west-2", "eu-west-1"], exit_on_error=False)
        assert invalid == []

    def test_validate_regions_some_invalid(self):
        """Test validate_regions returns list of invalid regions"""
        invalid = validate_regions(["us-east-1", "invalid", "foo"], exit_on_error=False)
        assert "invalid" in invalid
        assert "foo" in invalid
        assert "us-east-1" not in invalid

    def test_parser_rejects_invalid_region(self):
        """Test parser rejects invalid region at parse time"""
        with pytest.raises(SystemExit):
            parse_args(["list", "--region", "invalid-region"])
