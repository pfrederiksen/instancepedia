"""Logging configuration for Instancepedia"""

import logging
import sys
import time
from pathlib import Path


# Custom log handler for TUI integration
class TUILogHandler(logging.Handler):
    """Custom handler that feeds logs to TUI DebugPane"""

    def __init__(self):
        super().__init__()
        self._messages: list[str] = []
        self._max_messages: int = 1000
        self._debug_pane = None

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record"""
        try:
            msg = self.format(record)
            self._messages.append(msg)

            # Keep only the last N messages
            if len(self._messages) > self._max_messages:
                self._messages = self._messages[-self._max_messages:]

            # Update debug pane if available
            if self._debug_pane:
                try:
                    self._debug_pane._update_debug_pane()
                except Exception:
                    pass  # Ignore errors in UI update
        except Exception:
            self.handleError(record)

    def get_messages(self) -> list[str]:
        """Get all logged messages"""
        return self._messages.copy()

    def clear(self) -> None:
        """Clear all messages"""
        self._messages.clear()
        if self._debug_pane:
            try:
                self._debug_pane._update_debug_pane()
            except Exception:
                pass

    def set_debug_pane(self, pane) -> None:
        """Set the debug pane widget"""
        self._debug_pane = pane


class MillisecondFormatter(logging.Formatter):
    """Custom formatter that includes milliseconds in timestamps"""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Format time with milliseconds"""
        ct = self.converter(record.created)
        if datefmt:
            # Custom handling for milliseconds
            s = time.strftime(datefmt.replace('.%f', ''), ct)
            # Add milliseconds
            return f"{s}.{int(record.msecs):03d}"
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            return f"{t}.{int(record.msecs):03d}"


# Global TUI handler instance
_tui_handler: TUILogHandler | None = None


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    enable_tui: bool = False
) -> logging.Logger:
    """
    Set up logging configuration

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        enable_tui: Enable TUI log handler for debug pane

    Returns:
        Configured logger instance
    """
    global _tui_handler

    # Get root logger for the application
    logger = logging.getLogger("instancepedia")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler (stderr) - only add if not in TUI mode
    # TUI mode logs should only go to the debug pane
    if not enable_tui:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            fmt="%(levelname)s: %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # TUI handler (if enabled)
    if enable_tui:
        if _tui_handler is None:
            _tui_handler = TUILogHandler()
        _tui_handler.setLevel(logging.DEBUG)
        tui_formatter_ms = MillisecondFormatter(
            fmt="[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        _tui_handler.setFormatter(tui_formatter_ms)
        logger.addHandler(_tui_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "instancepedia") -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (defaults to main app logger)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_tui_handler() -> TUILogHandler | None:
    """Get the global TUI handler instance"""
    return _tui_handler


def enable_debug() -> None:
    """Enable DEBUG level logging"""
    logger = get_logger()
    logger.setLevel(logging.DEBUG)
    # Also set console handler to DEBUG
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, TUILogHandler):
            handler.setLevel(logging.DEBUG)
