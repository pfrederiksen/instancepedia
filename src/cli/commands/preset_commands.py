"""Filter preset CLI commands"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.services.free_tier_service import FreeTierService
from src.services.filter_preset_service import FilterPresetService, FilterPreset
from src.models.instance_type import InstanceType, PricingInfo
from src.cli.output import get_formatter
from src.config.settings import Settings

from .base import status, print_error, get_aws_client, write_output


def cmd_presets_list(args) -> int:
    """List filter presets command"""
    try:
        preset_service = FilterPresetService()
        all_presets = preset_service.get_all_presets()

        if args.format == "json":
            import json
            data = {
                name: preset.to_dict()
                for name, preset in all_presets.items()
            }
            print(json.dumps(data, indent=2))
        else:
            # Table format
            from tabulate import tabulate
            headers = ["Preset Name", "Description"]
            rows = []
            for name, preset in sorted(all_presets.items()):
                rows.append([name, preset.description or "No description"])

            print("Available Filter Presets:\n")
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            print("\nUse 'instancepedia presets apply <preset_name>' to apply a preset")

        return 0
    except Exception as e:
        print_error(str(e))
        return 1


def cmd_presets_apply(args) -> int:
    """Apply a filter preset command"""
    try:
        preset_service = FilterPresetService()
        preset = preset_service.get_preset(args.preset_name)

        if not preset:
            print_error(f"Preset '{args.preset_name}' not found")
            status("Use 'instancepedia presets list' to see available presets")
            return 1

        status(f"Applying preset: {preset.name}", args.quiet)
        if preset.description:
            status(f"Description: {preset.description}", args.quiet)
        status(f"Fetching instance types for region {args.region}...", args.quiet)

        # Fetch instances
        formatter = get_formatter(args.format)
        aws_client = get_aws_client(args.region, args.profile)
        instance_service = InstanceService(aws_client)
        instances = instance_service.get_instance_types(fetch_pricing=False)

        # Apply preset filters
        filtered_instances = _apply_preset_filters(instances, preset)

        status(f"Found {len(filtered_instances)} instances matching preset criteria", args.quiet)

        # Fetch pricing if requested
        if args.include_pricing and filtered_instances:
            filtered_instances = _fetch_pricing_for_preset(filtered_instances, args)

        # Sort and output
        filtered_instances = sorted(filtered_instances, key=lambda x: x.instance_type)

        output = formatter.format_instance_list(filtered_instances, args.region)
        write_output(output, args.output, args.quiet)

        return 0

    except Exception as e:
        print_error(str(e), debug=args.debug, exception=e)
        return 1


def _apply_preset_filters(instances: list, preset) -> list:
    """Apply preset filters to instances."""
    filtered_instances = instances

    if preset.min_vcpu is not None:
        filtered_instances = [i for i in filtered_instances if i.vcpu_info.default_vcpus >= preset.min_vcpu]

    if preset.max_vcpu is not None:
        filtered_instances = [i for i in filtered_instances if i.vcpu_info.default_vcpus <= preset.max_vcpu]

    if preset.min_memory is not None:
        filtered_instances = [i for i in filtered_instances if i.memory_info.size_in_gb >= preset.min_memory]

    if preset.max_memory is not None:
        filtered_instances = [i for i in filtered_instances if i.memory_info.size_in_gb <= preset.max_memory]

    if preset.has_gpu is not None:
        if preset.has_gpu:
            filtered_instances = [i for i in filtered_instances if i.gpu_info is not None]
        else:
            filtered_instances = [i for i in filtered_instances if i.gpu_info is None]

    if preset.current_generation_only:
        filtered_instances = [i for i in filtered_instances if i.current_generation]

    if preset.burstable_only:
        filtered_instances = [i for i in filtered_instances if i.burstable_performance_supported]

    if preset.free_tier_only:
        free_tier_service = FreeTierService()
        filtered_instances = [i for i in filtered_instances if free_tier_service.is_eligible(i.instance_type)]

    if preset.architecture:
        filtered_instances = [i for i in filtered_instances if preset.architecture in i.processor_info.supported_architectures]

    if preset.instance_families:
        filtered_instances = [i for i in filtered_instances if any(i.instance_type.startswith(f + '.') for f in preset.instance_families)]

    # Extended filters
    if preset.processor_family:
        filtered_instances = _filter_by_processor_family(filtered_instances, preset.processor_family)

    if preset.network_performance:
        filtered_instances = _filter_by_network_performance(filtered_instances, preset.network_performance)

    if preset.storage_type:
        filtered_instances = _filter_by_storage_type(filtered_instances, preset.storage_type)

    if preset.nvme_support:
        filtered_instances = _filter_by_nvme_support(filtered_instances, preset.nvme_support)

    # Price filters only apply to instances with pricing data
    if preset.min_price is not None:
        filtered_instances = [
            i for i in filtered_instances
            if i.pricing is None or i.pricing.on_demand_price is None or i.pricing.on_demand_price >= preset.min_price
        ]

    if preset.max_price is not None:
        filtered_instances = [
            i for i in filtered_instances
            if i.pricing is None or i.pricing.on_demand_price is None or i.pricing.on_demand_price <= preset.max_price
        ]

    return filtered_instances


def _filter_by_processor_family(instances: list, processor_family: str) -> list:
    """Filter instances by processor family."""
    if processor_family == "graviton":
        return [i for i in instances if "arm64" in i.processor_info.supported_architectures]
    elif processor_family == "amd":
        # AMD instances typically have 'a' suffix (e.g., m5a, c5a, r5a)
        return [
            i for i in instances
            if "arm64" not in i.processor_info.supported_architectures
            and any(c.isalpha() and c == 'a' for c in i.instance_type.split('.')[0][-1:])
        ]
    elif processor_family == "intel":
        # Intel is default x86 without 'a' suffix
        return [
            i for i in instances
            if "arm64" not in i.processor_info.supported_architectures
            and not any(c.isalpha() and c == 'a' for c in i.instance_type.split('.')[0][-1:])
        ]
    return instances


def _filter_by_network_performance(instances: list, network_performance: str) -> list:
    """Filter instances by network performance tier."""
    perf_map = {
        "low": ["Low", "Up to 5", "Moderate"],
        "moderate": ["10 Gigabit", "12 Gigabit", "Up to 10", "Up to 12"],
        "high": ["10 Gigabit", "12 Gigabit", "15 Gigabit", "20 Gigabit", "25 Gigabit"],
        "very_high": ["50 Gigabit", "75 Gigabit", "100 Gigabit", "200 Gigabit", "400 Gigabit"],
    }
    keywords = perf_map.get(network_performance, [])
    if not keywords:
        return instances

    return [
        i for i in instances
        if i.network_info and any(kw.lower() in i.network_info.network_performance.lower() for kw in keywords)
    ]


def _filter_by_storage_type(instances: list, storage_type: str) -> list:
    """Filter instances by storage type."""
    if storage_type == "ebs_only":
        return [
            i for i in instances
            if i.instance_storage_info is None or i.instance_storage_info.total_size_in_gb == 0
        ]
    elif storage_type == "has_instance_store":
        return [
            i for i in instances
            if i.instance_storage_info is not None and i.instance_storage_info.total_size_in_gb > 0
        ]
    return instances


def _filter_by_nvme_support(instances: list, nvme_support: str) -> list:
    """Filter instances by NVMe support."""
    if nvme_support == "required":
        return [
            i for i in instances
            if i.instance_storage_info and i.instance_storage_info.nvme_support == "required"
        ]
    elif nvme_support == "supported":
        return [
            i for i in instances
            if i.instance_storage_info and i.instance_storage_info.nvme_support in ["required", "supported"]
        ]
    elif nvme_support == "unsupported":
        return [
            i for i in instances
            if i.instance_storage_info is None or i.instance_storage_info.nvme_support == "unsupported"
        ]
    return instances


def _fetch_pricing_for_preset(instances: list, args) -> list:
    """Fetch pricing for preset-filtered instances."""
    status("Fetching pricing information...", args.quiet)

    settings = Settings()
    aws_client = get_aws_client(args.region, args.profile)
    pricing_service = PricingService(aws_client, settings=settings)

    def fetch_price(instance: InstanceType):
        try:
            on_demand = pricing_service.get_on_demand_price(instance.instance_type, args.region)
            spot = pricing_service.get_spot_price(instance.instance_type, args.region)
            instance.pricing = PricingInfo(on_demand_price=on_demand, spot_price=spot)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=settings.cli_pricing_concurrency) as executor:
        futures = {executor.submit(fetch_price, inst): inst for inst in instances}
        for future in as_completed(futures):
            pass

    return instances


def cmd_presets_save(args) -> int:
    """Save a custom filter preset command"""
    try:
        preset_service = FilterPresetService()
        preset_name = args.preset_name

        # Check if trying to overwrite a built-in preset
        if preset_service.is_builtin_preset(preset_name):
            print_error(f"Cannot overwrite built-in preset '{preset_name}'")
            return 1

        # Check if preset already exists
        existing_preset = preset_service.get_preset(preset_name)
        if existing_preset and not args.force:
            print_error(f"Preset '{preset_name}' already exists. Use --force to overwrite.")
            return 1

        # Build preset from arguments
        preset = FilterPreset(
            name=preset_name,
            description=args.description,
            min_vcpu=args.min_vcpu,
            max_vcpu=args.max_vcpu,
            min_memory=args.min_memory,
            max_memory=args.max_memory,
            has_gpu=args.has_gpu,
            current_generation_only=args.current_generation,
            burstable_only=args.burstable,
            free_tier_only=args.free_tier,
            architecture=args.architecture,
            instance_families=args.instance_families.split(",") if args.instance_families else None,
            processor_family=args.processor_family,
            network_performance=args.network_performance,
            storage_type=args.storage_type,
            nvme_support=args.nvme_support,
            min_price=args.min_price,
            max_price=args.max_price,
        )

        # Validate that at least one filter is set
        preset_dict = preset.to_dict()
        filter_keys = [k for k in preset_dict.keys() if k not in ("name", "description")]
        if not filter_keys:
            print_error("At least one filter option must be specified")
            status("Use --help to see available filter options")
            return 1

        # Save the preset
        if preset_service.save_custom_preset(preset):
            status(f"Preset '{preset_name}' saved successfully", args.quiet)
            if args.format == "json":
                import json
                print(json.dumps(preset.to_dict(), indent=2))
            return 0
        else:
            print_error("Failed to save preset")
            return 1

    except Exception as e:
        print_error(str(e), debug=getattr(args, 'debug', False), exception=e)
        return 1


def cmd_presets_delete(args) -> int:
    """Delete a custom filter preset command"""
    try:
        preset_service = FilterPresetService()
        preset_name = args.preset_name

        # Check if it's a built-in preset
        if preset_service.is_builtin_preset(preset_name):
            print_error(f"Cannot delete built-in preset '{preset_name}'")
            return 1

        # Check if preset exists
        if not preset_service.is_custom_preset(preset_name):
            print_error(f"Custom preset '{preset_name}' not found")
            status("Use 'instancepedia presets list' to see available presets")
            return 1

        # Confirm deletion unless --force is used
        if not args.force:
            print(f"Are you sure you want to delete preset '{preset_name}'? [y/N] ", end="")
            sys.stdout.flush()
            response = input().strip().lower()
            if response not in ("y", "yes"):
                status("Deletion cancelled")
                return 0

        # Delete the preset
        if preset_service.delete_custom_preset(preset_name):
            status(f"Preset '{preset_name}' deleted successfully", args.quiet)
            return 0
        else:
            print_error("Failed to delete preset")
            return 1

    except Exception as e:
        print_error(str(e), debug=getattr(args, 'debug', False), exception=e)
        return 1
