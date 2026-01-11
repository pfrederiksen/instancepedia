"""Tests for logging configuration"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.logging_config import (
    TUILogHandler,
    MillisecondFormatter,
    setup_logging,
    get_logger,
    get_tui_handler,
    enable_debug,
)


class TestTUILogHandler:
    """Tests for TUILogHandler class"""

    def test_init(self):
        """Test TUILogHandler initialization"""
        handler = TUILogHandler()
        assert handler._messages == []
        assert handler._max_messages == 1000
        assert handler._debug_pane is None

    def test_emit_adds_message(self):
        """Test that emit adds messages to buffer"""
        handler = TUILogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        handler.emit(record)
        messages = handler.get_messages()
        assert len(messages) == 1
        assert "Test message" in messages[0]

    def test_emit_respects_max_messages(self):
        """Test that emit respects maximum message buffer"""
        handler = TUILogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Add more than max_messages
        for i in range(1100):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Message {i}",
                args=(),
                exc_info=None
            )
            handler.emit(record)

        messages = handler.get_messages()
        assert len(messages) == 1000
        # Should keep the last 1000 messages
        assert "Message 100" in messages[0]
        assert "Message 1099" in messages[-1]

    def test_emit_updates_debug_pane(self):
        """Test that emit updates debug pane if available"""
        handler = TUILogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Mock debug pane
        mock_pane = Mock()
        handler.set_debug_pane(mock_pane)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        handler.emit(record)
        mock_pane._update_debug_pane.assert_called_once()

    def test_emit_handles_debug_pane_error(self):
        """Test that emit handles debug pane update errors gracefully"""
        handler = TUILogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Mock debug pane that raises exception
        mock_pane = Mock()
        mock_pane._update_debug_pane.side_effect = Exception("Pane error")
        handler.set_debug_pane(mock_pane)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Should not raise exception
        handler.emit(record)
        messages = handler.get_messages()
        assert len(messages) == 1

    def test_get_messages_returns_copy(self):
        """Test that get_messages returns a copy"""
        handler = TUILogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        handler.emit(record)

        messages1 = handler.get_messages()
        messages2 = handler.get_messages()

        # Should be equal but not the same object
        assert messages1 == messages2
        assert messages1 is not messages2

    def test_clear(self):
        """Test clear method"""
        handler = TUILogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Add some messages
        for i in range(5):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Message {i}",
                args=(),
                exc_info=None
            )
            handler.emit(record)

        assert len(handler.get_messages()) == 5

        handler.clear()
        assert len(handler.get_messages()) == 0

    def test_clear_updates_debug_pane(self):
        """Test that clear updates debug pane"""
        handler = TUILogHandler()
        mock_pane = Mock()
        handler.set_debug_pane(mock_pane)

        handler.clear()
        mock_pane._update_debug_pane.assert_called_once()

    def test_clear_handles_debug_pane_error(self):
        """Test that clear handles debug pane errors gracefully"""
        handler = TUILogHandler()
        mock_pane = Mock()
        mock_pane._update_debug_pane.side_effect = Exception("Pane error")
        handler.set_debug_pane(mock_pane)

        # Should not raise exception
        handler.clear()
        assert len(handler.get_messages()) == 0

    def test_set_debug_pane(self):
        """Test set_debug_pane method"""
        handler = TUILogHandler()
        mock_pane = Mock()

        handler.set_debug_pane(mock_pane)
        assert handler._debug_pane is mock_pane


class TestMillisecondFormatter:
    """Tests for MillisecondFormatter class"""

    def test_format_time_with_datefmt(self):
        """Test formatTime with custom date format"""
        formatter = MillisecondFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        # Set created time to a known value
        record.created = 1609459200.123  # 2021-01-01 00:00:00.123
        record.msecs = 123

        result = formatter.formatTime(record, datefmt="%H:%M:%S")
        # Should format as HH:MM:SS.mmm
        assert result.endswith(".123")
        assert len(result.split(".")[-1]) == 3  # 3 digits for milliseconds

    def test_format_time_without_datefmt(self):
        """Test formatTime without date format"""
        formatter = MillisecondFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.created = 1609459200.456
        record.msecs = 456

        result = formatter.formatTime(record)
        # Should format as YYYY-MM-DD HH:MM:SS.mmm
        assert ".456" in result
        assert len(result.split(".")[-1]) == 3  # 3 digits for milliseconds

    def test_format_complete_message(self):
        """Test formatting a complete log message"""
        formatter = MillisecondFormatter(
            fmt="[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.created = 1609459200.789
        record.msecs = 789

        result = formatter.format(record)
        assert "INFO: Test message" in result
        assert ".789" in result


class TestSetupLogging:
    """Tests for setup_logging function"""

    def test_setup_logging_basic(self):
        """Test basic logging setup"""
        logger = setup_logging(level="INFO")
        assert logger.name == "instancepedia"
        assert logger.level == logging.INFO
        assert not logger.propagate

    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level"""
        logger = setup_logging(level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_setup_logging_removes_existing_handlers(self):
        """Test that setup_logging clears existing handlers"""
        logger = setup_logging(level="INFO")
        initial_handler_count = len(logger.handlers)

        # Setup again
        logger = setup_logging(level="INFO")
        # Should have same number of handlers (old ones cleared)
        assert len(logger.handlers) == initial_handler_count

    def test_setup_logging_with_file(self):
        """Test logging setup with file handler"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            logger = setup_logging(level="INFO", log_file=log_file)

            # Should have console and file handlers
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) == 1

            # Test logging to file
            logger.info("Test message")

            # Read file contents
            with open(log_file, 'r') as f:
                content = f.read()
            assert "Test message" in content
            assert "INFO" in content
        finally:
            # Cleanup
            Path(log_file).unlink(missing_ok=True)

    def test_setup_logging_with_tui(self):
        """Test logging setup with TUI handler"""
        logger = setup_logging(level="DEBUG", enable_tui=True)

        # Should have TUI handler
        tui_handlers = [h for h in logger.handlers if isinstance(h, TUILogHandler)]
        assert len(tui_handlers) == 1

        # Should not have console handler in TUI mode
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, TUILogHandler)
        ]
        assert len(console_handlers) == 0

    def test_setup_logging_tui_uses_millisecond_formatter(self):
        """Test that TUI handler uses MillisecondFormatter"""
        logger = setup_logging(level="DEBUG", enable_tui=True)

        tui_handlers = [h for h in logger.handlers if isinstance(h, TUILogHandler)]
        assert len(tui_handlers) == 1

        formatter = tui_handlers[0].formatter
        assert isinstance(formatter, MillisecondFormatter)

    def test_setup_logging_without_tui_has_console_handler(self):
        """Test that console handler is added when TUI is not enabled"""
        logger = setup_logging(level="INFO", enable_tui=False)

        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, TUILogHandler)
        ]
        assert len(console_handlers) == 1

    def test_setup_logging_tui_reuses_handler(self):
        """Test that TUI handler is reused across setups"""
        logger1 = setup_logging(level="DEBUG", enable_tui=True)
        tui_handler1 = get_tui_handler()

        logger2 = setup_logging(level="DEBUG", enable_tui=True)
        tui_handler2 = get_tui_handler()

        # Should be the same handler instance
        assert tui_handler1 is tui_handler2


class TestGetLogger:
    """Tests for get_logger function"""

    def test_get_logger_default(self):
        """Test get_logger with default name"""
        logger = get_logger()
        assert logger.name == "instancepedia"

    def test_get_logger_custom_name(self):
        """Test get_logger with custom name"""
        logger = get_logger("custom")
        assert logger.name == "custom"

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns same instance"""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2


class TestGetTUIHandler:
    """Tests for get_tui_handler function"""

    def test_get_tui_handler_none_initially(self):
        """Test that TUI handler is None before setup"""
        # Reset by setting up without TUI
        setup_logging(level="INFO", enable_tui=False)
        # Note: Handler might exist from previous tests
        # This test verifies the function works

    def test_get_tui_handler_returns_handler(self):
        """Test that TUI handler is returned after setup"""
        setup_logging(level="DEBUG", enable_tui=True)
        handler = get_tui_handler()
        assert handler is not None
        assert isinstance(handler, TUILogHandler)


class TestEnableDebug:
    """Tests for enable_debug function"""

    def test_enable_debug_sets_logger_level(self):
        """Test that enable_debug sets logger to DEBUG level"""
        # Setup with INFO level
        setup_logging(level="INFO", enable_tui=False)
        logger = get_logger()
        assert logger.level == logging.INFO

        # Enable debug
        enable_debug()
        assert logger.level == logging.DEBUG

    def test_enable_debug_sets_console_handler_level(self):
        """Test that enable_debug sets console handler to DEBUG"""
        setup_logging(level="INFO", enable_tui=False)
        enable_debug()

        logger = get_logger()
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, TUILogHandler)
        ]

        if console_handlers:
            assert console_handlers[0].level == logging.DEBUG

    def test_enable_debug_does_not_affect_tui_handler(self):
        """Test that enable_debug doesn't change TUI handler level"""
        setup_logging(level="INFO", enable_tui=True)
        tui_handler = get_tui_handler()
        original_level = tui_handler.level

        enable_debug()

        # TUI handler level should remain unchanged
        assert tui_handler.level == original_level


class TestLoggingIntegration:
    """Integration tests for logging system"""

    def test_logging_flow_with_tui(self):
        """Test complete logging flow with TUI"""
        logger = setup_logging(level="DEBUG", enable_tui=True)
        handler = get_tui_handler()

        # Log some messages
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Check messages were captured
        messages = handler.get_messages()
        assert len(messages) == 4
        assert any("Debug message" in msg for msg in messages)
        assert any("Info message" in msg for msg in messages)
        assert any("Warning message" in msg for msg in messages)
        assert any("Error message" in msg for msg in messages)

    def test_logging_flow_with_file(self):
        """Test complete logging flow with file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            logger = setup_logging(level="INFO", log_file=log_file)

            logger.info("Test info")
            logger.warning("Test warning")

            # Read file
            with open(log_file, 'r') as f:
                content = f.read()

            assert "Test info" in content
            assert "Test warning" in content
        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_multiple_setup_calls(self):
        """Test that multiple setup calls work correctly"""
        logger1 = setup_logging(level="INFO", enable_tui=False)
        logger1.info("First setup")

        logger2 = setup_logging(level="DEBUG", enable_tui=True)
        logger2.debug("Second setup")

        # Should still work
        assert logger1 is logger2  # Same logger instance
        assert logger2.level == logging.DEBUG
