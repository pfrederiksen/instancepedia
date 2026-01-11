"""Tests for main entry point"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from src.main import main


class TestMainEntryPoint:
    """Tests for main() entry point function"""

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    @patch('src.main.DebugLog')
    def test_tui_mode_explicit_flag(self, mock_debug_log, mock_setup_logging,
                                    mock_settings, mock_app_class, mock_parse_args):
        """Test TUI mode with explicit --tui flag"""
        # Setup
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance

        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Execute
        main()

        # Verify - should run TUI normally
        mock_settings.assert_called_once()
        mock_setup_logging.assert_called_once_with(level="INFO", enable_tui=False)
        mock_app_class.assert_called_once_with(mock_settings_instance, debug=False)
        mock_app.run.assert_called_once()

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    def test_tui_mode_no_command(self, mock_setup_logging, mock_settings,
                                 mock_app_class, mock_parse_args):
        """Test TUI mode when no command provided (default behavior)"""
        # Setup
        mock_args = Mock()
        mock_args.tui = False
        mock_args.command = None  # No command = TUI mode
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance

        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Execute
        main()

        # Verify
        mock_app_class.assert_called_once_with(mock_settings_instance, debug=False)
        mock_app.run.assert_called_once()

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    @patch('src.main.DebugLog')
    def test_tui_mode_with_debug(self, mock_debug_log, mock_setup_logging,
                                 mock_settings, mock_app_class, mock_parse_args):
        """Test TUI mode with --debug flag"""
        # Setup
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = True
        mock_parse_args.return_value = mock_args

        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance

        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Execute
        main()

        # Verify
        mock_setup_logging.assert_called_once_with(level="DEBUG", enable_tui=True)
        mock_debug_log.enable.assert_called_once()
        mock_app_class.assert_called_once_with(mock_settings_instance, debug=True)
        mock_app.run.assert_called_once()

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    def test_tui_mode_keyboard_interrupt(self, mock_exit, mock_setup_logging,
                                        mock_settings, mock_app_class, mock_parse_args):
        """Test TUI mode handles KeyboardInterrupt (Ctrl+C) gracefully"""
        # Setup
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance

        mock_app = Mock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_app_class.return_value = mock_app

        # Execute
        main()

        # Verify - should exit with code 0 (clean exit)
        mock_exit.assert_called_once_with(0)

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_tui_mode_generic_exception(self, mock_print, mock_exit, mock_setup_logging,
                                       mock_settings, mock_app_class, mock_parse_args):
        """Test TUI mode handles generic exceptions"""
        # Setup
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance

        error_message = "Test error"
        mock_app = Mock()
        mock_app.run.side_effect = Exception(error_message)
        mock_app_class.return_value = mock_app

        # Execute
        main()

        # Verify
        mock_print.assert_called_once()
        call_args = mock_print.call_args
        assert error_message in str(call_args)
        assert call_args[1]['file'] == sys.stderr
        mock_exit.assert_called_once_with(1)

    @patch('src.main.parse_args')
    @patch('src.main.run_cli')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    def test_cli_mode_with_command(self, mock_exit, mock_setup_logging,
                                   mock_run_cli, mock_parse_args):
        """Test CLI mode with a command"""
        # Setup
        mock_args = Mock()
        mock_args.tui = False
        mock_args.command = 'list'  # CLI command provided
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_run_cli.return_value = 0  # Success

        # Execute
        main()

        # Verify
        mock_setup_logging.assert_called_once_with(level="INFO", enable_tui=False)
        mock_run_cli.assert_called_once_with(mock_args)
        mock_exit.assert_called_once_with(0)

    @patch('src.main.parse_args')
    @patch('src.main.run_cli')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    def test_cli_mode_with_debug(self, mock_exit, mock_setup_logging,
                                 mock_run_cli, mock_parse_args):
        """Test CLI mode with --debug flag"""
        # Setup
        mock_args = Mock()
        mock_args.tui = False
        mock_args.command = 'list'
        mock_args.debug = True
        mock_parse_args.return_value = mock_args

        mock_run_cli.return_value = 0

        # Execute
        main()

        # Verify
        mock_setup_logging.assert_called_once_with(level="DEBUG", enable_tui=False)
        mock_run_cli.assert_called_once_with(mock_args)
        mock_exit.assert_called_once_with(0)

    @patch('src.main.parse_args')
    @patch('src.main.run_cli')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    def test_cli_mode_failure_exit_code(self, mock_exit, mock_setup_logging,
                                       mock_run_cli, mock_parse_args):
        """Test CLI mode propagates failure exit codes"""
        # Setup
        mock_args = Mock()
        mock_args.tui = False
        mock_args.command = 'list'
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_run_cli.return_value = 1  # Failure

        # Execute
        main()

        # Verify
        mock_run_cli.assert_called_once_with(mock_args)
        mock_exit.assert_called_once_with(1)

    @patch('src.main.parse_args')
    @patch('src.main.run_cli')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    def test_cli_mode_custom_exit_code(self, mock_exit, mock_setup_logging,
                                      mock_run_cli, mock_parse_args):
        """Test CLI mode handles custom exit codes"""
        # Setup
        mock_args = Mock()
        mock_args.tui = False
        mock_args.command = 'list'
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_run_cli.return_value = 5  # Custom error code

        # Execute
        main()

        # Verify
        mock_exit.assert_called_once_with(5)

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    def test_tui_then_cli_mode_isolation(self, mock_setup_logging, mock_settings,
                                         mock_app_class, mock_parse_args):
        """Test that TUI and CLI modes don't interfere with each other"""
        # This test verifies state isolation between modes

        # First call - TUI mode
        mock_args_tui = Mock()
        mock_args_tui.tui = True
        mock_args_tui.command = None
        mock_args_tui.debug = False

        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance

        mock_app = Mock()
        mock_app_class.return_value = mock_app

        mock_parse_args.return_value = mock_args_tui

        # Execute TUI
        main()

        # Verify TUI setup
        assert mock_app_class.called
        assert mock_app.run.called

        # Reset mocks
        mock_app_class.reset_mock()
        mock_setup_logging.reset_mock()

    @patch('src.main.parse_args')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_tui_mode_settings_initialization_error(self, mock_print, mock_exit,
                                                   mock_setup_logging, mock_settings,
                                                   mock_parse_args):
        """Test TUI mode handles Settings initialization error"""
        # Setup
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        error_message = "Failed to load settings"
        mock_settings.side_effect = Exception(error_message)

        # Execute
        main()

        # Verify
        mock_print.assert_called_once()
        call_args = mock_print.call_args
        assert error_message in str(call_args)
        mock_exit.assert_called_once_with(1)

    @patch('src.main.parse_args')
    @patch('src.main.InstancepediaApp')
    @patch('src.main.Settings')
    @patch('src.main.setup_logging')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_tui_mode_app_initialization_error(self, mock_print, mock_exit,
                                              mock_setup_logging, mock_settings,
                                              mock_app_class, mock_parse_args):
        """Test TUI mode handles App initialization error"""
        # Setup
        mock_args = Mock()
        mock_args.tui = True
        mock_args.command = None
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        mock_settings_instance = Mock()
        mock_settings.return_value = mock_settings_instance

        error_message = "Failed to initialize app"
        mock_app_class.side_effect = Exception(error_message)

        # Execute
        main()

        # Verify
        mock_print.assert_called_once()
        call_args = mock_print.call_args
        assert error_message in str(call_args)
        mock_exit.assert_called_once_with(1)
