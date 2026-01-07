"""Filter preset service for saving and loading filter configurations"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class FilterPreset:
    """Filter preset configuration"""
    name: str
    description: Optional[str] = None
    min_vcpu: Optional[int] = None
    max_vcpu: Optional[int] = None
    min_memory: Optional[float] = None
    max_memory: Optional[float] = None
    has_gpu: Optional[bool] = None
    current_generation_only: bool = False
    burstable_only: bool = False
    free_tier_only: bool = False
    architecture: Optional[str] = None  # "x86_64" or "arm64"
    instance_families: Optional[List[str]] = None  # e.g., ["t3", "t4g"]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Remove None values to keep JSON clean
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> "FilterPreset":
        """Create from dictionary"""
        return cls(**data)


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

    def get_builtin_presets(self) -> Dict[str, FilterPreset]:
        """Get all built-in presets"""
        return self.builtin_presets.copy()

    def get_builtin_preset(self, name: str) -> Optional[FilterPreset]:
        """Get a specific built-in preset"""
        return self.builtin_presets.get(name)

    def list_builtin_presets(self) -> List[str]:
        """List names of all built-in presets"""
        return sorted(self.builtin_presets.keys())

    def load_custom_presets(self) -> Dict[str, FilterPreset]:
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

    def get_all_presets(self) -> Dict[str, FilterPreset]:
        """Get all presets (built-in and custom)"""
        all_presets = self.get_builtin_presets()
        all_presets.update(self.load_custom_presets())
        return all_presets

    def get_preset(self, name: str) -> Optional[FilterPreset]:
        """Get a preset by name (checks custom first, then built-in)"""
        custom_presets = self.load_custom_presets()
        if name in custom_presets:
            return custom_presets[name]
        return self.builtin_presets.get(name)

    def list_all_preset_names(self) -> List[str]:
        """List names of all presets"""
        all_presets = self.get_all_presets()
        return sorted(all_presets.keys())
