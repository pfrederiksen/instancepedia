"""Filter preset CLI commands"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.instance_service import InstanceService
from src.services.pricing_service import PricingService
from src.services.free_tier_service import FreeTierService
from src.services.filter_preset_service import FilterPresetService
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
                name: {
                    "description": preset.description,
                    "min_vcpu": preset.min_vcpu,
                    "max_vcpu": preset.max_vcpu,
                    "min_memory": preset.min_memory,
                    "max_memory": preset.max_memory,
                    "has_gpu": preset.has_gpu,
                    "current_generation_only": preset.current_generation_only,
                    "burstable_only": preset.burstable_only,
                    "free_tier_only": preset.free_tier_only,
                    "architecture": preset.architecture,
                    "instance_families": preset.instance_families
                }
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

    return filtered_instances


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
