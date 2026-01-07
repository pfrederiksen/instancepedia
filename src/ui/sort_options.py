"""Sorting options for instance list"""

from enum import Enum
from typing import List
from src.models.instance_type import InstanceType


class SortOption(Enum):
    """Available sort options"""
    DEFAULT = ("Instance Type (A-Z)", lambda inst: inst.instance_type.lower())
    PRICE_LOW_HIGH = ("Price (Low-High)", lambda inst: (inst.pricing.on_demand_price or float('inf'), inst.instance_type))
    PRICE_HIGH_LOW = ("Price (High-Low)", lambda inst: (-(inst.pricing.on_demand_price or 0), inst.instance_type))
    VCPU_LOW_HIGH = ("vCPU (Low-High)", lambda inst: (inst.vcpu_info.default_vcpus, inst.instance_type))
    VCPU_HIGH_LOW = ("vCPU (High-Low)", lambda inst: (-inst.vcpu_info.default_vcpus, inst.instance_type))
    MEMORY_LOW_HIGH = ("Memory (Low-High)", lambda inst: (inst.memory_info.size_in_gb, inst.instance_type))
    MEMORY_HIGH_LOW = ("Memory (High-Low)", lambda inst: (-inst.memory_info.size_in_gb, inst.instance_type))

    def __init__(self, display_name: str, key_func):
        self.display_name = display_name
        self.key_func = key_func

    def sort(self, instances: List[InstanceType]) -> List[InstanceType]:
        """Sort instances according to this option"""
        return sorted(instances, key=self.key_func)

    @classmethod
    def get_next(cls, current: 'SortOption') -> 'SortOption':
        """Get the next sort option in the cycle"""
        options = list(cls)
        current_index = options.index(current)
        next_index = (current_index + 1) % len(options)
        return options[next_index]
