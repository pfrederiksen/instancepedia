"""CLI argument parser"""

import argparse
from src.cli import commands
from src.config.settings import Settings


def add_common_args(parser: argparse.ArgumentParser):
    """Add common arguments to a parser"""
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="AWS region (default: from config or us-east-1)"
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="AWS profile name"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser"""
    settings = Settings()
    
    parser = argparse.ArgumentParser(
        description="Instancepedia - EC2 Instance Type Browser (CLI Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all instance types
  instancepedia list --region us-east-1

  # Show details for a specific instance
  instancepedia show t3.micro --region us-east-1

  # Search for instances
  instancepedia search m5 --region us-east-1

  # Get pricing information
  instancepedia pricing t3.micro --region us-east-1 --format json

  # List available regions
  instancepedia regions

  # Compare two instances
  instancepedia compare t3.micro t3.small --region us-east-1

  # Filter free tier instances
  instancepedia list --region us-east-1 --free-tier-only

  # Output to file
  instancepedia list --region us-east-1 --format json --output instances.json
        """
    )
    
    # Global arguments
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Run in TUI mode (interactive terminal UI)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List instance types")
    add_common_args(list_parser)
    list_parser.add_argument(
        "--search",
        type=str,
        default=None,
        help="Search filter (instance type name)"
    )
    list_parser.add_argument(
        "--free-tier-only",
        action="store_true",
        help="Show only free tier eligible instances"
    )
    list_parser.add_argument(
        "--family",
        type=str,
        default=None,
        help="Filter by instance family (e.g., t3, m5)"
    )
    list_parser.add_argument(
        "--include-pricing",
        action="store_true",
        help="Include pricing information (slower)"
    )
    list_parser.set_defaults(func=commands.cmd_list)
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show instance type details")
    add_common_args(show_parser)
    show_parser.add_argument(
        "instance_type",
        type=str,
        help="Instance type (e.g., t3.micro)"
    )
    show_parser.add_argument(
        "--include-pricing",
        action="store_true",
        help="Include pricing information"
    )
    show_parser.set_defaults(func=commands.cmd_show)
    
    # Search command (alias for list with search)
    search_parser = subparsers.add_parser("search", help="Search instance types")
    add_common_args(search_parser)
    search_parser.add_argument(
        "term",
        type=str,
        help="Search term"
    )
    search_parser.add_argument(
        "--free-tier-only",
        action="store_true",
        help="Show only free tier eligible instances"
    )
    search_parser.add_argument(
        "--family",
        type=str,
        default=None,
        help="Filter by instance family (e.g., t3, m5)"
    )
    search_parser.add_argument(
        "--include-pricing",
        action="store_true",
        help="Include pricing information (slower)"
    )
    # Override the search term to be used as --search
    def search_wrapper(args):
        args.search = args.term
        return commands.cmd_list(args)
    search_parser.set_defaults(func=search_wrapper)
    
    # Pricing command
    pricing_parser = subparsers.add_parser("pricing", help="Get pricing information")
    add_common_args(pricing_parser)
    pricing_parser.add_argument(
        "instance_type",
        type=str,
        help="Instance type (e.g., t3.micro)"
    )
    pricing_parser.set_defaults(func=commands.cmd_pricing)
    
    # Regions command
    regions_parser = subparsers.add_parser("regions", help="List available regions")
    add_common_args(regions_parser)
    regions_parser.set_defaults(func=commands.cmd_regions)
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two instance types")
    add_common_args(compare_parser)
    compare_parser.add_argument(
        "instance_type1",
        type=str,
        help="First instance type (e.g., t3.micro)"
    )
    compare_parser.add_argument(
        "instance_type2",
        type=str,
        help="Second instance type (e.g., t3.small)"
    )
    compare_parser.add_argument(
        "--include-pricing",
        action="store_true",
        help="Include pricing information"
    )
    compare_parser.set_defaults(func=commands.cmd_compare)
    
    return parser


def parse_args(args=None):
    """Parse command line arguments"""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Set default region if not provided (only for CLI commands)
    if parsed_args.command and not parsed_args.region and hasattr(parsed_args, 'region'):
        settings = Settings()
        parsed_args.region = settings.aws_region
    
    # Set default profile if not provided (only for CLI commands)
    if parsed_args.command and not parsed_args.profile and hasattr(parsed_args, 'profile'):
        settings = Settings()
        parsed_args.profile = settings.aws_profile
    
    return parsed_args
