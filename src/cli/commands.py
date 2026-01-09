"""CLI command handlers

This module re-exports all commands from the commands package for backwards compatibility.
The actual implementations are in:
- src/cli/commands/instance_commands.py
- src/cli/commands/pricing_commands.py
- src/cli/commands/cache_commands.py
- src/cli/commands/preset_commands.py
"""

# Re-export everything from the commands package
from src.cli.commands import (
    # Instance commands
    cmd_list,
    cmd_show,
    cmd_search,
    cmd_compare,
    cmd_compare_family,
    cmd_regions,
    # Pricing commands
    cmd_pricing,
    cmd_cost_estimate,
    cmd_compare_regions,
    cmd_spot_history,
    # Cache commands
    cmd_cache_stats,
    cmd_cache_clear,
    # Preset commands
    cmd_presets_list,
    cmd_presets_apply,
    # Base utilities
    print_error,
    get_aws_client,
    fetch_instance_pricing,
    write_output,
    # Runner
    run_cli,
)

__all__ = [
    'cmd_list',
    'cmd_show',
    'cmd_search',
    'cmd_compare',
    'cmd_compare_family',
    'cmd_regions',
    'cmd_pricing',
    'cmd_cost_estimate',
    'cmd_compare_regions',
    'cmd_spot_history',
    'cmd_cache_stats',
    'cmd_cache_clear',
    'cmd_presets_list',
    'cmd_presets_apply',
    'print_error',
    'get_aws_client',
    'fetch_instance_pricing',
    'write_output',
    'run_cli',
]
