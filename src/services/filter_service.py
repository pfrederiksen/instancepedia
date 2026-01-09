"""Unified filtering service for instance types

This module provides shared filtering logic used by both TUI and CLI.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from src.models.instance_type import InstanceType
from src.services.free_tier_service import FreeTierService


@dataclass
class FilterCriteria:
    """Container for filter criteria used by both TUI and CLI.

    Attributes:
        search: Text search filter (instance type name)
        min_vcpu: Minimum vCPU count
        max_vcpu: Maximum vCPU count
        min_memory_gb: Minimum memory in GB
        max_memory_gb: Maximum memory in GB
        gpu_filter: GPU filter - "any", "yes", "no"
        current_generation: Current generation filter - "any", "yes", "no"
        burstable: Burstable filter - "any", "yes", "no"
        free_tier: Free tier filter - "any", "yes", "no"
        architecture: Architecture filter - "any", "x86_64", "arm64"
        processor_family: Processor family - "any", "intel", "amd", "graviton"
        network_performance: Network performance - "any", "low", "moderate", "high", "very_high"
        family_filter: Comma-separated list of families
        storage_type: Storage type - "any", "ebs_only", "has_instance_store"
        nvme_support: NVMe support - "any", "required", "supported", "unsupported"
        min_price: Minimum hourly price
        max_price: Maximum hourly price
    """
    search: Optional[str] = None
    min_vcpu: Optional[int] = None
    max_vcpu: Optional[int] = None
    min_memory_gb: Optional[float] = None
    max_memory_gb: Optional[float] = None
    gpu_filter: str = "any"
    current_generation: str = "any"
    burstable: str = "any"
    free_tier: str = "any"
    architecture: str = "any"
    processor_family: str = "any"
    network_performance: str = "any"
    family_filter: str = ""
    storage_type: str = "any"
    nvme_support: str = "any"
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "search": self.search,
            "min_vcpu": self.min_vcpu,
            "max_vcpu": self.max_vcpu,
            "min_memory_gb": self.min_memory_gb,
            "max_memory_gb": self.max_memory_gb,
            "gpu_filter": self.gpu_filter,
            "current_generation": self.current_generation,
            "burstable": self.burstable,
            "free_tier": self.free_tier,
            "architecture": self.architecture,
            "processor_family": self.processor_family,
            "network_performance": self.network_performance,
            "family_filter": self.family_filter,
            "storage_type": self.storage_type,
            "nvme_support": self.nvme_support,
            "min_price": self.min_price,
            "max_price": self.max_price,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FilterCriteria":
        """Create from dictionary."""
        return cls(
            search=data.get("search"),
            min_vcpu=data.get("min_vcpu"),
            max_vcpu=data.get("max_vcpu"),
            min_memory_gb=data.get("min_memory_gb"),
            max_memory_gb=data.get("max_memory_gb"),
            gpu_filter=data.get("gpu_filter", "any"),
            current_generation=data.get("current_generation", "any"),
            burstable=data.get("burstable", "any"),
            free_tier=data.get("free_tier", "any"),
            architecture=data.get("architecture", "any"),
            processor_family=data.get("processor_family", "any"),
            network_performance=data.get("network_performance", "any"),
            family_filter=data.get("family_filter", ""),
            storage_type=data.get("storage_type", "any"),
            nvme_support=data.get("nvme_support", "any"),
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
        )

    @classmethod
    def from_cli_args(cls, args) -> "FilterCriteria":
        """Create from CLI argument namespace.

        Maps CLI argument names to FilterCriteria fields.
        """
        return cls(
            search=getattr(args, 'search', None),
            free_tier="yes" if getattr(args, 'free_tier_only', False) else "any",
            family_filter=getattr(args, 'family', None) or "",
            storage_type=_map_cli_storage_type(getattr(args, 'storage_type', None)),
            nvme_support=getattr(args, 'nvme', None) or "any",
            processor_family=getattr(args, 'processor_family', None) or "any",
            network_performance=_map_cli_network_performance(getattr(args, 'network_performance', None)),
            min_price=getattr(args, 'min_price', None),
            max_price=getattr(args, 'max_price', None),
        )

    def has_active_filters(self) -> bool:
        """Check if any filters are active."""
        return (
            self.search is not None
            or self.min_vcpu is not None
            or self.max_vcpu is not None
            or self.min_memory_gb is not None
            or self.max_memory_gb is not None
            or self.gpu_filter != "any"
            or self.current_generation != "any"
            or self.burstable != "any"
            or self.free_tier != "any"
            or self.architecture != "any"
            or self.processor_family != "any"
            or self.network_performance != "any"
            or bool(self.family_filter.strip())
            or self.storage_type != "any"
            or self.nvme_support != "any"
            or self.min_price is not None
            or self.max_price is not None
        )

    def reset(self) -> None:
        """Reset all filters to default."""
        self.search = None
        self.min_vcpu = None
        self.max_vcpu = None
        self.min_memory_gb = None
        self.max_memory_gb = None
        self.gpu_filter = "any"
        self.current_generation = "any"
        self.burstable = "any"
        self.free_tier = "any"
        self.architecture = "any"
        self.processor_family = "any"
        self.network_performance = "any"
        self.family_filter = ""
        self.storage_type = "any"
        self.nvme_support = "any"
        self.min_price = None
        self.max_price = None


def _map_cli_storage_type(value: Optional[str]) -> str:
    """Map CLI storage type argument to filter criteria value."""
    if not value:
        return "any"
    mapping = {
        "ebs-only": "ebs_only",
        "instance-store": "has_instance_store",
    }
    return mapping.get(value, "any")


def _map_cli_network_performance(value: Optional[str]) -> str:
    """Map CLI network performance argument to filter criteria value."""
    if not value:
        return "any"
    mapping = {
        "very-high": "very_high",
    }
    return mapping.get(value, value)


def apply_filters(
    instances: List[InstanceType],
    criteria: FilterCriteria
) -> List[InstanceType]:
    """Apply all filters to a list of instances.

    Args:
        instances: List of instances to filter
        criteria: Filter criteria to apply

    Returns:
        Filtered list of instances
    """
    filtered = instances

    # Search filter
    if criteria.search:
        search_lower = criteria.search.lower()
        filtered = [inst for inst in filtered if search_lower in inst.instance_type.lower()]

    # vCPU filters
    if criteria.min_vcpu is not None:
        filtered = [inst for inst in filtered if inst.vcpu_info.default_vcpus >= criteria.min_vcpu]
    if criteria.max_vcpu is not None:
        filtered = [inst for inst in filtered if inst.vcpu_info.default_vcpus <= criteria.max_vcpu]

    # Memory filters
    if criteria.min_memory_gb is not None:
        filtered = [inst for inst in filtered if inst.memory_info.size_in_gb >= criteria.min_memory_gb]
    if criteria.max_memory_gb is not None:
        filtered = [inst for inst in filtered if inst.memory_info.size_in_gb <= criteria.max_memory_gb]

    # GPU filter
    if criteria.gpu_filter == "yes":
        filtered = [inst for inst in filtered if inst.gpu_info and inst.gpu_info.total_gpu_count > 0]
    elif criteria.gpu_filter == "no":
        filtered = [inst for inst in filtered if not inst.gpu_info or inst.gpu_info.total_gpu_count == 0]

    # Current generation filter
    if criteria.current_generation == "yes":
        filtered = [inst for inst in filtered if inst.current_generation]
    elif criteria.current_generation == "no":
        filtered = [inst for inst in filtered if not inst.current_generation]

    # Burstable filter
    if criteria.burstable == "yes":
        filtered = [inst for inst in filtered if inst.burstable_performance_supported]
    elif criteria.burstable == "no":
        filtered = [inst for inst in filtered if not inst.burstable_performance_supported]

    # Free tier filter
    if criteria.free_tier == "yes":
        free_tier_service = FreeTierService()
        filtered = [inst for inst in filtered if free_tier_service.is_eligible(inst.instance_type)]
    elif criteria.free_tier == "no":
        free_tier_service = FreeTierService()
        filtered = [inst for inst in filtered if not free_tier_service.is_eligible(inst.instance_type)]

    # Architecture filter
    if criteria.architecture != "any":
        filtered = [inst for inst in filtered if criteria.architecture in inst.processor_info.supported_architectures]

    # Processor family filter
    if criteria.processor_family != "any":
        filtered = _apply_processor_filter(filtered, criteria.processor_family)

    # Network performance filter
    if criteria.network_performance != "any":
        filtered = _apply_network_filter(filtered, criteria.network_performance)

    # Family filter
    if criteria.family_filter.strip():
        families = [f.strip() for f in criteria.family_filter.split(',') if f.strip()]
        filtered = [
            inst for inst in filtered
            if any(inst.instance_type.startswith(f + '.') or inst.instance_type.startswith(f) for f in families)
        ]

    # Storage type filter
    if criteria.storage_type == "ebs_only":
        filtered = [
            inst for inst in filtered
            if inst.instance_storage_info is None
            or inst.instance_storage_info.total_size_in_gb is None
            or inst.instance_storage_info.total_size_in_gb == 0
        ]
    elif criteria.storage_type == "has_instance_store":
        filtered = [
            inst for inst in filtered
            if inst.instance_storage_info
            and inst.instance_storage_info.total_size_in_gb
            and inst.instance_storage_info.total_size_in_gb > 0
        ]

    # NVMe support filter
    if criteria.nvme_support == "required":
        filtered = [inst for inst in filtered if inst.instance_storage_info and inst.instance_storage_info.nvme_support == "required"]
    elif criteria.nvme_support == "supported":
        filtered = [inst for inst in filtered if inst.instance_storage_info and inst.instance_storage_info.nvme_support == "supported"]
    elif criteria.nvme_support == "unsupported":
        filtered = [inst for inst in filtered if not inst.instance_storage_info or not inst.instance_storage_info.nvme_support or inst.instance_storage_info.nvme_support == "unsupported"]

    # Price filters (instances without pricing are kept)
    if criteria.min_price is not None:
        filtered = [
            inst for inst in filtered
            if not inst.pricing or inst.pricing.on_demand_price is None or inst.pricing.on_demand_price >= criteria.min_price
        ]
    if criteria.max_price is not None:
        filtered = [
            inst for inst in filtered
            if not inst.pricing or inst.pricing.on_demand_price is None or inst.pricing.on_demand_price <= criteria.max_price
        ]

    return filtered


def _is_amd_instance(instance_type: str) -> bool:
    """Check if instance type is AMD (has 'a' suffix before size)."""
    parts = instance_type.split('.')
    if len(parts) >= 1:
        family_part = parts[0]
        return family_part.endswith('a') and not family_part.endswith('ga')
    return False


def _apply_processor_filter(instances: List[InstanceType], processor_family: str) -> List[InstanceType]:
    """Apply processor family filter."""
    if processor_family == "intel":
        return [
            inst for inst in instances
            if not _is_amd_instance(inst.instance_type) and "arm64" not in inst.processor_info.supported_architectures
        ]
    elif processor_family == "amd":
        return [inst for inst in instances if _is_amd_instance(inst.instance_type)]
    elif processor_family == "graviton":
        return [inst for inst in instances if "arm64" in inst.processor_info.supported_architectures]
    return instances


def _apply_network_filter(instances: List[InstanceType], network_performance: str) -> List[InstanceType]:
    """Apply network performance filter."""
    perf_map = {
        "low": ["low", "very low", "up to 5 gigabit"],
        "moderate": ["moderate", "up to 10 gigabit", "up to 12 gigabit"],
        "high": ["high", "10 gigabit", "12 gigabit", "25 gigabit", "up to 25 gigabit"],
        "very_high": ["50 gigabit", "100 gigabit", "200 gigabit", "up to 100 gigabit", "up to 200 gigabit"],
    }
    target_perfs = perf_map.get(network_performance, [])
    return [
        inst for inst in instances
        if any(perf.lower() in inst.network_info.network_performance.lower() for perf in target_perfs)
    ]
