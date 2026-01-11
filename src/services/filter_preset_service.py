"""Filter preset service for saving and loading filter configurations"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class FilterPreset:
    """Filter preset configuration"""
    name: str
    description: str | None = None
    min_vcpu: int | None = None
    max_vcpu: int | None = None
    min_memory: float | None = None
    max_memory: float | None = None
    has_gpu: bool | None = None
    current_generation_only: bool = False
    burstable_only: bool = False
    free_tier_only: bool = False
    architecture: str | None = None  # "x86_64" or "arm64"
    instance_families: list[str] | None = None  # e.g., ["t3", "t4g"]
    # Extended filter fields (aligned with FilterCriteria)
    processor_family: str | None = None  # "intel", "amd", "graviton"
    network_performance: str | None = None  # "low", "moderate", "high", "very_high"
    storage_type: str | None = None  # "ebs_only", "has_instance_store"
    nvme_support: str | None = None  # "required", "supported", "unsupported"
    min_price: float | None = None  # minimum hourly price
    max_price: float | None = None  # maximum hourly price

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Remove None values and False booleans to keep JSON clean
        return {k: v for k, v in data.items() if v is not None and v is not False}

    @classmethod
    def from_dict(cls, data: dict) -> "FilterPreset":
        """Create from dictionary"""
        # Filter out unknown fields for forward compatibility
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    def to_filter_criteria(self) -> "FilterCriteria":
        """Convert preset to FilterCriteria for TUI/CLI use

        Returns:
            FilterCriteria object with values from this preset
        """
        # Import here to avoid circular imports
        from src.ui.filter_modal import FilterCriteria

        criteria = FilterCriteria()

        # Map simple fields
        criteria.min_vcpu = self.min_vcpu
        criteria.max_vcpu = self.max_vcpu
        criteria.min_memory_gb = self.min_memory
        criteria.max_memory_gb = self.max_memory
        criteria.min_price = self.min_price
        criteria.max_price = self.max_price

        # Map boolean to "any/yes/no" format
        if self.has_gpu is not None:
            criteria.gpu_filter = "yes" if self.has_gpu else "no"
        if self.current_generation_only:
            criteria.current_generation = "yes"
        if self.burstable_only:
            criteria.burstable = "yes"
        if self.free_tier_only:
            criteria.free_tier = "yes"

        # Map architecture
        if self.architecture:
            criteria.architecture = self.architecture

        # Map instance families (list to comma-separated string)
        if self.instance_families:
            criteria.family_filter = ", ".join(self.instance_families)

        # Map extended fields
        if self.processor_family:
            criteria.processor_family = self.processor_family
        if self.network_performance:
            criteria.network_performance = self.network_performance
        if self.storage_type:
            criteria.storage_type = self.storage_type
        if self.nvme_support:
            criteria.nvme_support = self.nvme_support

        return criteria

    @classmethod
    def from_filter_criteria(
        cls,
        criteria: "FilterCriteria",
        name: str,
        description: str | None = None
    ) -> "FilterPreset":
        """Create preset from FilterCriteria

        Args:
            criteria: FilterCriteria object to convert
            name: Name for the preset
            description: Optional description

        Returns:
            FilterPreset object
        """
        preset = cls(name=name, description=description)

        # Map simple fields
        preset.min_vcpu = criteria.min_vcpu
        preset.max_vcpu = criteria.max_vcpu
        preset.min_memory = criteria.min_memory_gb
        preset.max_memory = criteria.max_memory_gb
        preset.min_price = criteria.min_price
        preset.max_price = criteria.max_price

        # Map "any/yes/no" to boolean
        if criteria.gpu_filter == "yes":
            preset.has_gpu = True
        elif criteria.gpu_filter == "no":
            preset.has_gpu = False

        preset.current_generation_only = criteria.current_generation == "yes"
        preset.burstable_only = criteria.burstable == "yes"
        preset.free_tier_only = criteria.free_tier == "yes"

        # Map architecture
        if criteria.architecture and criteria.architecture != "any":
            preset.architecture = criteria.architecture

        # Map family filter (comma-separated string to list)
        if criteria.family_filter and criteria.family_filter.strip():
            families = [f.strip() for f in criteria.family_filter.split(",") if f.strip()]
            if families:
                preset.instance_families = families

        # Map extended fields (only if not "any")
        if criteria.processor_family and criteria.processor_family != "any":
            preset.processor_family = criteria.processor_family
        if criteria.network_performance and criteria.network_performance != "any":
            preset.network_performance = criteria.network_performance
        if criteria.storage_type and criteria.storage_type != "any":
            preset.storage_type = criteria.storage_type
        if criteria.nvme_support and criteria.nvme_support != "any":
            preset.nvme_support = criteria.nvme_support

        return preset


class FilterPresetService:
    """Service for managing filter presets"""

    def __init__(self):
        """Initialize the preset service"""
        self.presets_dir = Path.home() / ".instancepedia" / "presets"
        self.presets_file = self.presets_dir / "filter_presets.json"
        self._ensure_presets_dir()
        self._load_builtin_presets()

    def _ensure_presets_dir(self):
        """Ensure presets directory exists"""
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    def _load_builtin_presets(self):
        """Load built-in preset definitions"""
        self.builtin_presets = {
            "web-server": FilterPreset(
                name="web-server",
                description="Cost-effective instances for web servers (4+ vCPU, 8+ GB RAM)",
                min_vcpu=4,
                min_memory=8.0,
                current_generation_only=True
            ),
            "database": FilterPreset(
                name="database",
                description="Memory-optimized instances for databases (8+ vCPU, 32+ GB RAM)",
                min_vcpu=8,
                min_memory=32.0,
                current_generation_only=True,
                instance_families=["r6i", "r6g", "r7g", "x2", "db"]
            ),
            "compute-intensive": FilterPreset(
                name="compute-intensive",
                description="Compute-optimized instances (16+ vCPU)",
                min_vcpu=16,
                current_generation_only=True,
                instance_families=["c6i", "c6g", "c7g", "c5"]
            ),
            "gpu-ml": FilterPreset(
                name="gpu-ml",
                description="GPU instances for machine learning",
                has_gpu=True,
                current_generation_only=True,
                instance_families=["p4", "p3", "g5", "g4"]
            ),
            "arm-graviton": FilterPreset(
                name="arm-graviton",
                description="ARM-based Graviton instances for cost savings",
                architecture="arm64",
                current_generation_only=True
            ),
            "burstable": FilterPreset(
                name="burstable",
                description="Burstable performance instances (t-series)",
                burstable_only=True,
                current_generation_only=True
            ),
            "free-tier": FilterPreset(
                name="free-tier",
                description="Free tier eligible instances",
                free_tier_only=True
            ),
            "small-dev": FilterPreset(
                name="small-dev",
                description="Small instances for development (1-2 vCPU, up to 4 GB RAM)",
                max_vcpu=2,
                max_memory=4.0,
                current_generation_only=True
            )
        }

    def get_builtin_presets(self) -> dict[str, FilterPreset]:
        """Get all built-in presets"""
        return self.builtin_presets.copy()

    def get_builtin_preset(self, name: str) -> FilterPreset | None:
        """Get a specific built-in preset"""
        return self.builtin_presets.get(name)

    def list_builtin_presets(self) -> list[str]:
        """List names of all built-in presets"""
        return sorted(self.builtin_presets.keys())

    def load_custom_presets(self) -> dict[str, FilterPreset]:
        """Load custom presets from file"""
        if not self.presets_file.exists():
            return {}

        try:
            with open(self.presets_file, 'r') as f:
                data = json.load(f)

            presets = {}
            for name, preset_data in data.items():
                try:
                    presets[name] = FilterPreset.from_dict(preset_data)
                except Exception as e:
                    # Skip invalid presets
                    print(f"Warning: Failed to load preset '{name}': {e}")
                    continue

            return presets
        except Exception as e:
            print(f"Warning: Failed to load custom presets: {e}")
            return {}

    def save_custom_preset(self, preset: FilterPreset) -> bool:
        """Save a custom preset

        Args:
            preset: FilterPreset to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing presets
            custom_presets = self.load_custom_presets()

            # Add/update the preset
            custom_presets[preset.name] = preset

            # Convert to dict format
            data = {name: p.to_dict() for name, p in custom_presets.items()}

            # Save to file
            with open(self.presets_file, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving preset: {e}")
            return False

    def delete_custom_preset(self, name: str) -> bool:
        """Delete a custom preset

        Args:
            name: Name of preset to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            custom_presets = self.load_custom_presets()

            if name not in custom_presets:
                return False

            del custom_presets[name]

            # Save updated presets
            data = {name: p.to_dict() for name, p in custom_presets.items()}

            with open(self.presets_file, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error deleting preset: {e}")
            return False

    def get_all_presets(self) -> dict[str, FilterPreset]:
        """Get all presets (built-in and custom)"""
        all_presets = self.get_builtin_presets()
        all_presets.update(self.load_custom_presets())
        return all_presets

    def get_preset(self, name: str) -> FilterPreset | None:
        """Get a preset by name (checks custom first, then built-in)"""
        custom_presets = self.load_custom_presets()
        if name in custom_presets:
            return custom_presets[name]
        return self.builtin_presets.get(name)

    def list_all_preset_names(self) -> list[str]:
        """List names of all presets"""
        all_presets = self.get_all_presets()
        return sorted(all_presets.keys())

    def is_builtin_preset(self, name: str) -> bool:
        """Check if a preset name is a built-in preset

        Args:
            name: Preset name to check

        Returns:
            True if built-in, False otherwise
        """
        return name in self.builtin_presets

    def is_custom_preset(self, name: str) -> bool:
        """Check if a preset name is a custom preset

        Args:
            name: Preset name to check

        Returns:
            True if custom, False otherwise
        """
        custom_presets = self.load_custom_presets()
        return name in custom_presets
