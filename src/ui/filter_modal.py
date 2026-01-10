"""Filter modal for advanced instance filtering"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Input, Select, Button, Checkbox
from textual.screen import ModalScreen
from typing import Dict, Any, Optional, List, Tuple

from src.services.filter_preset_service import FilterPresetService, FilterPreset


class FilterCriteria:
    """Container for filter criteria"""

    def __init__(self):
        self.min_vcpu: Optional[int] = None
        self.max_vcpu: Optional[int] = None
        self.min_memory_gb: Optional[float] = None
        self.max_memory_gb: Optional[float] = None
        self.gpu_filter: str = "any"  # any, yes, no
        self.current_generation: str = "any"  # any, yes, no
        self.burstable: str = "any"  # any, yes, no
        self.free_tier: str = "any"  # any, yes, no
        self.architecture: str = "any"  # any, x86_64, arm64
        self.processor_family: str = "any"  # any, intel, amd, graviton
        self.network_performance: str = "any"  # any, low, moderate, high, very_high
        self.family_filter: str = ""  # comma-separated list of families
        self.storage_type: str = "any"  # any, ebs_only, has_instance_store
        self.nvme_support: str = "any"  # any, required, supported, unsupported
        self.min_price: Optional[float] = None  # minimum hourly price
        self.max_price: Optional[float] = None  # maximum hourly price

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
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

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load from dictionary"""
        self.min_vcpu = data.get("min_vcpu")
        self.max_vcpu = data.get("max_vcpu")
        self.min_memory_gb = data.get("min_memory_gb")
        self.max_memory_gb = data.get("max_memory_gb")
        self.gpu_filter = data.get("gpu_filter", "any")
        self.current_generation = data.get("current_generation", "any")
        self.burstable = data.get("burstable", "any")
        self.free_tier = data.get("free_tier", "any")
        self.architecture = data.get("architecture", "any")
        self.processor_family = data.get("processor_family", "any")
        self.network_performance = data.get("network_performance", "any")
        self.family_filter = data.get("family_filter", "")
        self.storage_type = data.get("storage_type", "any")
        self.nvme_support = data.get("nvme_support", "any")
        self.min_price = data.get("min_price")
        self.max_price = data.get("max_price")

    def has_active_filters(self) -> bool:
        """Check if any filters are active"""
        return (
            self.min_vcpu is not None
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
        """Reset all filters to default"""
        self.__init__()


class FilterModal(ModalScreen):
    """Modal screen for setting instance filters"""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    FilterModal {
        align: center middle;
    }

    #filter-modal {
        width: 80;
        height: auto;
        max-height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #filter-header {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #filter-content {
        height: auto;
        max-height: 1fr;
        overflow-y: auto;
    }

    .filter-row {
        height: 3;
        margin: 1;
        align: left middle;
    }

    .preset-row {
        height: 3;
        margin: 1;
        align: left middle;
        background: $surface-darken-1;
        padding: 0 1;
    }

    .filter-label {
        width: 25;
        margin-right: 1;
    }

    .filter-separator {
        width: 3;
        text-align: center;
        margin: 0 1;
    }

    Input {
        width: 1fr;
    }

    Select {
        width: 1fr;
    }

    #preset-select {
        width: 1fr;
    }

    #filter-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    #filter-help {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, current_criteria: Optional[FilterCriteria] = None):
        super().__init__()
        self.criteria = current_criteria or FilterCriteria()
        self.preset_service = FilterPresetService()
        self._selected_preset_name: Optional[str] = None

    def _get_preset_options(self) -> List[Tuple[str, str]]:
        """Get list of preset options for the dropdown"""
        options = [("-- Select Preset --", "")]
        all_presets = self.preset_service.get_all_presets()
        for name, preset in sorted(all_presets.items()):
            # Mark custom presets with asterisk
            if self.preset_service.is_custom_preset(name):
                label = f"* {name}"
            else:
                label = name
            if preset.description:
                label = f"{label} ({preset.description[:30]}...)" if len(preset.description) > 30 else f"{label} ({preset.description})"
            options.append((label, name))
        return options

    def compose(self) -> ComposeResult:
        with Container(id="filter-modal"):
            yield Static("Filter Instances", id="filter-header")

            with Vertical(id="filter-content"):
                # Preset selector
                with Horizontal(classes="preset-row"):
                    yield Static("Load Preset:", classes="filter-label")
                    yield Select(
                        self._get_preset_options(),
                        value="",
                        id="preset-select",
                        allow_blank=True
                    )

                # vCPU filters
                with Horizontal(classes="filter-row"):
                    yield Static("vCPU Count:", classes="filter-label")
                    yield Input(
                        placeholder="Min",
                        value=str(self.criteria.min_vcpu) if self.criteria.min_vcpu is not None else "",
                        id="min-vcpu"
                    )
                    yield Static("-", classes="filter-separator")
                    yield Input(
                        placeholder="Max",
                        value=str(self.criteria.max_vcpu) if self.criteria.max_vcpu is not None else "",
                        id="max-vcpu"
                    )

                # Memory filters
                with Horizontal(classes="filter-row"):
                    yield Static("Memory (GB):", classes="filter-label")
                    yield Input(
                        placeholder="Min",
                        value=str(self.criteria.min_memory_gb) if self.criteria.min_memory_gb is not None else "",
                        id="min-memory"
                    )
                    yield Static("-", classes="filter-separator")
                    yield Input(
                        placeholder="Max",
                        value=str(self.criteria.max_memory_gb) if self.criteria.max_memory_gb is not None else "",
                        id="max-memory"
                    )

                # GPU filter
                with Horizontal(classes="filter-row"):
                    yield Static("Has GPU:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("Yes", "yes"), ("No", "no")],
                        value=self.criteria.gpu_filter,
                        id="gpu-filter"
                    )

                # Current generation filter
                with Horizontal(classes="filter-row"):
                    yield Static("Current Generation:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("Yes", "yes"), ("No", "no")],
                        value=self.criteria.current_generation,
                        id="current-gen-filter"
                    )

                # Burstable performance filter
                with Horizontal(classes="filter-row"):
                    yield Static("Burstable Performance:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("Yes", "yes"), ("No", "no")],
                        value=self.criteria.burstable,
                        id="burstable-filter"
                    )

                # Free tier filter
                with Horizontal(classes="filter-row"):
                    yield Static("Free Tier Eligible:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("Yes", "yes"), ("No", "no")],
                        value=self.criteria.free_tier,
                        id="free-tier-filter"
                    )

                # Architecture filter
                with Horizontal(classes="filter-row"):
                    yield Static("Architecture:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("x86_64", "x86_64"), ("ARM64", "arm64")],
                        value=self.criteria.architecture,
                        id="arch-filter"
                    )

                # Processor family filter
                with Horizontal(classes="filter-row"):
                    yield Static("Processor Family:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("Intel", "intel"), ("AMD", "amd"), ("Graviton (ARM)", "graviton")],
                        value=self.criteria.processor_family,
                        id="processor-family-filter"
                    )

                # Network performance filter
                with Horizontal(classes="filter-row"):
                    yield Static("Network Performance:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("Low", "low"), ("Moderate", "moderate"), ("High", "high"), ("Very High", "very_high")],
                        value=self.criteria.network_performance,
                        id="network-performance-filter"
                    )

                # Family filter
                with Horizontal(classes="filter-row"):
                    yield Static("Instance Families:", classes="filter-label")
                    yield Input(
                        placeholder="e.g., t3, m5, c6i (comma-separated)",
                        value=self.criteria.family_filter,
                        id="family-filter"
                    )

                # Storage type filter
                with Horizontal(classes="filter-row"):
                    yield Static("Storage Type:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("EBS Only", "ebs_only"), ("Has Instance Store", "has_instance_store")],
                        value=self.criteria.storage_type,
                        id="storage-type-filter"
                    )

                # NVMe support filter
                with Horizontal(classes="filter-row"):
                    yield Static("NVMe Support:", classes="filter-label")
                    yield Select(
                        [("Any", "any"), ("Required", "required"), ("Supported", "supported"), ("Unsupported", "unsupported")],
                        value=self.criteria.nvme_support,
                        id="nvme-filter"
                    )

                # Price range filters
                with Horizontal(classes="filter-row"):
                    yield Static("Price Range ($/hr):", classes="filter-label")
                    yield Input(
                        placeholder="Min",
                        value=str(self.criteria.min_price) if self.criteria.min_price is not None else "",
                        id="min-price"
                    )
                    yield Static("-", classes="filter-separator")
                    yield Input(
                        placeholder="Max",
                        value=str(self.criteria.max_price) if self.criteria.max_price is not None else "",
                        id="max-price"
                    )

                # Buttons
                with Horizontal(id="filter-buttons"):
                    yield Button("Apply Filters", variant="primary", id="apply-button")
                    yield Button("Save Preset", variant="default", id="save-preset-button")
                    yield Button("Reset All", variant="default", id="reset-button")
                    yield Button("Cancel", variant="default", id="cancel-button")

            yield Static(
                "Esc: Cancel  |  * = Custom Preset",
                id="filter-help"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "apply-button":
            self._apply_filters()
        elif event.button.id == "save-preset-button":
            self._show_save_preset_dialog()
        elif event.button.id == "reset-button":
            self._reset_filters()
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle preset selection"""
        if event.select.id == "preset-select" and event.value:
            self._apply_preset(event.value)

    def _apply_preset(self, preset_name: str) -> None:
        """Apply a preset to the filter fields"""
        preset = self.preset_service.get_preset(preset_name)
        if not preset:
            return

        self._selected_preset_name = preset_name

        # Convert preset to filter criteria and populate fields
        criteria = preset.to_filter_criteria()

        # Update all the input fields
        self.query_one("#min-vcpu", Input).value = str(criteria.min_vcpu) if criteria.min_vcpu is not None else ""
        self.query_one("#max-vcpu", Input).value = str(criteria.max_vcpu) if criteria.max_vcpu is not None else ""
        self.query_one("#min-memory", Input).value = str(criteria.min_memory_gb) if criteria.min_memory_gb is not None else ""
        self.query_one("#max-memory", Input).value = str(criteria.max_memory_gb) if criteria.max_memory_gb is not None else ""
        self.query_one("#gpu-filter", Select).value = criteria.gpu_filter
        self.query_one("#current-gen-filter", Select).value = criteria.current_generation
        self.query_one("#burstable-filter", Select).value = criteria.burstable
        self.query_one("#free-tier-filter", Select).value = criteria.free_tier
        self.query_one("#arch-filter", Select).value = criteria.architecture
        self.query_one("#processor-family-filter", Select).value = criteria.processor_family
        self.query_one("#network-performance-filter", Select).value = criteria.network_performance
        self.query_one("#family-filter", Input).value = criteria.family_filter
        self.query_one("#storage-type-filter", Select).value = criteria.storage_type
        self.query_one("#nvme-filter", Select).value = criteria.nvme_support
        self.query_one("#min-price", Input).value = str(criteria.min_price) if criteria.min_price is not None else ""
        self.query_one("#max-price", Input).value = str(criteria.max_price) if criteria.max_price is not None else ""

    def _show_save_preset_dialog(self) -> None:
        """Show dialog to save current filters as a preset"""
        # Collect current criteria first
        criteria = self._collect_criteria()

        # Check if there are any active filters
        if not criteria.has_active_filters():
            self.notify("No filters to save. Set at least one filter first.", severity="warning")
            return

        # Push the save preset modal
        from src.ui.save_preset_modal import SavePresetModal
        self.app.push_screen(
            SavePresetModal(criteria, self._selected_preset_name),
            self._on_save_preset_complete
        )

    def _on_save_preset_complete(self, result: Optional[FilterPreset]) -> None:
        """Handle save preset modal result"""
        if result:
            # Refresh the preset dropdown
            preset_select = self.query_one("#preset-select", Select)
            preset_select.set_options(self._get_preset_options())
            preset_select.value = result.name
            self._selected_preset_name = result.name
            self.notify(f"Preset '{result.name}' saved successfully!", severity="information")

    def _collect_criteria(self) -> FilterCriteria:
        """Collect current filter values into FilterCriteria"""
        criteria = FilterCriteria()

        # Get vCPU values
        min_vcpu_input = self.query_one("#min-vcpu", Input)
        max_vcpu_input = self.query_one("#max-vcpu", Input)
        try:
            if min_vcpu_input.value.strip():
                criteria.min_vcpu = int(min_vcpu_input.value.strip())
        except ValueError:
            pass
        try:
            if max_vcpu_input.value.strip():
                criteria.max_vcpu = int(max_vcpu_input.value.strip())
        except ValueError:
            pass

        # Get memory values
        min_memory_input = self.query_one("#min-memory", Input)
        max_memory_input = self.query_one("#max-memory", Input)
        try:
            if min_memory_input.value.strip():
                criteria.min_memory_gb = float(min_memory_input.value.strip())
        except ValueError:
            pass
        try:
            if max_memory_input.value.strip():
                criteria.max_memory_gb = float(max_memory_input.value.strip())
        except ValueError:
            pass

        # Get select values
        criteria.gpu_filter = self.query_one("#gpu-filter", Select).value
        criteria.current_generation = self.query_one("#current-gen-filter", Select).value
        criteria.burstable = self.query_one("#burstable-filter", Select).value
        criteria.free_tier = self.query_one("#free-tier-filter", Select).value
        criteria.architecture = self.query_one("#arch-filter", Select).value
        criteria.processor_family = self.query_one("#processor-family-filter", Select).value
        criteria.network_performance = self.query_one("#network-performance-filter", Select).value
        criteria.storage_type = self.query_one("#storage-type-filter", Select).value
        criteria.nvme_support = self.query_one("#nvme-filter", Select).value

        # Get family filter
        criteria.family_filter = self.query_one("#family-filter", Input).value.strip()

        # Get price range values
        min_price_input = self.query_one("#min-price", Input)
        max_price_input = self.query_one("#max-price", Input)
        try:
            if min_price_input.value.strip():
                criteria.min_price = float(min_price_input.value.strip())
        except ValueError:
            pass
        try:
            if max_price_input.value.strip():
                criteria.max_price = float(max_price_input.value.strip())
        except ValueError:
            pass

        return criteria

    def _apply_filters(self) -> None:
        """Collect filter values and apply"""
        criteria = self._collect_criteria()
        # Dismiss with criteria
        self.dismiss(criteria)

    def _reset_filters(self) -> None:
        """Reset all filter inputs to default"""
        self.query_one("#preset-select", Select).value = ""
        self._selected_preset_name = None
        self.query_one("#min-vcpu", Input).value = ""
        self.query_one("#max-vcpu", Input).value = ""
        self.query_one("#min-memory", Input).value = ""
        self.query_one("#max-memory", Input).value = ""
        self.query_one("#gpu-filter", Select).value = "any"
        self.query_one("#current-gen-filter", Select).value = "any"
        self.query_one("#burstable-filter", Select).value = "any"
        self.query_one("#free-tier-filter", Select).value = "any"
        self.query_one("#arch-filter", Select).value = "any"
        self.query_one("#processor-family-filter", Select).value = "any"
        self.query_one("#network-performance-filter", Select).value = "any"
        self.query_one("#family-filter", Input).value = ""
        self.query_one("#storage-type-filter", Select).value = "any"
        self.query_one("#nvme-filter", Select).value = "any"
        self.query_one("#min-price", Input).value = ""
        self.query_one("#max-price", Input).value = ""

    def action_cancel(self) -> None:
        """Cancel and close modal"""
        self.dismiss(None)
