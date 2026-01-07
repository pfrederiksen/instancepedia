"""Filter modal for advanced instance filtering"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Input, Select, Button, Checkbox
from textual.screen import ModalScreen
from typing import Dict, Any, Optional


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
        self.family_filter: str = ""  # comma-separated list of families

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
            "family_filter": self.family_filter,
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
        self.family_filter = data.get("family_filter", "")

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
            or bool(self.family_filter.strip())
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

    def compose(self) -> ComposeResult:
        with Container(id="filter-modal"):
            yield Static("Filter Instances", id="filter-header")

            with Vertical(id="filter-content"):
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

                # Family filter
                with Horizontal(classes="filter-row"):
                    yield Static("Instance Families:", classes="filter-label")
                    yield Input(
                        placeholder="e.g., t3, m5, c6i (comma-separated)",
                        value=self.criteria.family_filter,
                        id="family-filter"
                    )

                # Buttons
                with Horizontal(id="filter-buttons"):
                    yield Button("Apply Filters", variant="primary", id="apply-button")
                    yield Button("Reset All", variant="default", id="reset-button")
                    yield Button("Cancel", variant="default", id="cancel-button")

            yield Static(
                "Esc: Cancel",
                id="filter-help"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "apply-button":
            self._apply_filters()
        elif event.button.id == "reset-button":
            self._reset_filters()
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def _apply_filters(self) -> None:
        """Collect filter values and apply"""
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

        # Get family filter
        criteria.family_filter = self.query_one("#family-filter", Input).value.strip()

        # Dismiss with criteria
        self.dismiss(criteria)

    def _reset_filters(self) -> None:
        """Reset all filter inputs to default"""
        self.query_one("#min-vcpu", Input).value = ""
        self.query_one("#max-vcpu", Input).value = ""
        self.query_one("#min-memory", Input).value = ""
        self.query_one("#max-memory", Input).value = ""
        self.query_one("#gpu-filter", Select).value = "any"
        self.query_one("#current-gen-filter", Select).value = "any"
        self.query_one("#burstable-filter", Select).value = "any"
        self.query_one("#free-tier-filter", Select).value = "any"
        self.query_one("#arch-filter", Select).value = "any"
        self.query_one("#family-filter", Input).value = ""

    def action_cancel(self) -> None:
        """Cancel and close modal"""
        self.dismiss(None)
