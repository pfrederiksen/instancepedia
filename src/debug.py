"""Debug logging utility"""

from typing import List, Optional
from textual.widgets import Static, RichLog
from textual.containers import Container, ScrollableContainer


class DebugLog:
    """Singleton debug log"""
    _instance: Optional['DebugLog'] = None
    _enabled: bool = False
    _messages: List[str] = []
    _max_messages: int = 1000  # Increased for scrolling log

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def enable(cls) -> None:
        """Enable debug logging"""
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable debug logging"""
        cls._enabled = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if debug is enabled"""
        return cls._enabled

    @classmethod
    def log(cls, message: str) -> None:
        """Log a debug message"""
        if not cls._enabled:
            return
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_message = f"[{timestamp}] {message}"
        cls._messages.append(log_message)
        
        # Keep only the last N messages (increase for scrolling log)
        if len(cls._messages) > cls._max_messages:
            cls._messages = cls._messages[-cls._max_messages:]
        
        # If there's a debug pane, try to update it
        try:
            if cls._instance and hasattr(cls._instance, '_debug_pane') and cls._instance._debug_pane:
                cls._instance._debug_pane._update_debug_pane()
        except Exception:
            pass  # Ignore errors

    @classmethod
    def get_messages(cls) -> List[str]:
        """Get all debug messages"""
        return cls._messages.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear debug messages"""
        cls._messages.clear()
        if hasattr(cls._instance, '_debug_pane'):
            cls._instance._update_debug_pane()


class DebugPane(Container):
    """Debug pane widget"""

    def __init__(self):
        super().__init__(id="debug-pane")
        self._debug_log = DebugLog()
        self._last_message_count = 0  # Track how many messages we've added
        # Store reference to this pane in the debug log instance
        if DebugLog._instance:
            DebugLog._instance._debug_pane = self

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
        # Store reference
        if DebugLog._instance:
            DebugLog._instance._debug_pane = self
        
        # Initialize with existing messages
        try:
            messages = self._debug_log.get_messages()
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
            messages = self._debug_log.get_messages()
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
                messages = self._debug_log.get_messages()
                for msg in messages:
                    debug_log.write(msg)
                self._last_message_count = len(messages)
                debug_log.scroll_end(animate=False)
            except Exception:
                pass  # Ignore errors during update

