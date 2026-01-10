"""Modal for saving filter presets"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Button
from textual.screen import ModalScreen
from typing import Optional

from src.services.filter_preset_service import FilterPresetService, FilterPreset
from src.ui.filter_modal import FilterCriteria


class SavePresetModal(ModalScreen):
    """Modal screen for saving current filters as a preset"""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    SavePresetModal {
        align: center middle;
    }

    #save-preset-modal {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #save-preset-header {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .input-row {
        height: 3;
        margin: 1;
        align: left middle;
    }

    .input-label {
        width: 15;
        margin-right: 1;
    }

    Input {
        width: 1fr;
    }

    #save-preset-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    #save-preset-error {
        text-align: center;
        color: $error;
        margin-top: 1;
    }

    #save-preset-help {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        criteria: FilterCriteria,
        suggested_name: Optional[str] = None
    ):
        super().__init__()
        self.criteria = criteria
        self.suggested_name = suggested_name or ""
        self.preset_service = FilterPresetService()

    def compose(self) -> ComposeResult:
        with Container(id="save-preset-modal"):
            yield Static("Save Filter Preset", id="save-preset-header")

            with Vertical():
                # Name input
                with Horizontal(classes="input-row"):
                    yield Static("Name:", classes="input-label")
                    yield Input(
                        placeholder="my-preset",
                        value=self.suggested_name,
                        id="preset-name-input"
                    )

                # Description input
                with Horizontal(classes="input-row"):
                    yield Static("Description:", classes="input-label")
                    yield Input(
                        placeholder="Optional description",
                        id="preset-description-input"
                    )

                # Error message area
                yield Static("", id="save-preset-error")

                # Buttons
                with Horizontal(id="save-preset-buttons"):
                    yield Button("Save", variant="primary", id="save-button")
                    yield Button("Cancel", variant="default", id="cancel-button")

            yield Static(
                "Press Enter to save, Esc to cancel",
                id="save-preset-help"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "save-button":
            self._save_preset()
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields"""
        self._save_preset()

    def _save_preset(self) -> None:
        """Validate and save the preset"""
        name_input = self.query_one("#preset-name-input", Input)
        desc_input = self.query_one("#preset-description-input", Input)
        error_label = self.query_one("#save-preset-error", Static)

        preset_name = name_input.value.strip()
        description = desc_input.value.strip() or None

        # Validate name
        if not preset_name:
            error_label.update("Please enter a preset name")
            name_input.focus()
            return

        # Check for invalid characters
        if not preset_name.replace("-", "").replace("_", "").isalnum():
            error_label.update("Name can only contain letters, numbers, hyphens, and underscores")
            name_input.focus()
            return

        # Check if trying to overwrite a built-in preset
        if self.preset_service.is_builtin_preset(preset_name):
            error_label.update(f"Cannot overwrite built-in preset '{preset_name}'")
            name_input.focus()
            return

        # Create preset from criteria
        preset = FilterPreset.from_filter_criteria(
            self.criteria,
            name=preset_name,
            description=description
        )

        # Save the preset
        if self.preset_service.save_custom_preset(preset):
            self.dismiss(preset)
        else:
            error_label.update("Failed to save preset. Check file permissions.")

    def action_cancel(self) -> None:
        """Cancel and close modal"""
        self.dismiss(None)
