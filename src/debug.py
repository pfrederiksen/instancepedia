"""Debug logging utility - backwards compatibility wrapper"""

import logging
from src.logging_config import get_logger, get_tui_handler, enable_debug as enable_debug_logging
from textual.widgets import Static, RichLog
from textual.containers import Container, ScrollableContainer


class DebugLog:
    """
    Backwards compatibility wrapper for legacy DebugLog calls.
    Delegates to proper logging system.
    """
    _enabled: bool = False

    @classmethod
    def enable(cls) -> None:
        """Enable debug logging"""
        cls._enabled = True
        enable_debug_logging()

    @classmethod
    def disable(cls) -> None:
        """Disable debug logging"""
        cls._enabled = False
        logger = get_logger()
        logger.setLevel(logging.INFO)

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if debug is enabled"""
        return cls._enabled

    @classmethod
    def log(cls, message: str) -> None:
        """Log a debug message (delegates to logging system)"""
        logger = get_logger()
        logger.debug(message)

    @classmethod
    def get_messages(cls) -> list[str]:
        """Get all debug messages from TUI handler"""
        handler = get_tui_handler()
        if handler:
            return handler.get_messages()
        return []

    @classmethod
    def clear(cls) -> None:
        """Clear debug messages"""
        handler = get_tui_handler()
        if handler:
            handler.clear()


class DebugPane(Container):
    """Debug pane widget"""

    def __init__(self):
        super().__init__(id="debug-pane")
        self._last_message_count = 0  # Track how many messages we've added
        # Register this pane with the TUI handler
        handler = get_tui_handler()
        if handler:
            handler.set_debug_pane(self)

    CSS = """
    #debug-pane {
        height: 50%;
        border-top: solid $primary;
        background: $panel;
        padding: 0 1;
        dock: bottom;
    }
    
    #debug-label {
        text-style: bold;
        color: $primary;
        height: 1;
        padding: 0 1;
    }
    
    #debug-content {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }
    """

    def compose(self):
        yield Static("Debug Log:", id="debug-label")
        with ScrollableContainer(id="debug-content"):
            yield RichLog(id="debug-log", wrap=True, markup=False)

    def on_mount(self) -> None:
        """Update debug pane when mounted"""
        # Register with TUI handler
        handler = get_tui_handler()
        if handler:
            handler.set_debug_pane(self)

        # Initialize with existing messages
        try:
            messages = DebugLog.get_messages()
            debug_log = self.query_one("#debug-log", RichLog)
            for msg in messages:
                debug_log.write(msg)
            self._last_message_count = len(messages)
        except Exception:
            self._last_message_count = 0

        # Set up a timer to periodically update
        self.set_interval(0.1, self._update_debug_pane)  # Update more frequently

    def _update_debug_pane(self) -> None:
        """Update the debug pane content"""
        try:
            messages = DebugLog.get_messages()
            debug_log = self.query_one("#debug-log", RichLog)

            # Handle case where messages were trimmed and _last_message_count is out of sync
            # If messages were trimmed, we need to reset and repopulate
            if self._last_message_count > len(messages):
                # Messages were trimmed, clear and repopulate
                debug_log.clear()
                for msg in messages:
                    debug_log.write(msg)
                self._last_message_count = len(messages)
                debug_log.scroll_end(animate=False)
            elif self._last_message_count < len(messages):
                # Add new messages
                for msg in messages[self._last_message_count:]:
                    debug_log.write(msg)
                self._last_message_count = len(messages)
                # Force scroll to bottom to show latest messages
                try:
                    debug_log.scroll_end(animate=False)
                    # Also try scrolling by a large amount to ensure we're at the end
                    debug_log.scroll_down(999999, animate=False)
                except Exception:
                    pass  # Ignore scroll errors
        except Exception:
            # If RichLog doesn't exist yet or other error, try to initialize
            try:
                debug_log = self.query_one("#debug-log", RichLog)
                # Clear and repopulate
                debug_log.clear()
                messages = DebugLog.get_messages()
                for msg in messages:
                    debug_log.write(msg)
                self._last_message_count = len(messages)
                debug_log.scroll_end(animate=False)
            except Exception:
                pass  # Ignore errors during update

