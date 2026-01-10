"""Tests for SavePresetModal TUI component"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from textual.app import App, ComposeResult
from textual.widgets import Input, Button, Static
from textual.pilot import Pilot

from src.ui.save_preset_modal import SavePresetModal
from src.ui.filter_modal import FilterCriteria
from src.services.filter_preset_service import FilterPreset


def get_static_text(static_widget: Static) -> str:
    """Get the text content of a Static widget"""
    # Access the internal content attribute
    return str(static_widget._Static__content)


class SavePresetModalTestApp(App):
    """Test app for SavePresetModal"""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    def __init__(self, criteria=None, suggested_name=None, mock_service=None):
        super().__init__()
        self.criteria = criteria or FilterCriteria()
        self.suggested_name = suggested_name
        self.mock_service = mock_service
        self.dismissed_value = "NOT_DISMISSED"  # Sentinel to distinguish from None

    def compose(self) -> ComposeResult:
        yield Button("Open Modal", id="open-modal")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-modal":
            modal = SavePresetModal(self.criteria, self.suggested_name)
            if self.mock_service:
                modal.preset_service = self.mock_service
            self.push_screen(modal, callback=self._on_dismiss)

    def _on_dismiss(self, result):
        self.dismissed_value = result

    def get_modal(self):
        """Get the current modal screen if one is active"""
        if len(self.screen_stack) > 1:
            return self.screen_stack[-1]
        return None


class TestSavePresetModalDisplay:
    """Tests for SavePresetModal display"""

    @pytest.mark.asyncio
    async def test_modal_displays(self):
        """Test that modal displays correctly"""
        app = SavePresetModalTestApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            # Verify modal is open
            modal = app.get_modal()
            assert modal is not None
            assert isinstance(modal, SavePresetModal)

            # Verify modal elements exist
            header = modal.query_one("#save-preset-header", Static)
            assert "Save Filter Preset" in get_static_text(header)

            name_input = modal.query_one("#preset-name-input", Input)
            assert name_input is not None

            desc_input = modal.query_one("#preset-description-input", Input)
            assert desc_input is not None

    @pytest.mark.asyncio
    async def test_modal_with_suggested_name(self):
        """Test that suggested name is pre-filled"""
        app = SavePresetModalTestApp(suggested_name="my-preset")
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            assert name_input.value == "my-preset"

    @pytest.mark.asyncio
    async def test_modal_buttons_exist(self):
        """Test that Save and Cancel buttons exist"""
        app = SavePresetModalTestApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            save_btn = modal.query_one("#save-button", Button)
            cancel_btn = modal.query_one("#cancel-button", Button)
            assert save_btn is not None
            assert cancel_btn is not None


class TestSavePresetModalValidation:
    """Tests for SavePresetModal validation"""

    @pytest.mark.asyncio
    async def test_empty_name_shows_error(self):
        """Test that empty name shows error message"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = True

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = ""

            await pilot.click("#save-button")
            await pilot.pause()

            error_label = modal.query_one("#save-preset-error", Static)
            assert "Please enter a preset name" in get_static_text(error_label)

    @pytest.mark.asyncio
    async def test_invalid_characters_shows_error(self):
        """Test that invalid characters show error message"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "invalid@name!"

            await pilot.click("#save-button")
            await pilot.pause()

            error_label = modal.query_one("#save-preset-error", Static)
            assert "letters, numbers, hyphens, and underscores" in get_static_text(error_label)

    @pytest.mark.asyncio
    async def test_builtin_preset_shows_error(self):
        """Test that overwriting built-in preset shows error"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = True

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "web-server"

            await pilot.click("#save-button")
            await pilot.pause()

            error_label = modal.query_one("#save-preset-error", Static)
            assert "Cannot overwrite built-in preset" in get_static_text(error_label)

    @pytest.mark.asyncio
    async def test_valid_name_with_hyphens(self):
        """Test that names with hyphens are valid"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = True

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "my-custom-preset"

            await pilot.click("#save-button")
            await pilot.pause()

            mock_service.save_custom_preset.assert_called_once()

    @pytest.mark.asyncio
    async def test_valid_name_with_underscores(self):
        """Test that names with underscores are valid"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = True

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "my_custom_preset"

            await pilot.click("#save-button")
            await pilot.pause()

            mock_service.save_custom_preset.assert_called_once()


class TestSavePresetModalActions:
    """Tests for SavePresetModal actions"""

    @pytest.mark.asyncio
    async def test_save_button_saves_preset(self):
        """Test that clicking Save button saves the preset"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = True

        criteria = FilterCriteria()
        criteria.min_vcpu = 4
        criteria.gpu_filter = "yes"

        app = SavePresetModalTestApp(criteria=criteria, mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "test-preset"

            desc_input = modal.query_one("#preset-description-input", Input)
            desc_input.value = "Test description"

            await pilot.click("#save-button")
            await pilot.pause()

            mock_service.save_custom_preset.assert_called_once()
            saved_preset = mock_service.save_custom_preset.call_args[0][0]
            assert saved_preset.name == "test-preset"
            assert saved_preset.description == "Test description"

    @pytest.mark.asyncio
    async def test_cancel_button_dismisses(self):
        """Test that clicking Cancel button dismisses modal"""
        app = SavePresetModalTestApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            await pilot.click("#cancel-button")
            await pilot.pause()

            assert app.dismissed_value is None

    @pytest.mark.asyncio
    async def test_escape_key_dismisses(self):
        """Test that Escape key dismisses modal"""
        app = SavePresetModalTestApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert app.dismissed_value is None

    @pytest.mark.asyncio
    async def test_enter_key_saves(self):
        """Test that Enter key in input saves preset"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = True

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "enter-test"
            name_input.focus()

            await pilot.press("enter")
            await pilot.pause()

            mock_service.save_custom_preset.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_failure_shows_error(self):
        """Test that save failure shows error message"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = False  # Simulate failure

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "test-preset"

            await pilot.click("#save-button")
            await pilot.pause()

            error_label = modal.query_one("#save-preset-error", Static)
            assert "Failed to save preset" in get_static_text(error_label)


class TestSavePresetModalCriteriaConversion:
    """Tests for FilterCriteria to FilterPreset conversion in modal"""

    @pytest.mark.asyncio
    async def test_criteria_with_filters_saved(self):
        """Test that filter criteria are properly converted to preset"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = True

        criteria = FilterCriteria()
        criteria.min_vcpu = 8
        criteria.max_memory_gb = 64.0
        criteria.gpu_filter = "yes"
        criteria.current_generation = "yes"
        criteria.architecture = "arm64"
        criteria.processor_family = "graviton"
        criteria.min_price = 0.05

        app = SavePresetModalTestApp(criteria=criteria, mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "full-criteria"

            await pilot.click("#save-button")
            await pilot.pause()

            saved_preset = mock_service.save_custom_preset.call_args[0][0]
            assert saved_preset.name == "full-criteria"
            assert saved_preset.min_vcpu == 8
            assert saved_preset.max_memory == 64.0
            assert saved_preset.has_gpu == True
            assert saved_preset.current_generation_only == True
            assert saved_preset.architecture == "arm64"
            assert saved_preset.processor_family == "graviton"
            assert saved_preset.min_price == 0.05

    @pytest.mark.asyncio
    async def test_empty_description_saved_as_none(self):
        """Test that empty description is saved as None"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.save_custom_preset.return_value = True

        app = SavePresetModalTestApp(mock_service=mock_service)
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#open-modal")
            await pilot.pause()

            modal = app.get_modal()
            name_input = modal.query_one("#preset-name-input", Input)
            name_input.value = "no-desc"

            desc_input = modal.query_one("#preset-description-input", Input)
            desc_input.value = ""  # Empty description

            await pilot.click("#save-button")
            await pilot.pause()

            saved_preset = mock_service.save_custom_preset.call_args[0][0]
            assert saved_preset.description is None
