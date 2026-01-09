"""CLI command handlers

This package organizes CLI commands into logical modules:
- instance_commands: Instance browsing, listing, comparison
- pricing_commands: Pricing operations, cost estimation, spot history
- cache_commands: Cache management
- preset_commands: Filter preset management
"""

import sys

# Import all commands for easy access
from .instance_commands import (
    cmd_list,
    cmd_show,
    cmd_search,
    cmd_compare,
    cmd_compare_family,
    cmd_regions,
)
from .pricing_commands import (
    cmd_pricing,
    cmd_cost_estimate,
    cmd_compare_regions,
    cmd_spot_history,
)
from .cache_commands import (
    cmd_cache_stats,
    cmd_cache_clear,
)
from .preset_commands import (
    cmd_presets_list,
    cmd_presets_apply,
)
from .base import (
    print_error,
    get_aws_client,
    fetch_instance_pricing,
    write_output,
)


def run_cli(args) -> int:
    """Run CLI command based on args"""
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        print("Error: No command specified", file=sys.stderr)
        return 1


__all__ = [
    # Instance commands
    'cmd_list',
    'cmd_show',
    'cmd_search',
    'cmd_compare',
    'cmd_compare_family',
    'cmd_regions',
    # Pricing commands
    'cmd_pricing',
    'cmd_cost_estimate',
    'cmd_compare_regions',
    'cmd_spot_history',
    # Cache commands
    'cmd_cache_stats',
    'cmd_cache_clear',
    # Preset commands
    'cmd_presets_list',
    'cmd_presets_apply',
    # Base utilities
    'print_error',
    'get_aws_client',
    'fetch_instance_pricing',
    'write_output',
    # Runner
    'run_cli',
]
